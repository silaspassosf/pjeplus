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
from comum import (BLOCO_A, BLOCO_B, BLOCO_I, BLOCO_II, MES_ALVO_PADRAO, ID_PLANILHA, DriveIndex,
                   gerar_prefixo_mes, normalizar, RE_CONSOLIDADO, obter_letra_mes,
                   eh_mes_no_periodo, PERIODO_ATIVO_INICIO, PERIODO_ATIVO_FIM)
from extrato import extrato_geral, parse_extrato_pdf, obter_arquivo_extrato_drive


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
RE_VALOR_RS_INT = re.compile(r'R\$\s*(\d{1,3}(?:\.\d{3})+|\d{1,4})(?![\d.,])')
RE_VALOR = re.compile(r'(?<![\d.,])(\d+)[.,](\d{2})(?![\d])')
RE_VALOR_INT_EXATO = re.compile(r'^(\d{1,4})(?:\s*\(\d+\))?$')
RE_VALOR_INT_PREFIXO = re.compile(r'^(\d{1,4})\s+[A-Za-zÀ-ÿ\[]')

relatorio = {
    'criados': [], 'atualizados': [], 'ignorados': 0,
    'duplicados': [], 'substituidos': [], 'blindados_manuais': [],
    'sem_valor': [], 'compilados': [],
}


def higienizar_nome(nome):
    return re.sub(r'[\\/*?:"<>|]', '-', nome)[:80].strip()


def formatar_nome_consolidado(rubrica, bloco, mes_nome, doc_str):
    """Padrão: Doc A2 - Comprovantes - (nome da despesa/Individual ou geral) - mes/ano"""
    tipo_bloco = 'Individual' if bloco in ('I', 'A') else 'Geral'
    rubrica_limpa = higienizar_nome(rubrica)
    if f'({tipo_bloco})' in rubrica_limpa:
        return f'{doc_str} - Comprovantes - {rubrica_limpa} - {mes_nome}.pdf'
    return f'{doc_str} - Comprovantes - {rubrica_limpa} ({tipo_bloco}) - {mes_nome}.pdf'


def extrair_valor_do_nome(nome_arquivo):
    # Remove timestamps completos do WhatsApp (ex: WhatsApp Image 2026-10-26 at 17.52.23 (1)) e padrões de hora/data
    nome_limpo = re.sub(
        r'WhatsApp\s+(?:Image|Video|Audio|Document|Doc)\s+\d{4}-\d{2}-\d{2}\s+at\s+\d{1,2}[._:]\d{2}[._:]\d{2}(?:\s*\(\d+\))?',
        'whatsapp',
        nome_arquivo,
        flags=re.IGNORECASE,
    )
    nome_limpo = re.sub(r'WhatsApp Image \d{4}-\d{2}-\d{2}[^.]*', 'whatsapp', nome_limpo, flags=re.IGNORECASE)
    nome_limpo = re.sub(r'\bat\s+\d{1,2}[.]\d{2}(?:[.]\d{2})?\b', '', nome_limpo, flags=re.IGNORECASE)
    nome_limpo = re.sub(r'\b\d{2}[.]\d{2}[.]\d{2}\b', '', nome_limpo)
    m = RE_VALOR_RS.search(nome_limpo)
    if m:
        bruto = m.group(1)
        if ',' in bruto:
            bruto = bruto.replace('.', '').replace(',', '.')
        return float(bruto)
    m = RE_VALOR.search(nome_limpo)
    if m:
        return float(f'{m.group(1)}.{m.group(2)}')

    # Fallback para valores inteiros sem centavos (ex: '127.jpeg', '100.jpeg', '190.pdf', '10.jpeg', '250 recibo.jpg')
    stem = os.path.splitext(nome_limpo)[0].strip()
    m_rs_int = RE_VALOR_RS_INT.search(stem)
    if m_rs_int:
        return float(m_rs_int.group(1).replace('.', ''))
    m_int = RE_VALOR_INT_EXATO.match(stem)
    if m_int:
        return float(m_int.group(1))
    m_pref = RE_VALOR_INT_PREFIXO.match(stem)
    if m_pref:
        val_int = int(m_pref.group(1))
        if not (2020 <= val_int <= 2035):
            return float(val_int)
    return 0.0


def fmt_br(v):
    return f'{v:.2f}'.replace('.', ',')


def parse_valor_celula_planilha(texto_celula):
    """Converte o texto atual da célula C da planilha (ex: 'R$ 1.040,08', '633,20', '45.4') em float."""
    if not texto_celula:
        return 0.0
    limpo = re.sub(r'[^\d,.-]', '', str(texto_celula)).strip()
    if not limpo:
        return 0.0
    if ',' in limpo:
        limpo = limpo.replace('.', '').replace(',', '.')
    try:
        return round(float(limpo), 2)
    except ValueError:
        return 0.0


VERSAO_BANNER = 'v3_camada_imagem'


def gerar_hash_estado(arquivos_fonte, versao=VERSAO_BANNER):
    if not arquivos_fonte:
        return 'VAZIO'
    assinaturas = sorted(f"{a['id']}-{a.get('name', '')}-{a.get('md5Checksum', a.get('modifiedTime', ''))}" for a in arquivos_fonte)
    return hashlib.md5(f"{versao}|{'|'.join(assinaturas)}".encode('utf-8')).hexdigest()


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
            # Conta única: substitui apenas versões antigas sem valor ou com valor muito próximo.
            # Comprovantes com valores distintos nunca são descartados automaticamente.
            oficial = fontes[0]
            v_oficial = extrair_valor_do_nome(oficial['name'])
            mantidos = [oficial]
            for antigo in fontes[1:]:
                v_antigo = extrair_valor_do_nome(antigo['name'])
                if v_antigo == 0.0 or (v_oficial > 0 and comum.valores_muito_proximos(v_oficial, v_antigo)):
                    relatorio['substituidos'].append(
                        f"{rotulo}: '{antigo['name']}' substituído por '{oficial['name']}' (versão mais recente mantida)"
                    )
                    if not dry_run:
                        try:
                            drive_idx.drive.files().update(fileId=antigo['id'], body={'trashed': True}).execute()
                            drive_idx.remover_arquivo(antigo['id'])
                        except Exception:
                            pass
                else:
                    mantidos.append(antigo)
            fontes = mantidos
        else:
            # Rubricas multi-itens: NUNCA descarta comprovantes automaticamente!
            # Múltiplas despesas de mesmo valor (ex: 2 faxinas de R$ 250, vários prints/ingressos)
            # são gastos legítimos separados. Apenas duplicatas idênticas de MD5 são filtradas.
            pass

    return fontes, consolidado


def baixar(drive, id_arquivo):
    buf = io.BytesIO()
    dl = MediaIoBaseDownload(buf, drive.files().get_media(fileId=id_arquivo))
    done = False
    while not done:
        _, done = dl.next_chunk()
    buf.seek(0)
    return buf


def formatar_titulo_cabecalho(str_doc, mes_nome, rubrica):
    partes = mes_nome.split()
    if len(partes) >= 2:
        m_txt = partes[0]
        ano_txt = partes[1][-2:] if len(partes[1]) >= 2 else partes[1]
        mes_ano = f"{m_txt}/{ano_txt}"
    else:
        mes_ano = mes_nome
    return f"{str_doc.upper()} — {mes_ano.upper()} — {rubrica.upper()}"


def montar_pdf(drive, arquivos, str_doc=None, mes_nome=None, rubrica=None, bloco=None, nota_extrato=None):
    paginas_fonte = []  # tuplas: ('pdf', doc_fitz, pno, meta_custom) ou ('img', raw_bytes, 0, meta_custom)
    docs_abertos = []
    vistos_hashes_visuais = set()

    for arq in arquivos:
        dados = baixar(drive, arq['id'])
        raw = dados.getvalue()
        meta_custom = {
            'titulo': arq.get('_titulo_custom'),
            'subtitulo': arq.get('_subtitulo_custom'),
            'nota': arq.get('_nota_custom'),
        }
        if arq.get('mimeType') == 'application/pdf' or raw[:4] == b'%PDF':
            try:
                sub_doc = fitz.open(stream=raw, filetype="pdf")
                docs_abertos.append(sub_doc)
                for pno in range(len(sub_doc)):
                    # Deduplicação visual para evitar páginas ou comprovantes repetidos
                    try:
                        pix = sub_doc[pno].get_pixmap(dpi=36)
                        img_pil = Image.open(io.BytesIO(pix.tobytes("png"))).convert('RGB')
                        h_vis = hashlib.md5(img_pil.resize((150, 150)).tobytes()).hexdigest()
                        if h_vis in vistos_hashes_visuais:
                            print(f"     ✂️  [Deduplicação] Página {pno+1} idêntica ignorada em '{arq['name']}'")
                            continue
                        vistos_hashes_visuais.add(h_vis)
                    except Exception:
                        pass
                    paginas_fonte.append(('pdf', sub_doc, pno, meta_custom))
            except Exception as e:
                print(f"     ⚠️  Aviso ao ler PDF {arq['name']}: {e}")
        else:
            try:
                img_pil = Image.open(io.BytesIO(raw)).convert('RGB')
                h_vis = hashlib.md5(img_pil.resize((150, 150)).tobytes()).hexdigest()
                if h_vis in vistos_hashes_visuais:
                    print(f"     ✂️  [Deduplicação] Imagem idêntica ignorada em '{arq['name']}'")
                    continue
                vistos_hashes_visuais.add(h_vis)
            except Exception:
                h_raw = hashlib.md5(raw).hexdigest()
                if h_raw in vistos_hashes_visuais:
                    print(f"     ✂️  [Deduplicação] Imagem (bytes) idêntica ignorada em '{arq['name']}'")
                    continue
                vistos_hashes_visuais.add(h_raw)
            paginas_fonte.append(('img', raw, 0, meta_custom))

    if not paginas_fonte:
        doc_vazio = fitz.open()
        out = io.BytesIO(doc_vazio.tobytes())
        doc_vazio.close()
        return out

    doc_final = fitz.open()
    total_pags = len(paginas_fonte)
    tem_cabecalho = bool(str_doc and mes_nome and rubrica)

    if tem_cabecalho:
        titulo = formatar_titulo_cabecalho(str_doc, mes_nome, rubrica)
        tipo_desc = 'Despesa Individual da Alimentanda (100%)' if bloco in ('I', 'A') else 'Despesa Geral da Casa (Rateio 1/3)'

    for idx, (tipo_src, obj, pno, meta_custom) in enumerate(paginas_fonte):
        # Monta a página em um documento temporário e rasteriza em camada única de imagem
        # para garantir que nenhum texto ou objeto por trás de tarjas seja editável ou selecionável.
        doc_temp = fitz.open()
        page_temp = doc_temp.new_page(width=595.32, height=841.92)

        if tem_cabecalho:
            tit_pag = meta_custom.get('titulo') or titulo
            nota_pag = meta_custom.get('nota') if meta_custom.get('nota') is not None else nota_extrato
            subtit_base = meta_custom.get('subtitulo') or tipo_desc
            subtit_pag = subtit_base
            if total_pags > 1:
                subtit_pag += f"  |  Página {idx+1} de {total_pags}"

            # 1. Banner de Cabeçalho (Marinho Nobre + Linha Dourada)
            altura_banner = 68 if nota_pag else 55
            banner_rect = fitz.Rect(0, 0, 595.32, altura_banner)
            page_temp.draw_rect(banner_rect, color=(0.10, 0.22, 0.45), fill=(0.10, 0.22, 0.45))
            page_temp.draw_line(fitz.Point(0, altura_banner - 1), fitz.Point(595.32, altura_banner - 1), color=(0.85, 0.65, 0.15), width=2)

            if nota_pag:
                page_temp.insert_text(fitz.Point(20, 22), tit_pag, fontname="helv", fontsize=10.5, color=(1, 1, 1))
                page_temp.insert_text(fitz.Point(20, 38), subtit_pag, fontname="helv", fontsize=8.5, color=(0.85, 0.90, 1.0))
                page_temp.insert_text(fitz.Point(20, 55), f"(*) {nota_pag}", fontname="helv", fontsize=8, color=(1.0, 0.90, 0.50))
                conteudo_rect = fitz.Rect(20, altura_banner + 10, 575.32, 825)
            else:
                page_temp.insert_text(fitz.Point(20, 26), tit_pag, fontname="helv", fontsize=11.5, color=(1, 1, 1))
                page_temp.insert_text(fitz.Point(20, 44), subtit_pag, fontname="helv", fontsize=9, color=(0.85, 0.90, 1.0))
                conteudo_rect = fitz.Rect(20, 65, 575.32, 825)
        else:
            conteudo_rect = fitz.Rect(20, 20, 575.32, 822)

        if tipo_src == 'pdf':
            page_temp.show_pdf_page(conteudo_rect, obj, pno)
        else:
            try:
                page_temp.insert_image(conteudo_rect, stream=obj, keep_proportion=True)
            except Exception:
                try:
                    img_pil = Image.open(io.BytesIO(obj)).convert('RGB')
                    buf_temp = io.BytesIO()
                    img_pil.save(buf_temp, format='JPEG', quality=90)
                    page_temp.insert_image(conteudo_rect, stream=buf_temp.getvalue(), keep_proportion=True)
                except Exception as e_img:
                    print(f"     ⚠️  Aviso ao inserir imagem: {e_img}")

        # Achata (rasteriza) a página inteira em camada exclusiva de imagem (sem texto selecionável/editável)
        pix_flat = page_temp.get_pixmap(dpi=200, alpha=False)
        img_flat_pil = Image.open(io.BytesIO(pix_flat.tobytes("png"))).convert('RGB')
        buf_flat = io.BytesIO()
        img_flat_pil.save(buf_flat, format='JPEG', quality=92, optimize=True)
        doc_temp.close()

        page_final = doc_final.new_page(width=595.32, height=841.92)
        page_final.insert_image(fitz.Rect(0, 0, 595.32, 841.92), stream=buf_flat.getvalue())

    for d in docs_abertos:
        try:
            d.close()
        except Exception:
            pass

    out = io.BytesIO(doc_final.tobytes(garbage=4, deflate=True))
    doc_final.close()
    out.seek(0)
    return out


def upload_consolidado(drive, nome_arquivo, pdf_bytes, id_pasta, hash_pasta, existente, extra_props=None):
    media = MediaIoBaseUpload(pdf_bytes, mimetype='application/pdf', resumable=True)
    app_props = {'hash_estado': hash_pasta}
    if extra_props:
        app_props.update(extra_props)
    props = {'appProperties': app_props}
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


def carregar_mapa_extratos_gerais(drive, drive_idx):
    """Carrega extratos gerais consolidados multimês (ex: Banco Inter na raiz de Janeiro 2026
    e Cantina Escolar em 'Alimentação rua e Cantina Escolar' de Janeiro 2026).
    """
    mapa = {}
    arq = obter_arquivo_extrato_drive(drive, drive_idx, 'Janeiro 2026')
    if arq:
        try:
            from extrato import baixar_arquivo_drive, parse_extrato_pdf
            dados = baixar_arquivo_drive(drive, arq['id'])
            txs, totais, total_geral = parse_extrato_pdf(dados)
            totais_por_nome = {}
            for (ano, mes), v in totais.items():
                totais_por_nome[f"{comum.MESES[mes - 1]} {ano}"] = v
            mapa[normalizar('Mercado/Açougue/Padaria')] = {
                'arquivo': arq,
                'link': arq.get('webViewLink', ''),
                'totais_por_mes_nome': totais_por_nome,
                'total_geral': total_geral
            }
        except Exception as e:
            print(f"⚠️  Aviso ao carregar extrato geral: {e}")

    try:
        from extrato import baixar_arquivo_drive, obter_arquivo_cantina_drive, parse_extrato_cantina
        arq_cantina = obter_arquivo_cantina_drive(drive, drive_idx, 'Janeiro 2026')
        if arq_cantina:
            dados_cantina = baixar_arquivo_drive(drive, arq_cantina['id'])
            txs_c, totais_c, total_geral_c = parse_extrato_cantina(dados_cantina)
            totais_c_nome = {}
            for (ano, mes), v in totais_c.items():
                totais_c_nome[f"{comum.MESES[mes - 1]} {ano}"] = v
            mapa[normalizar('Alimentação rua e Cantina Escolar')] = {
                'arquivo': arq_cantina,
                'link': arq_cantina.get('webViewLink', ''),
                'totais_por_mes_nome': totais_c_nome,
                'total_geral': total_geral_c
            }
    except Exception as e_c:
        print(f"⚠️  Aviso ao carregar extrato cantina: {e_c}")

    try:
        from extrato import obter_escola_parcelado_drive
        info_escola = obter_escola_parcelado_drive(drive, drive_idx, 'Janeiro 2026')
        if info_escola:
            mapa[normalizar('Escola')] = info_escola
    except Exception as e_esc:
        print(f"⚠️  Aviso ao carregar comprovante parcelado de Escola: {e_esc}")

    return mapa


def garantir_linhas_outros(drive_idx, aba, pastas, dados, dry_run=False):
    """Linhas 'Outros (Individual/Geral) NN' só existem na planilha quando há valor registrado.

    Se uma pasta 'Outros ...' do Drive recebeu comprovantes e a aba não tem a linha correspondente
    (ex.: removida na limpeza de linhas vazias), insere a linha dentro do intervalo do subtotal do bloco
    (sempre acima da última linha do bloco, para os SUM() do subtotal se expandirem) e devolve os dados relidos.
    """
    re_outros = re.compile(r'^outros \((individual|geral)\) (\d+)$')
    linhas_existentes = {normalizar(l[1]) for l in dados if len(l) > 1 and str(l[1]).strip()}

    faltantes = {'I': [], 'II': []}
    for chave in ('I', 'II'):
        for nome_norm, id_pasta in pastas.get(chave, {}).items():
            m = re_outros.match(nome_norm)
            if not m or nome_norm in linhas_existentes:
                continue
            tem_arquivos = any(
                eh_comprovante(f) and not comum.RE_CONSOLIDADO.match(f['name'])
                for f in drive_idx.listar_filhos(id_pasta, apenas_pastas=False)
            )
            if tem_arquivos:
                rotulo_linha = f"Outros ({'Individual' if m.group(1) == 'individual' else 'Geral'}) {int(m.group(2)):02d}"
                faltantes[chave].append((int(m.group(2)), rotulo_linha))

    if not faltantes['I'] and not faltantes['II']:
        return dados

    for chave, tipo in (('II', 'Geral'), ('I', 'Individual')):  # de baixo para cima: não desloca o bloco acima
        for _, rotulo_linha in sorted(faltantes[chave], reverse=True):
            print(f"  ➕ [{aba.title.strip()}] linha '{rotulo_linha}' inserida na planilha (há comprovantes na pasta do Drive)")
            if dry_run:
                continue
            linha_subtotal = None
            bloco_atual = None
            for i, l in enumerate(dados, 1):
                c0 = str(l[0]).strip() if len(l) > 0 else ''
                rub = str(l[1]).strip() if len(l) > 1 else ''
                if 'DESPESAS INDIVIDUAIS' in c0:
                    bloco_atual = 'I'
                elif 'DESPESAS GERAIS' in c0:
                    bloco_atual = 'II'
                elif rub.startswith('Subtotal') and bloco_atual == chave:
                    linha_subtotal = i
                    break
            if not linha_subtotal:
                continue
            pos = linha_subtotal - 1  # 1-based da última linha do bloco; nova linha entra acima dela
            aba.spreadsheet.batch_update({'requests': [{'insertDimension': {
                'range': {'sheetId': aba.id, 'dimension': 'ROWS', 'startIndex': pos - 1, 'endIndex': pos},
                'inheritFromBefore': True,
            }}]})
            formula_d = f'=IF(C{pos}=""; ""; C{pos})' if chave == 'I' else f'=IF(C{pos}=""; ""; ROUND(C{pos}/3; 2))'
            aba.batch_update([{'range': f'B{pos}:D{pos}', 'values': [[rotulo_linha, '', formula_d]]}],
                             value_input_option='USER_ENTERED')
            dados = aba.get_all_values()
    return aba.get_all_values() if not dry_run else dados


def consolidar_aba(drive_idx, aba, dry_run=False, mapa_extrato_geral=None):
    drive = drive_idx.drive
    mes_nome = aba.title.strip()
    id_mes = drive_idx.pasta_do_mes(mes_nome)
    if not id_mes:
        return []

    pastas = {}
    for bloco_nome, chave in ((BLOCO_I, 'I'), (BLOCO_II, 'II')):
        nomes_comp = [bloco_nome]
        if chave == 'I':
            nomes_comp += ['Bloco I - Individuais', 'Bloco A - Individuais', 'Grupo I - Individuais']
        else:
            nomes_comp += ['Bloco II - Gerais', 'Bloco B - Gerais', 'Grupo II - Gerais']
        blocos = [f for f in drive_idx.listar_filhos(id_mes, apenas_pastas=True) if f['name'] in nomes_comp]
        if blocos:
            pastas[chave] = {normalizar(f['name']): f['id']
                             for f in drive_idx.listar_filhos(blocos[0]['id'], apenas_pastas=True)
                             if not f['name'].startswith('[LIXO')}
        else:
            pastas[chave] = {}

    dados = aba.get_all_values()
    dados = garantir_linhas_outros(drive_idx, aba, pastas, dados, dry_run=dry_run)
    letra_mes = obter_letra_mes(mes_nome)
    bloco, updates, doc = None, [], 2  # Doc {letra}1 é a planilha do mês! As despesas iniciam em Doc {letra}2...
    docs_compilacao = []

    for i, linha in enumerate(dados):
        ln = i + 1
        c0 = linha[0].strip() if len(linha) > 0 else ''
        rubrica = linha[1].strip() if len(linha) > 1 else ''
        if 'DESPESAS INDIVIDUAIS' in c0:
            bloco = 'I'
            continue
        if 'DESPESAS GERAIS' in c0:
            bloco = 'II'
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
        tipo_bloco = 'Individual' if bloco in ('I', 'A') else 'Geral'
        str_doc = f'Doc {letra_mes}{doc}'
        nome_cons = formatar_nome_consolidado(rubrica, bloco, mes_nome, str_doc)
        fontes, consolidado = classificar_arquivos_da_pasta(
            drive_idx, id_pasta, nome_cons, rotulo, rubrica=rubrica, dry_run=dry_run
        )

        # Suporte a Extrato Geral Consolidado / Parcelamento Multimês (ex: Mercado, Cantina Escolar, Escola)
        val_extrato = 0.0
        link_extrato = ""
        id_arq_extrato = ""
        nota_custom_extrato = None
        if mapa_extrato_geral and normalizar(rubrica) in mapa_extrato_geral:
            info_ext = mapa_extrato_geral[normalizar(rubrica)]
            val_extrato = info_ext.get('totais_por_mes_nome', {}).get(mes_nome, 0.0)
            link_extrato = info_ext.get('link', '')
            id_arq_extrato = (info_ext.get('arquivo') or {}).get('id', '')
            nota_custom_extrato = info_ext.get('notas_por_mes_nome', {}).get(mes_nome)

        if not fontes and val_extrato <= 0:
            continue

        doc += 1
        com_valor, sem_valor, soma_arquivos = [], [], 0.0
        for a in fontes:
            if (id_arq_extrato and a['id'] == id_arq_extrato) or ('cantina' in a['name'].lower() and val_extrato > 0):
                # O valor do mês deste comprovante multimês já entra via val_extrato; inclui páginas no PDF sem duplicar soma
                com_valor.append(a)
                continue
            v = extrair_valor_do_nome(a['name'])
            if v > 0:
                soma_arquivos += v
                com_valor.append(a)
            else:
                sem_valor.append(a)

        soma_auto = round(soma_arquivos + val_extrato, 2)
        valor_planilha_atual = parse_valor_celula_planilha(linha[2] if len(linha) > 2 else '')

        nota_extrato = None
        if val_extrato > 0:
            nota_extrato = nota_custom_extrato or f"Há no mês o valor de R$ {fmt_br(val_extrato)} a partir do extrato consolidado de Janeiro/26"

        eh_mercado_janeiro = (
            mes_nome == 'Janeiro 2026'
            and normalizar(rubrica) == normalizar('Mercado/Açougue/Padaria')
            and mapa_extrato_geral
            and normalizar(rubrica) in mapa_extrato_geral
            and bool((mapa_extrato_geral[normalizar(rubrica)].get('arquivo')))
        )

        fontes_para_hash = list(fontes)
        if eh_mercado_janeiro:
            fontes_para_hash.append(mapa_extrato_geral[normalizar(rubrica)]['arquivo'])

        hash_atual = gerar_hash_estado(fontes_para_hash, versao=f"{VERSAO_BANNER}_interv2_ext{val_extrato}")
        app_props = dict((consolidado or {}).get('appProperties') or {})
        hash_salvo = app_props.get('hash_estado', '')
        hash_sv_salvo = app_props.get('hash_sv', '')
        soma_auto_salva_str = app_props.get('soma_auto', '')
        parc_man_salva = round(float(app_props.get('parc_man', '0') or 0.0), 2)
        qtd_sv_salva = int(app_props.get('qtd_sv', '0') or 0)

        parcela_manual = 0.0
        novo_sv_pendente = False
        hash_sv_atual = gerar_hash_estado(sem_valor, versao='sv1') if sem_valor else ''
        hash_sv_para_salvar = hash_sv_atual

        # Blindagem por padrão de valores preenchidos manualmente na planilha:
        # 1) Se há arquivos sem valor no nome e a planilha já possui registro manual (> soma_auto ou salvo em appProperties),
        #    preserva a parcela manual sem exigir renomeação dos arquivos e soma novos comprovantes com valor por cima.
        # 2) Se todos os arquivos já estavam consolidados com mesmo hash e soma_auto, preserva eventual ajuste manual na célula.
        if sem_valor:
            if hash_atual == hash_salvo or not hash_sv_salvo or hash_sv_atual != hash_sv_salvo:
                if valor_planilha_atual > soma_auto:
                    parcela_manual = round(valor_planilha_atual - soma_auto, 2)
                elif parc_man_salva > 0 and hash_sv_atual == hash_sv_salvo:
                    parcela_manual = parc_man_salva
                elif parc_man_salva > 0 and valor_planilha_atual > 0:
                    parcela_manual = parc_man_salva

                if (hash_sv_salvo and hash_sv_atual != hash_sv_salvo
                        and len(sem_valor) >= qtd_sv_salva
                        and abs(parcela_manual - parc_man_salva) < 0.005):
                    novo_sv_pendente = True
                    hash_sv_para_salvar = hash_sv_salvo
            else:
                # hash_atual != hash_salvo e hash_sv_atual == hash_sv_salvo:
                # Os arquivos sem valor não mudaram, mas entraram/mudaram comprovantes COM valor
                if soma_auto_salva_str != '':
                    soma_auto_antiga = round(float(soma_auto_salva_str), 2)
                    if valor_planilha_atual > soma_auto_antiga:
                        parcela_manual = round(valor_planilha_atual - soma_auto_antiga, 2)
                    elif parc_man_salva > 0:
                        parcela_manual = parc_man_salva
                elif parc_man_salva > 0:
                    parcela_manual = parc_man_salva
                elif valor_planilha_atual > soma_auto:
                    parcela_manual = round(valor_planilha_atual - soma_auto, 2)
        elif (consolidado and hash_atual == hash_salvo
              and soma_auto_salva_str == f'{soma_auto:.2f}'
              and valor_planilha_atual > 0
              and abs(valor_planilha_atual - soma_auto) >= 0.01):
            parcela_manual = round(valor_planilha_atual - soma_auto, 2)

        soma = round(soma_auto + parcela_manual, 2)
        individual = soma if bloco in ('I', 'A') else round(soma / 3, 2)

        if sem_valor:
            if parcela_manual > 0 and not novo_sv_pendente:
                detalhe_auto = f'R$ {fmt_br(soma_auto)} auto + ' if soma_auto > 0 else ''
                relatorio['blindados_manuais'].append(
                    f'{rotulo} {str_doc}: R$ {fmt_br(soma)} preservado ({detalhe_auto}R$ {fmt_br(parcela_manual)} manual p/ {len(sem_valor)} arq)'
                )
            else:
                if parcela_manual > 0 and novo_sv_pendente:
                    relatorio['blindados_manuais'].append(
                        f'{rotulo} {str_doc}: R$ {fmt_br(soma)} preservado, mas há novo arq sem valor pendente de ajuste'
                    )
                for a in sem_valor:
                    relatorio['sem_valor'].append({
                        'rotulo': rotulo,
                        'mes': mes_nome,
                        'rubrica': rubrica,
                        'bloco': tipo_bloco,
                        'nome': a['name'],
                        'id': a['id'],
                        'link': a.get('webViewLink') or f"https://drive.google.com/file/d/{a['id']}/view"
                    })
        elif parcela_manual != 0:
            relatorio['blindados_manuais'].append(
                f'{rotulo} {str_doc}: R$ {fmt_br(soma)} preservado (ajuste manual na planilha; soma arquivos R$ {fmt_br(soma_auto)})'
            )

        extra_props = {
            'hash_sv': hash_sv_para_salvar,
            'soma_auto': f'{soma_auto:.2f}',
            'parc_man': f'{parcela_manual:.2f}',
            'qtd_sv': str(len(sem_valor)),
        }

        id_cons_final = None
        pdf_bytes_final = None

        if not fontes:
            link = link_extrato
            id_cons_final = (mapa_extrato_geral.get(normalizar(rubrica), {}).get('arquivo') or {}).get('id', '')
            print(f"  📄 {rotulo} -> {str_doc} | Extrato Geral (Janeiro 2026 - RAIZ) | R$ {fmt_br(soma)}")
        elif consolidado and hash_atual == hash_salvo:
            relatorio['ignorados'] += 1
            link = consolidado.get('webViewLink', '')
            id_cons_final = consolidado['id']
            precisa_sync_props = (
                not dry_run
                and (sem_valor or parcela_manual != 0 or app_props.get('hash_sv') or app_props.get('parc_man') not in (None, '', '0.00'))
                and any(app_props.get(k, '') != v for k, v in extra_props.items())
            )
            if precisa_sync_props:
                try:
                    novas_props = {'hash_estado': hash_atual, **extra_props}
                    drive.files().update(
                        fileId=consolidado['id'],
                        body={'appProperties': novas_props},
                        fields='id, appProperties',
                    ).execute()
                    consolidado['appProperties'] = novas_props
                except Exception as e_prop:
                    print(f"     ⚠️  Aviso ao sincronizar metadados de blindagem ({e_prop})")
        else:
            acao = 'atualizados' if consolidado else 'criados'
            print(f"  {'🔄' if consolidado else '🆕'} {rotulo} -> {str_doc} | {len(fontes)} arq | R$ {fmt_br(soma)}")
            relatorio[acao].append(f'{rotulo} {str_doc} (R$ {fmt_br(soma)})')
            if dry_run:
                link = (consolidado or {}).get('webViewLink', '<novo>')
                id_cons_final = (consolidado or {}).get('id', '')
            else:
                try:
                    arquivos_para_pdf = list(sem_valor + com_valor)
                    if eh_mercado_janeiro:
                        arq_inter = dict(mapa_extrato_geral[normalizar(rubrica)]['arquivo'])
                        arq_inter['_titulo_custom'] = "Extrato consolidado banco inter - TOTAL do período - R$ 3.121,60"
                        arq_inter['_subtitulo_custom'] = "Despesa Geral da Casa (Rateio 1/3)  |  Compras Físicas Alimentação"
                        arq_inter['_nota_custom'] = "Contabilizado mês a mês na planilha conforme a data de cada compra"
                        arquivos_para_pdf = [arq_inter] + [a for a in arquivos_para_pdf if a.get('id') != arq_inter.get('id')]

                    pdf = montar_pdf(drive, arquivos_para_pdf, str_doc=str_doc, mes_nome=mes_nome, rubrica=rubrica, bloco=bloco, nota_extrato=nota_extrato)
                    pdf_bytes_final = pdf.getvalue()
                    f_salvo = upload_consolidado(drive, nome_cons, io.BytesIO(pdf_bytes_final), id_pasta, hash_atual, consolidado, extra_props=extra_props)
                    link = f_salvo.get('webViewLink', '')
                    id_cons_final = f_salvo.get('id', '')
                    drive_idx.adicionar_arquivo(f_salvo)
                except Exception as e:
                    print(f"     ⚠️  Não foi possível fazer upload do PDF ({e}); preservando link existente.")
                    link = (consolidado or {}).get('webViewLink', '')
                    id_cons_final = (consolidado or {}).get('id', '')

        formula_d = f'=IF(C{ln}=""; ""; C{ln})' if bloco in ('I', 'A') else f'=IF(C{ln}=""; ""; ROUND(C{ln}/3; 2))'
        val_c = fmt_br(soma) if soma else ''
        updates += [
            {'range': f'C{ln}:E{ln}', 'values': [[val_c, formula_d, str_doc]]},
            {'range': f'G{ln}', 'values': [[f'=HYPERLINK("{link}"; "Link")']] if link else [['']]},
        ]

        docs_compilacao.append({
            'doc_num': str_doc,
            'rubrica': rubrica,
            'tipo': tipo_bloco,
            'nome_cons': nome_cons,
            'id_arquivo': id_cons_final,
            'pdf_bytes': pdf_bytes_final,
            'hash_estado': hash_atual,
            'soma': fmt_br(soma),
        })

    if updates and not dry_run:
        aba.batch_update(updates, value_input_option='USER_ENTERED')
        time.sleep(0.5)

    return docs_compilacao


def _ordem_doc_num(item):
    m = re.search(r'(\d+)$', str(item.get('doc_num', '')))
    return int(m.group(1)) if m else 9999


def compilar_mes_final(sheets_client, drive_idx, aba, docs_compilacao, dry_run=False):
    """Gera o documento PDF mestre mensal na pasta separada 'Consolidado mensal' do Drive:
    1. Garante a existência da pasta 'Consolidado mensal' na raiz do Drive.
    2. Mantém estritamente 1 único arquivo por mês na pasta, nomeado 'Despesas {mes_nome}.pdf'.
    3. Junta tudo em ordem: Página 1 = Planilha do mês + Páginas seguintes = PDFs consolidados (Doc X2, Doc X3, ...).
    4. Adiciona Sumário/Marcadores (TOC), salva cópia em GASTOS/compilados_finais/ e atualiza célula G1 da planilha.
    """
    mes_nome = aba.title.strip()
    id_mes = drive_idx.pasta_do_mes(mes_nome)
    if not id_mes or not docs_compilacao:
        return None

    # Ordena estritamente em sequência (Doc X2, Doc X3, ...)
    docs_ordenados = sorted(docs_compilacao, key=_ordem_doc_num)

    letra_mes = obter_letra_mes(mes_nome)
    nome_compilado = f"Despesas {mes_nome}.pdf"

    # Garante a pasta separada "Consolidado mensal" na raiz do Drive
    id_pasta_consolidado, _ = drive_idx.obter_ou_criar_pasta(
        comum.PASTA_CONSOLIDADO_MENSAL, comum.ID_PASTA_RAIZ_DRIVE, dry_run=dry_run
    )

    filhos_cons = (
        drive_idx.listar_filhos(id_pasta_consolidado, apenas_pastas=False)
        if not str(id_pasta_consolidado).startswith('<nova:') else []
    )

    # Localiza arquivo existente daquele mês na pasta "Consolidado mensal" e remove eventuais duplicatas do mesmo mês
    candidatos_mes = [
        f for f in filhos_cons
        if f['name'].lower() == nome_compilado.lower()
        or f['name'].lower() == f"despesas ({mes_nome.lower()}).pdf"
        or mes_nome.lower() in f['name'].lower()
    ]
    existente = candidatos_mes[0] if candidatos_mes else None

    if existente and existente['name'] != nome_compilado and not dry_run:
        try:
            drive_idx.drive.files().update(fileId=existente['id'], body={'name': nome_compilado}).execute()
            existente['name'] = nome_compilado
        except Exception:
            pass

    # Garante apenas 1 arquivo para o mês dentro de "Consolidado mensal"
    for dup in candidatos_mes[1:]:
        if not dry_run:
            try:
                drive_idx.drive.files().update(fileId=dup['id'], body={'trashed': True}).execute()
                drive_idx.remover_arquivo(dup['id'])
            except Exception:
                pass

    # Hash de integridade dos componentes da compilação (inclui soma de cada rubrica para atualizar Planilha/Pág. 1)
    # 'layout3_sem_fg' = exporta planilha restrita às colunas A:E (sem colunas F e G)
    hash_compilacao = hashlib.md5(
        ('layout3_sem_fg|' + '|'.join(
            f"{d['doc_num']}:{d['id_arquivo']}:{d.get('hash_estado', '')}:{d.get('soma', '')}"
            for d in docs_ordenados
        )).encode('utf-8')
    ).hexdigest()

    if existente and existente.get('appProperties', {}).get('hash_compilacao') == hash_compilacao:
        relatorio.setdefault('compilados', []).append(f"[{mes_nome}] {comum.PASTA_CONSOLIDADO_MENSAL}/{nome_compilado} (inalterado)")
        print(f"  ⏩ Consolidado mensal inalterado: {comum.PASTA_CONSOLIDADO_MENSAL}/{nome_compilado}")
        return existente.get('webViewLink', '')

    print(f"\n📑 Compilando consolidado mensal em '{comum.PASTA_CONSOLIDADO_MENSAL}': {nome_compilado} (Planilha + {len(docs_ordenados)} documentos em ordem)...")
    if dry_run:
        print(f"     [DRY-RUN] Simulação: geraria '{comum.PASTA_CONSOLIDADO_MENSAL}/{nome_compilado}'")
        relatorio.setdefault('compilados', []).append(f"[{mes_nome}] {comum.PASTA_CONSOLIDADO_MENSAL}/{nome_compilado} (simulado)")
        return ""

    # 1. Exportar a aba da planilha para PDF em formato A4 (apenas colunas A:E, sem F e G)
    doc_master = None
    gid = aba.id
    url = (
        f"https://docs.google.com/spreadsheets/d/{ID_PLANILHA}/export?"
        f"format=pdf&gid={gid}&range=A:E&size=A4&portrait=true&fitw=true&gridlines=false"
        f"&top_margin=0.5&bottom_margin=0.5&left_margin=0.5&right_margin=0.5"
    )
    for tentativa in range(1, 4):
        try:
            resp = sheets_client.http_client.session.get(url, timeout=30)
            if resp.status_code == 200 and resp.content and resp.content[:4] == b'%PDF':
                doc_master = fitz.open(stream=resp.content, filetype="pdf")
                break
            elif resp.status_code == 429:
                print(f"     ⚠️  Rate limit (HTTP 429) ao exportar planilha, aguardando tentativa {tentativa}/3...")
                time.sleep(3 * tentativa)
            else:
                print(f"     ⚠️  Status {resp.status_code} ao exportar planilha (tentativa {tentativa}/3)")
                time.sleep(2)
        except Exception as e:
            print(f"     ⚠️  Erro ao exportar PDF da planilha (tentativa {tentativa}/3): {e}")
            time.sleep(2)

    if not doc_master:
        print(f"     ❌ Não foi possível exportar a planilha para PDF para {mes_nome}")
        return None

    # 2. Montar sumário com marcadores (TOC) e mesclar os PDFs em sequência
    num_pags_planilha = len(doc_master)
    toc = [[1, f"Doc {letra_mes}1 - Planilha do Mês ({mes_nome})", 1]]
    pag_atual = num_pags_planilha + 1

    for item in docs_ordenados:
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
            if raw_pdf[:4] == b'%PDF':
                sub_doc = fitz.open(stream=raw_pdf, filetype="pdf")
            else:
                img_doc = fitz.open(stream=raw_pdf, filetype="jpeg")
                sub_doc = fitz.open(stream=img_doc.convert_to_pdf(), filetype="pdf")
                img_doc.close()
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
        'title': f'Despesas {mes_nome}',
        'author': 'Prestação de Contas',
        'subject': f'Planilha (Doc {letra_mes}1) + {len(docs_ordenados)} documentos de comprovantes em ordem'
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

    # 4. Upload para o Google Drive na pasta "Consolidado mensal" (apenas 1 arquivo por mês)
    media = MediaIoBaseUpload(io.BytesIO(out_bytes), mimetype='application/pdf', resumable=True)
    props = {'name': nome_compilado, 'appProperties': {'hash_compilacao': hash_compilacao, 'mes': mes_nome}}
    link_compilado = (existente or {}).get('webViewLink', '')
    try:
        if existente:
            f_drive = drive_idx.drive.files().update(
                fileId=existente['id'], body=props, media_body=media, fields='id, name, mimeType, parents, webViewLink, appProperties'
            ).execute()
        else:
            f_drive = drive_idx.drive.files().create(
                body={'parents': [id_pasta_consolidado], **props},
                media_body=media, fields='id, name, mimeType, parents, webViewLink, appProperties'
            ).execute()
            try:
                drive_idx.drive.permissions().create(fileId=f_drive['id'], body={'type': 'anyone', 'role': 'reader'}).execute()
            except Exception:
                pass
        link_compilado = f_drive.get('webViewLink', '')
        drive_idx.adicionar_arquivo(f_drive)
    except Exception as e_up:
        print(f"     ⚠️  Não foi possível fazer upload do consolidado mensal no Drive ({e_up}); preservando cópia local e link anterior.")

    # 5. Atualizar célula G1 da planilha com o link direto da compilação completa
    try:
        aba.update_acell('G1', f'=HYPERLINK("{link_compilado}"; "📄 Despesas {mes_nome}")')
    except Exception:
        pass

    print(f"  ✅ Consolidado mensal salvo em '{comum.PASTA_CONSOLIDADO_MENSAL}': {nome_compilado} ({total_pags} págs, {len(out_bytes)//1024} KB)")
    print(f"     📁 Local: {caminho_local}")
    print(f"     🔗 Drive: {link_compilado}")

    relatorio.setdefault('compilados', []).append(f"[{mes_nome}] {comum.PASTA_CONSOLIDADO_MENSAL}/{nome_compilado} ({total_pags} págs)")
    return link_compilado


def salvar_relatorio_txt_sem_valor(itens_sem_valor, triagem=None):
    """Gera/atualiza arquivos_sem_valor.txt na raiz de Gastos/ com todos os arquivos que necessitam conferência."""
    caminho_txt = os.path.join(comum.BASE_DIR, 'arquivos_sem_valor.txt')
    ts = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    linhas = [
        "=" * 70,
        "RELATÓRIO DE COMPROVANTES SEM VALOR / PENDENTES (GASTOS)",
        f"Gerado em: {ts}",
        "=" * 70,
    ]
    pendentes_triagem = [t for t in (triagem or []) if t.get('status') != 'COMPLETO']
    total_pendencias = len(itens_sem_valor) + len(pendentes_triagem)

    if total_pendencias == 0:
        linhas.append("\n✅ Nenhum arquivo sem valor ou pendente encontrado!")
        linhas.append("Todos os comprovantes possuem valor identificado (no nome ou blindados na planilha) e foram contabilizados.")
    else:
        linhas.append(f"\n⚠️  Total de comprovantes pendentes de valor/conferência: {total_pendencias}\n")
        linhas.append("COMO RESOLVER (escolha uma das opções):")
        linhas.append("• Opção A (Planilha): Preencha o valor diretamente na célula da rubrica na planilha (o consolidador blinda automaticamente pelo hash).")
        linhas.append("• Opção B (Drive): Renomeie o arquivo no Google Drive adicionando o valor no início (ex: '150.00 recibo.jpg') e rode: py consolidar.py\n")
        linhas.append("-" * 70)

        if itens_sem_valor:
            linhas.append("📁 ARQUIVOS NAS PASTAS DE RUBRICAS SEM VALOR IDENTIFICADO:")
            por_rotulo = {}
            for item in itens_sem_valor:
                rot = item.get('rotulo') if isinstance(item, dict) else str(item)
                por_rotulo.setdefault(rot, []).append(item)

            for rot, arqs in sorted(por_rotulo.items()):
                linhas.append(f"\n[{rot}] ({len(arqs)} arquivo(s)):")
                for a in arqs:
                    if isinstance(a, dict):
                        linhas.append(f"  • Arquivo: {a.get('nome')}")
                        linhas.append(f"    Link: {a.get('link')}")
                        linhas.append(f"    ID: {a.get('id')}")
                    else:
                        linhas.append(f"  • {a}")

        if pendentes_triagem:
            linhas.append("\n" + "-" * 70)
            linhas.append("📁 ARQUIVOS DA RAIZ / TRIAGEM PENDENTES:")
            for p in pendentes_triagem:
                linhas.append(f"\n  • Arquivo original: {p.get('nome_original')}")
                linhas.append(f"    Nome sugerido: {p.get('nome_sugerido')}")
                linhas.append(f"    Status: {p.get('status')}")
                linhas.append(f"    Destino: {p.get('pasta_mes_drive') or 'Raiz do Drive'}")
                linhas.append(f"    Atenção: {p.get('aviso')}")

    linhas.append("\n" + "=" * 70)
    try:
        with open(caminho_txt, 'w', encoding='utf-8') as f:
            f.write('\n'.join(linhas) + '\n')
        print(f"\n📄 Relatório de arquivos sem valor atualizado em:\n   -> {caminho_txt}")
    except Exception as e_txt:
        print(f"⚠️  Falha ao salvar relatório txt: {e_txt}")


def consolidar_tudo(sheets_client, drive_idx, so_mes=None, dry_run=False, triagem=None, compilar=True, todos_meses=False):
    planilha = sheets_client.open_by_key(ID_PLANILHA)
    print(f"\n🚀 CONSOLIDAÇÃO {'(DRY-RUN) ' if dry_run else ''}...")
    if not so_mes and not todos_meses:
        print(f"📌 Período ativo selecionado: {comum.MESES[PERIODO_ATIVO_INICIO[1]-1]}/{PERIODO_ATIVO_INICIO[0]} até {comum.MESES[PERIODO_ATIVO_FIM[1]-1]}/{PERIODO_ATIVO_FIM[0]}")
    mapa_extratos = carregar_mapa_extratos_gerais(drive_idx.drive, drive_idx)
    if mapa_extratos:
        for r_norm, inf in mapa_extratos.items():
            print(f"📊 Extrato Geral ativo: {inf['arquivo']['name']} (R$ {inf['total_geral']:.2f})")
    for aba in planilha.worksheets():
        m_nome = aba.title.strip()
        if so_mes and m_nome != so_mes:
            continue
        if not so_mes and not todos_meses and not eh_mes_no_periodo(m_nome):
            continue
        docs_mes = consolidar_aba(drive_idx, aba, dry_run=dry_run, mapa_extrato_geral=mapa_extratos)
        if compilar and docs_mes:
            compilar_mes_final(sheets_client, drive_idx, aba, docs_mes, dry_run=dry_run)

    print('\n' + '=' * 60)
    print(f"📊 RELATÓRIO {'(DRY-RUN — nada foi gravado)' if dry_run else 'FINAL'}")
    print('=' * 60)
    for chave, titulo in (('compilados', '📑 Compilações Finais do Mês (Planilha + Comprovantes)'),
                          ('criados', '🆕 Novos'), ('atualizados', '🔄 Atualizados'),
                          ('duplicados', '♊ Duplicatas exatas descartadas/ignoradas'),
                          ('substituidos', '🔄 Versões antigas substituídas pelo último subido'),
                          ('blindados_manuais', '🔒 Blindados com valor manual na planilha'),
                          ('sem_valor', '❓ Arquivos sem valor no nome')):
        itens = relatorio.get(chave, [])
        print(f'\n{titulo}: {len(itens)}')
        for item in itens:
            if isinstance(item, dict):
                print(f"   - {item.get('rotulo')}: '{item.get('nome')}' -> {item.get('link')}")
            else:
                print(f'   - {item}')
    print(f"\n⏩ Inalterados (já consolidados com mesmo hash): {relatorio['ignorados']}")

    if not dry_run and not so_mes:
        salvar_relatorio_txt_sem_valor(relatorio.get('sem_valor', []), triagem=triagem)

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
    rubricas_conferir = ['Aluguel', 'Mesada', 'Luz', 'Água', 'Internet', 'Faxina/Limpeza', 'Mercado/Açougue/Padaria', 'Transporte', 'Escola', 'Psicoterapia', 'Psicopedagoga', 'Farmácia e Higiene']
    for aba in planilha.worksheets():
        m_nome = aba.title.strip()
        if not any(m_nome.startswith(m) for m in comum.MESES):
            continue
        if not so_mes and not todos_meses and not eh_mes_no_periodo(m_nome):
            continue
        dados = aba.get_all_values()
        valores_mes = {}
        for linha in dados:
            if len(linha) > 2 and linha[1].strip() and linha[2].strip():
                valores_mes[linha[1].strip()] = linha[2].strip()

        itens_status = []
        for r in rubricas_conferir:
            if r in valores_mes:
                val_txt = valores_mes[r]
                val_fmt = val_txt if val_txt.startswith('R$') else f"R$ {val_txt}"
                itens_status.append(f"{r}: ✅ {val_fmt}")
            else:
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
    ap.add_argument('--todos-meses', action='store_true', help='consolidar todo o histórico (desde Maio 2025) em vez de apenas o período ativo 2026')
    ap.add_argument('--sem-meses', action='store_true', help='não gerar meses faltantes')
    ap.add_argument('--sem-compilar', action='store_true', help='não gerar o PDF compilado final do mês')
    ap.add_argument('--extrato-geral', action='store_true', help='processar extrato geral consolidado multimês')
    ap.add_argument('--farmacia', action='store_true', help='processar prints de gastos de Farmácia e Higiene')
    ap.add_argument('--organizar-raiz', action='store_true', help='organizar arquivos pendentes na raiz do Drive via classificador')
    args = ap.parse_args()
    ate = tuple(int(x) for x in args.ate.split('-'))

    sheets_client, drive, tipo = comum.conectar(permitir_login=args.oauth)
    print(f'🔑 Credencial: {tipo}')
    print('⚡ Carregando índice do Drive...')
    drive_idx = DriveIndex(drive)
    print(f'   {len(drive_idx.by_id)} objetos indexados.')

    if args.farmacia:
        classificador.processar_pasta_farmacia(drive=drive, drive_idx=drive_idx, dry_run=args.dry_run)
        drive_idx.recarregar()

    if args.extrato_geral:
        extrato_geral(aplicar_planilha=True, sheets_client=sheets_client, drive=drive, drive_idx=drive_idx, dry_run=args.dry_run)
        drive_idx.recarregar()

    if not args.sem_meses:
        comum.garantir_meses(sheets_client, drive_idx, ate=ate, dry_run=args.dry_run)
        drive_idx.recarregar()

    triagem = None
    if args.organizar_raiz:
        import classificador
        movidos, triagem = classificador.organizar_arquivos_raiz_drive(drive, drive_idx, dry_run=args.dry_run)
        if movidos > 0 and not args.dry_run:
            drive_idx.recarregar()

    consolidar_tudo(
        sheets_client, drive_idx, so_mes=args.mes, dry_run=args.dry_run, triagem=triagem, compilar=not args.sem_compilar,
        todos_meses=args.todos_meses
    )


if __name__ == '__main__':
    main()
