"""Consolidação mensal da Prestação de Contas.

Usa DriveIndex para resolução em memória ultra-rápida.
- Cruza rubricas com pastas usando match normalizado (ex: Faxina/Limpeza == Faxina-Limpeza)
- Detecta duplicatas de arquivo por hash MD5
- Preserva links e IDs de PDFs já consolidados
- Escreve na planilha via batch_update (Google Sheets)

Uso:
  py consolidar.py                 # garante meses até 09/2026 + consolida tudo
  py consolidar.py --dry-run       # simula sem gravar alterações
  py consolidar.py --sem-meses     # consolida sem criar novas abas/pastas
  py consolidar.py --mes "Maio 2026"
"""
import argparse
import hashlib
import io
import os
import re
import sys
import time
from datetime import datetime

import fitz  # PyMuPDF (substitui PyPDF2, eliminando avisos de Object not defined)
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from PIL import Image

import classificador
import comum
from comum import (BLOCO_A, BLOCO_B, MES_ALVO_PADRAO, ID_PLANILHA, DriveIndex,
                   gerar_prefixo_mes, normalizar, RE_CONSOLIDADO, obter_letra_mes)


class LoggerTee:
    """Duplica a saída de print para o console e para os arquivos de log em disco."""
    def __init__(self, *files):
        self.files = files

    def write(self, data):
        for f in self.files:
            try:
                f.write(data)
                f.flush()
            except Exception:
                pass

    def flush(self):
        for f in self.files:
            try:
                f.flush()
            except Exception:
                pass


def iniciar_logger():
    pasta_logs = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(pasta_logs, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    caminho_hist = os.path.join(pasta_logs, f'consolidacao_{ts}.log')
    caminho_ultimo = os.path.join(os.path.dirname(__file__), 'consolidacao_ultimo.log')
    f_hist = open(caminho_hist, 'w', encoding='utf-8', buffering=1)
    f_ult = open(caminho_ultimo, 'w', encoding='utf-8', buffering=1)
    sys.stdout = LoggerTee(sys.stdout, f_hist, f_ult)
    sys.stderr = LoggerTee(sys.stderr, f_hist, f_ult)
    return caminho_hist, caminho_ultimo

RE_VALOR_RS = re.compile(r'R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2}|\d+[.,]\d{2})')
RE_VALOR = re.compile(r'(?<![\d.,])(\d+)[.,](\d{2})(?![\d])')

relatorio = {'criados': [], 'atualizados': [], 'ignorados': 0, 'duplicados': [], 'substituidos': [], 'sem_valor': [], 'compilados': []}


def higienizar_nome(nome):
    return re.sub(r'[\\/*?:"<>|]', '-', nome)[:80].strip()


def formatar_nome_consolidado(rubrica, bloco, mes_nome, doc_str):
    """Padrão: Doc A2 - Comprovantes - (nome da despesa/Individual ou geral) - mes/ano"""
    tipo_bloco = 'Individual' if bloco == 'A' else 'Geral'
    rubrica_limpa = higienizar_nome(rubrica)
    if f'({tipo_bloco})' in rubrica_limpa:
        return f'{doc_str} - Comprovantes - {rubrica_limpa} - {mes_nome}.pdf'
    return f'{doc_str} - Comprovantes - {rubrica_limpa} ({tipo_bloco}) - {mes_nome}.pdf'


def extrair_valor_do_nome(nome_arquivo):
    m = RE_VALOR_RS.search(nome_arquivo)
    if m:
        bruto = m.group(1)
        if ',' in bruto:
            bruto = bruto.replace('.', '').replace(',', '.')
        return float(bruto)
    m = RE_VALOR.search(nome_arquivo)
    return float(f'{m.group(1)}.{m.group(2)}') if m else 0.0


def fmt_br(v):
    return f'{v:.2f}'.replace('.', ',')


def gerar_hash_estado(arquivos_fonte):
    if not arquivos_fonte:
        return 'VAZIO'
    assinaturas = sorted(f"{a['id']}-{a.get('md5Checksum', a.get('modifiedTime', ''))}" for a in arquivos_fonte)
    return hashlib.md5('|'.join(assinaturas).encode('utf-8')).hexdigest()


def eh_comprovante(f):
    mt = f.get('mimeType', '')
    return mt == 'application/pdf' or mt.startswith('image/') or mt == 'application/octet-stream'


def classificar_arquivos_da_pasta(drive_idx, id_pasta, nome_consolidado, rotulo, rubrica="", dry_run=False):
    filhos = drive_idx.listar_filhos(id_pasta, apenas_pastas=False)
    fontes, consolidado, vistos = [], None, {}
    for f in sorted(filhos, key=lambda x: x['name'].lower()):
        if f['name'] == nome_consolidado:
            consolidado = f
            continue
        if RE_CONSOLIDADO.match(f['name']):
            # Arquivo consolidado pré-existente ou com formato anterior (ex: 'mai-26 Aluguel.pdf')
            if not consolidado:
                f_orig = f['name']
                if not dry_run:
                    try:
                        drive_idx.drive.files().update(fileId=f['id'], body={'name': nome_consolidado}).execute()
                        f['name'] = nome_consolidado
                        consolidado = f
                        print(f"     🏷️  Padronizado nome: '{f_orig}' -> '{nome_consolidado}'")
                        continue
                    except Exception:
                        pass
                else:
                    f['name'] = nome_consolidado
                    consolidado = f
                    continue
            else:
                # Já temos o consolidado principal, descarta arquivo anterior redundante
                if not dry_run:
                    try:
                        drive_idx.drive.files().update(fileId=f['id'], body={'trashed': True}).execute()
                        drive_idx.remover_arquivo(f['id'])
                    except Exception:
                        pass
                continue
        if not eh_comprovante(f):
            continue
        md5 = f.get('md5Checksum')
        if md5 and md5 in vistos:
            relatorio['duplicados'].append(f"{rotulo}: '{f['name']}' == '{vistos[md5]}' (duplicata exata descartada)")
            if not dry_run:
                try:
                    drive_idx.drive.files().update(fileId=f['id'], body={'trashed': True}).execute()
                    drive_idx.remover_arquivo(f['id'])
                except Exception:
                    pass
            continue
        if md5:
            vistos[md5] = f['name']
        fontes.append(f)

    # Regra de substituição de versão: preferir o último subido
    if len(fontes) > 1:
        # Ordena fontes pelo modifiedTime decrescente (mais recente primeiro)
        fontes.sort(key=lambda x: x.get('modifiedTime', ''), reverse=True)

        if comum.eh_rubrica_conta_unica(rubrica):
            # Conta única: mantém estritamente o mais recente
            oficial = fontes[0]
            for antigo in fontes[1:]:
                relatorio['substituidos'].append(f"{rotulo}: '{antigo['name']}' substituído por '{oficial['name']}' (versão mais recente mantida)")
                if not dry_run:
                    try:
                        drive_idx.drive.files().update(fileId=antigo['id'], body={'trashed': True}).execute()
                        drive_idx.remover_arquivo(antigo['id'])
                    except Exception:
                        pass
            fontes = [oficial]
        else:
            # Rubricas multi-itens: verifica comprovantes com valor muito próximo e mesma data
            mantidos = []
            for f in fontes:
                v_f = extrair_valor_do_nome(f['name'])
                substituido_por = None
                for m in mantidos:
                    v_m = extrair_valor_do_nome(m['name'])
                    if v_f > 0 and v_m > 0 and comum.valores_muito_proximos(v_f, v_m):
                        d_f = classificador.extrair_data(f['name'])
                        d_m = classificador.extrair_data(m['name'])
                        match_data = False
                        if d_f and d_m:
                            match_data = (d_f.date() == d_m.date())
                        elif not d_f and not d_m:
                            match_data = (abs(v_f - v_m) < 0.01)
                        if match_data:
                            substituido_por = m
                            break
                if substituido_por:
                    relatorio['substituidos'].append(f"{rotulo}: '{f['name']}' substituído por '{substituido_por['name']}' (versão mais recente mantida)")
                    if not dry_run:
                        try:
                            drive_idx.drive.files().update(fileId=f['id'], body={'trashed': True}).execute()
                            drive_idx.remover_arquivo(f['id'])
                        except Exception:
                            pass
                else:
                    mantidos.append(f)
            fontes = mantidos

    return fontes, consolidado


def baixar(drive, id_arquivo):
    buf = io.BytesIO()
    dl = MediaIoBaseDownload(buf, drive.files().get_media(fileId=id_arquivo))
    done = False
    while not done:
        _, done = dl.next_chunk()
    buf.seek(0)
    return buf


def montar_pdf(drive, arquivos):
    doc_final = fitz.open()
    for arq in arquivos:
        dados = baixar(drive, arq['id'])
        raw = dados.getvalue()
        if arq.get('mimeType') == 'application/pdf' or raw[:4] == b'%PDF':
            try:
                sub_doc = fitz.open(stream=raw, filetype="pdf")
                doc_final.insert_pdf(sub_doc)
                sub_doc.close()
            except Exception as e:
                print(f"     ⚠️  Aviso ao mesclar PDF {arq['name']}: {e}")
        else:
            try:
                imagem = Image.open(io.BytesIO(raw)).convert('RGB')
                imagem.thumbnail((1200, 1600), Image.Resampling.LANCZOS)
                pdf_bytes = io.BytesIO()
                imagem.save(pdf_bytes, format='PDF', resolution=72, optimize=True, quality=50)
                sub_doc = fitz.open(stream=pdf_bytes.getvalue(), filetype="pdf")
                doc_final.insert_pdf(sub_doc)
                sub_doc.close()
            except Exception as e:
                print(f"     ⚠️  Aviso ao converter imagem {arq['name']}: {e}")

    out = io.BytesIO(doc_final.tobytes(garbage=4, deflate=True))
    doc_final.close()
    out.seek(0)
    return out


def upload_consolidado(drive, nome_arquivo, pdf_bytes, id_pasta, hash_pasta, existente):
    media = MediaIoBaseUpload(pdf_bytes, mimetype='application/pdf', resumable=True)
    props = {'appProperties': {'hash_estado': hash_pasta}}
    if existente:
        f = drive.files().update(fileId=existente['id'], body=props, media_body=media,
                                 fields='id, name, webViewLink, appProperties').execute()
    else:
        f = drive.files().create(body={'name': nome_arquivo, 'parents': [id_pasta], **props},
                                 media_body=media, fields='id, name, webViewLink, appProperties').execute()
        try:
            drive.permissions().create(fileId=f['id'], body={'type': 'anyone', 'role': 'reader'}).execute()
        except Exception:
            pass
    return f


def consolidar_aba(drive_idx, aba, dry_run=False):
    drive = drive_idx.drive
    mes_nome = aba.title.strip()
    id_mes = drive_idx.pasta_do_mes(mes_nome)
    if not id_mes:
        return []

    pastas = {}
    for bloco_nome, chave in ((BLOCO_A, 'A'), (BLOCO_B, 'B')):
        blocos = [f for f in drive_idx.listar_filhos(id_mes, apenas_pastas=True) if f['name'] == bloco_nome]
        if blocos:
            pastas[chave] = {normalizar(f['name']): f['id']
                             for f in drive_idx.listar_filhos(blocos[0]['id'], apenas_pastas=True)
                             if not f['name'].startswith('[LIXO')}
        else:
            pastas[chave] = {}

    dados = aba.get_all_values()
    letra_mes = obter_letra_mes(mes_nome)
    bloco, updates, doc = None, [], 2  # Doc {letra}1 é a planilha do mês! As despesas iniciam em Doc {letra}2...
    docs_compilacao = []

    for i, linha in enumerate(dados):
        ln = i + 1
        c0 = linha[0].strip() if len(linha) > 0 else ''
        rubrica = linha[1].strip() if len(linha) > 1 else ''
        if 'A - DESPESAS INDIVIDUAIS' in c0:
            bloco = 'A'
            continue
        if 'B - DESPESAS GERAIS' in c0:
            bloco = 'B'
            continue
        if rubrica.startswith('Subtotal') or rubrica.startswith('TOTAL'):
            bloco = None
            continue
        if not bloco or not rubrica or rubrica == 'Descrição / Rubrica':
            continue

        id_pasta = pastas[bloco].get(normalizar(rubrica))
        if not id_pasta:
            continue
        rotulo = f'[{mes_nome}] {rubrica}'
        tipo_bloco = 'Individual' if bloco == 'A' else 'Geral'
        str_doc = f'Doc {letra_mes}{doc}'
        nome_cons = formatar_nome_consolidado(rubrica, bloco, mes_nome, str_doc)
        fontes, consolidado = classificar_arquivos_da_pasta(
            drive_idx, id_pasta, nome_cons, rotulo, rubrica=rubrica, dry_run=dry_run
        )
        if not fontes:
            continue

        doc += 1
        com_valor, sem_valor, soma = [], [], 0.0
        for a in fontes:
            v = extrair_valor_do_nome(a['name'])
            soma += v
            (com_valor if v else sem_valor).append(a)
        for a in sem_valor:
            relatorio['sem_valor'].append(f"{rotulo}: '{a['name']}'")
        soma = round(soma, 2)
        individual = soma if bloco == 'A' else round(soma / 3, 2)

        hash_atual = gerar_hash_estado(fontes)
        hash_salvo = (consolidado or {}).get('appProperties', {}).get('hash_estado', '')
        valores = [[fmt_br(soma) if soma else '', fmt_br(individual) if soma else '']]

        id_cons_final = None
        pdf_bytes_final = None

        if consolidado and hash_atual == hash_salvo:
            relatorio['ignorados'] += 1
            link = consolidado.get('webViewLink', '')
            id_cons_final = consolidado['id']
        else:
            acao = 'atualizados' if consolidado else 'criados'
            print(f"  {'🔄' if consolidado else '🆕'} {rotulo} -> {str_doc} | {len(fontes)} arq | R$ {fmt_br(soma)}")
            relatorio[acao].append(f'{rotulo} {str_doc} (R$ {fmt_br(soma)})')
            if dry_run:
                link = (consolidado or {}).get('webViewLink', '<novo>')
                id_cons_final = (consolidado or {}).get('id', '')
            else:
                try:
                    pdf = montar_pdf(drive, sem_valor + com_valor)
                    pdf_bytes_final = pdf.getvalue()
                    f_salvo = upload_consolidado(drive, nome_cons, io.BytesIO(pdf_bytes_final), id_pasta, hash_atual, consolidado)
                    link = f_salvo.get('webViewLink', '')
                    id_cons_final = f_salvo.get('id', '')
                    drive_idx.adicionar_arquivo(f_salvo)
                except Exception as e:
                    print(f"     ⚠️  Não foi possível fazer upload do PDF ({e}); preservando link existente.")
                    link = (consolidado or {}).get('webViewLink', '')
                    id_cons_final = (consolidado or {}).get('id', '')

        updates += [
            {'range': f'C{ln}:E{ln}', 'values': [valores[0] + [str_doc]]},
            {'range': f'G{ln}', 'values': [[f'=HYPERLINK("{link}"; "Link")']] if link else [['']]},
        ]

        docs_compilacao.append({
            'doc_num': str_doc,
            'rubrica': rubrica,
            'tipo': tipo_bloco,
            'nome_cons': nome_cons,
            'id_arquivo': id_cons_final,
            'pdf_bytes': pdf_bytes_final,
            'hash_estado': hash_atual
        })

    if updates and not dry_run:
        aba.batch_update(updates, value_input_option='USER_ENTERED')
        time.sleep(0.5)

    return docs_compilacao


def compilar_mes_final(sheets_client, drive_idx, aba, docs_compilacao, dry_run=False):
    """Gera o documento PDF mestre da Prestação de Contas do mês:
    1. Página 1: A página renderizada da planilha (aba do mês)
    2. Páginas seguintes: Os PDFs consolidados de cada rubrica em sequência (Doc 01, Doc 02, ...)
    3. Sumário/Marcadores (TOC) com links de navegação para cada documento
    4. Cópia salva em GASTOS/compilados_finais/ e upload na pasta raiz do mês no Google Drive
    5. Célula G1 da planilha atualizada com o link direto da compilação
    """
    mes_nome = aba.title.strip()
    id_mes = drive_idx.pasta_do_mes(mes_nome)
    if not id_mes or not docs_compilacao:
        return None

    letra_mes = obter_letra_mes(mes_nome)
    nome_compilado = f"Doc {letra_mes} - Prestação de Contas - {mes_nome}.pdf"
    filhos_mes = drive_idx.listar_filhos(id_mes, apenas_pastas=False)
    existente = next((f for f in filhos_mes if f['name'] == nome_compilado), None)
    if not existente:
        existente = next(
            (f for f in filhos_mes if f['name'] == f"Prestação de Contas - {mes_nome}.pdf"
             or (f['name'].endswith(f"Prestação de Contas - {mes_nome}.pdf") and f['name'].startswith('Doc '))),
            None
        )
        if existente and not dry_run:
            try:
                drive_idx.drive.files().update(fileId=existente['id'], body={'name': nome_compilado}).execute()
                existente['name'] = nome_compilado
            except Exception:
                pass

    # Hash de integridade dos componentes da compilação
    hash_compilacao = hashlib.md5(
        '|'.join(f"{d['doc_num']}:{d['id_arquivo']}:{d.get('hash_estado', '')}" for d in docs_compilacao).encode('utf-8')
    ).hexdigest()

    if existente and existente.get('appProperties', {}).get('hash_compilacao') == hash_compilacao:
        relatorio.setdefault('compilados', []).append(f"[{mes_nome}] {nome_compilado} (inalterado)")
        print(f"  ⏩ Compilação final inalterada: {nome_compilado}")
        return existente.get('webViewLink', '')

    print(f"\n📑 Compilando documento final: {nome_compilado} (Planilha + {len(docs_compilacao)} documentos)...")
    if dry_run:
        print(f"     [DRY-RUN] Simulação: geraria compilação final '{nome_compilado}'")
        relatorio.setdefault('compilados', []).append(f"[{mes_nome}] {nome_compilado} (simulado)")
        return ""

    # 1. Exportar a aba da planilha para PDF em formato A4
    try:
        gid = aba.id
        url = (
            f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/export?"
            f"format=pdf&gid={gid}&size=A4&portrait=true&fitw=true&gridlines=false"
            f"&top_margin=0.5&bottom_margin=0.5&left_margin=0.5&right_margin=0.5"
        )
        resp = sheets_client.http_client.session.get(url)
        if resp.status_code != 200:
            print(f"     ⚠️  Não foi possível exportar a planilha para PDF (HTTP {resp.status_code})")
            return None
        doc_master = fitz.open(stream=resp.content, filetype="pdf")
    except Exception as e:
        print(f"     ⚠️  Erro ao exportar PDF da planilha: {e}")
        return None

    # 2. Montar sumário com marcadores (TOC) e mesclar os PDFs em sequência
    num_pags_planilha = len(doc_master)
    toc = [[1, f"Doc {letra_mes}1 - Planilha do Mês ({mes_nome})", 1]]
    pag_atual = num_pags_planilha + 1

    for item in docs_compilacao:
        raw_pdf = item.get('pdf_bytes')
        if not raw_pdf and item.get('id_arquivo'):
            try:
                buf = baixar(drive_idx.drive, item['id_arquivo'])
                raw_pdf = buf.getvalue()
            except Exception as e:
                print(f"     ⚠️  Erro ao baixar {item['nome_cons']}: {e}")
                continue

        if not raw_pdf:
            continue

        try:
            sub_doc = fitz.open(stream=raw_pdf, filetype="pdf")
            qtd_pags = len(sub_doc)
            doc_master.insert_pdf(sub_doc)
            titulo_toc = f"{item['doc_num']} - Comprovantes - {item['rubrica']} ({item['tipo']})"
            toc.append([1, titulo_toc, pag_atual])
            pag_atual += qtd_pags
            sub_doc.close()
        except Exception as e:
            print(f"     ⚠️  Erro ao mesclar {item['nome_cons']}: {e}")

    try:
        doc_master.set_toc(toc)
    except Exception:
        pass

    doc_master.set_metadata({
        'title': f'Doc {letra_mes} - Prestação de Contas - {mes_nome}',
        'author': 'Prestação de Contas',
        'subject': f'Planilha (Doc {letra_mes}1) + {len(docs_compilacao)} documentos de comprovantes'
    })

    out_bytes = doc_master.tobytes(garbage=4, deflate=True)
    total_pags = len(doc_master)
    doc_master.close()

    # 3. Salvar cópia local
    pasta_compilados = os.path.join(os.path.dirname(__file__), 'compilados_finais')
    os.makedirs(pasta_compilados, exist_ok=True)
    caminho_local = os.path.join(pasta_compilados, nome_compilado)
    with open(caminho_local, 'wb') as f_out:
        f_out.write(out_bytes)

    # 4. Upload para o Google Drive na pasta raiz do mês
    media = MediaIoBaseUpload(io.BytesIO(out_bytes), mimetype='application/pdf', resumable=True)
    props = {'appProperties': {'hash_compilacao': hash_compilacao}}
    if existente:
        f_drive = drive_idx.drive.files().update(
            fileId=existente['id'], body=props, media_body=media, fields='id, name, webViewLink, appProperties'
        ).execute()
    else:
        f_drive = drive_idx.drive.files().create(
            body={'name': nome_compilado, 'parents': [id_mes], **props},
            media_body=media, fields='id, name, webViewLink, appProperties'
        ).execute()
        try:
            drive_idx.drive.permissions().create(fileId=f_drive['id'], body={'type': 'anyone', 'role': 'reader'}).execute()
        except Exception:
            pass

    link_compilado = f_drive.get('webViewLink', '')
    drive_idx.adicionar_arquivo(f_drive)

    # 5. Atualizar célula G1 da planilha com o link direto da compilação completa
    try:
        aba.update_acell('G1', f'=HYPERLINK("{link_compilado}"; "📄 Doc {letra_mes} - Compilação Completa")')
    except Exception:
        pass

    print(f"  ✅ Compilação final salva: {nome_compilado} ({total_pags} págs, {len(out_bytes)//1024} KB)")
    print(f"     📁 Local: {caminho_local}")
    print(f"     🔗 Drive: {link_compilado}")

    relatorio.setdefault('compilados', []).append(f"[{mes_nome}] {nome_compilado} ({total_pags} págs)")
    return link_compilado


def consolidar_tudo(sheets_client, drive_idx, so_mes=None, dry_run=False, triagem=None, compilar=True):
    planilha = sheets_client.open_by_key(ID_PLANILHA)
    print(f"\n🚀 CONSOLIDAÇÃO {'(DRY-RUN) ' if dry_run else ''}...")
    for aba in planilha.worksheets():
        if so_mes and aba.title.strip() != so_mes:
            continue
        docs_mes = consolidar_aba(drive_idx, aba, dry_run=dry_run)
        if compilar and docs_mes:
            compilar_mes_final(sheets_client, drive_idx, aba, docs_mes, dry_run=dry_run)

    print('\n' + '=' * 60)
    print(f"📊 RELATÓRIO {'(DRY-RUN — nada foi gravado)' if dry_run else 'FINAL'}")
    print('=' * 60)
    for chave, titulo in (('compilados', '📑 Compilações Finais do Mês (Planilha + Comprovantes)'),
                          ('criados', '🆕 Novos'), ('atualizados', '🔄 Atualizados'),
                          ('duplicados', '♊ Duplicatas exatas descartadas/ignoradas'),
                          ('substituidos', '🔄 Versões antigas substituídas pelo último subido'),
                          ('sem_valor', '❓ Arquivos sem valor no nome')):
        print(f'\n{titulo}: {len(relatorio.get(chave, []))}')
        for item in relatorio.get(chave, []):
            print(f'   - {item}')
    print(f"\n⏩ Inalterados (já consolidados com mesmo hash): {relatorio['ignorados']}")

    if triagem:
        pendentes = [t for t in triagem if t.get('status') != 'COMPLETO']
        if pendentes:
            print('\n' + '=' * 60)
            print('⚠️  PAINEL DE TRIAGEM (AÇÕES PENDENTES PARA VOCÊ / ISA)')
            print('=' * 60)
            for p in pendentes:
                print(f"   [{p['status']}] {p['nome_original']} -> {p['nome_sugerido']}")
                print(f"      📍 Onde foi guardado: {p.get('pasta_mes_drive') or '[QUARENTENA]'}")
                print(f"      ℹ️  O que falta fazer: {p.get('aviso')}")

    # Painel de conferência: O que já está documentado e o que falta por mês
    print('\n' + '=' * 60)
    print('📋 MAPA DE STATUS POR MÊS (DOCUMENTADOS vs PENDENTES)')
    print('=' * 60)
    rubricas_conferir = ['Aluguel', 'Luz', 'Água', 'Internet', 'Faxina/Limpeza', 'Mercado/Açougue/Padaria', 'Transporte', 'Escola']
    for aba in planilha.worksheets():
        m_nome = aba.title.strip()
        if not any(m_nome.startswith(m) for m in comum.MESES):
            continue
        dados = aba.get_all_values()
        valores_mes = {}
        for linha in dados:
            if len(linha) > 2 and linha[1].strip() and linha[2].strip():
                valores_mes[linha[1].strip()] = linha[2].strip()

        itens_status = []
        for r in rubricas_conferir:
            if r in valores_mes:
                itens_status.append(f"{r}: ✅ R$ {valores_mes[r]}")
            elif r in comum.RUBRICAS_CONTA_UNICA or r == 'Faxina/Limpeza':
                itens_status.append(f"{r}: ❌")

        print(f"📅 [{m_nome}]")
        for chunk in [itens_status[i:i+4] for i in range(0, len(itens_status), 4)]:
            print("   " + " | ".join(chunk))
        print()
    print('=' * 60 + '\n')


def main():
    comum.configurar_stdout()
    caminho_hist, caminho_ult = iniciar_logger()
    print(f"📝 Registrando log de execução em:")
    print(f"   -> {caminho_ult}")
    print(f"   -> {caminho_hist}\n")

    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--oauth', action='store_true', help='abrir navegador para renovar OAuth do usuário')
    ap.add_argument('--ate', default=f'{MES_ALVO_PADRAO[0]}-{MES_ALVO_PADRAO[1]:02d}', help='AAAA-MM')
    ap.add_argument('--mes', help='consolidar só esta aba, ex: "Maio 2026"')
    ap.add_argument('--sem-meses', action='store_true', help='não gerar meses faltantes')
    ap.add_argument('--sem-compilar', action='store_true', help='não gerar o PDF compilado final do mês')
    args = ap.parse_args()
    ate = tuple(int(x) for x in args.ate.split('-'))

    sheets_client, drive, tipo = comum.conectar(permitir_login=args.oauth)
    print(f'🔑 Credencial: {tipo}')
    print('⚡ Carregando índice do Drive...')
    drive_idx = DriveIndex(drive)
    print(f'   {len(drive_idx.by_id)} objetos indexados.')

    if not args.sem_meses:
        comum.garantir_meses(sheets_client, drive_idx, ate=ate, dry_run=args.dry_run)
        drive_idx.recarregar()

    import classificador
    movidos, triagem = classificador.organizar_arquivos_raiz_drive(drive, drive_idx, dry_run=args.dry_run)
    if movidos > 0 and not args.dry_run:
        drive_idx.recarregar()

    consolidar_tudo(
        sheets_client, drive_idx, so_mes=args.mes, dry_run=args.dry_run, triagem=triagem, compilar=not args.sem_compilar
    )


if __name__ == '__main__':
    main()
