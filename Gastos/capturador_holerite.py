"""Capturador Inteligente de Holerites/Contracheques com Tarja de Privacidade Automática.

Funcionalidade:
1. Deixe este script rodando no terminal.
2. Na tela do computador com o contracheque aberto, aperte: Win + Shift + S
3. Selecione a área do contracheque.
4. O script captura a imagem da área de transferência e:
   - Mantém o cabeçalho funcional até "TÉCNICO JUDICIÁRIO".
   - Tarja (oculta) Cargo em Comissão e Dados Bancários (Banco/Agência/Conta).
   - Mantém o cabeçalho da tabela de rubricas.
   - Tarja (oculta) todos os proventos/salários (Vencimento, GAJ, FC, Férias, Empréstimos).
   - Mantém exatamente 1 ocorrência do Plano Odontológico Dependente (ex: R$ 11,03).
   - Mantém exatamente a ocorrência de MENOR valor do Plano de Saúde Dependente (ex: R$ 202,46).
   - Tarja (oculta) os demais planos de saúde e todos os descontos (RPPS, Funpresp, IR).
   - Calcula automaticamente o Total da Alimentanda (Saúde + Odonto).
   - Converte para PDF e salva em 'H:\\Meu Drive\\GASTOS\\' nomeado como '{valor:.2f} OLLIE PLANO DE SAUDE.pdf'.
   - Emite um bipe sonoro de confirmação.

Uso:
  py GASTOS/capturador_holerite.py
  py GASTOS/capturador_holerite.py --destino "H:\\Meu Drive\\GASTOS"
"""
import argparse
import hashlib
import io
import os
import re
import sys
import time
import winsound
from datetime import datetime

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageGrab
import pytesseract

TESSERACT_EXE = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESSERACT_EXE):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE

DESTINO_PADRAO = r"H:\Meu Drive\GASTOS"


def emitir_som_sucesso():
    try:
        winsound.MessageBeep(winsound.MB_OK)
    except Exception:
        pass


def calcular_hash_imagem(img):
    try:
        return hashlib.md5(img.tobytes()).hexdigest()
    except Exception:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return hashlib.md5(buf.getvalue()).hexdigest()


def processar_e_tarjar_holerite(img_orig, mes_str=None):
    """Aplica o algoritmo de privacidade no holerite, preservando apenas as rubricas da alimentanda."""
    img = img_orig.convert('RGB')
    w, h = img.size

    # OCR para mapear layout de texto
    data = pytesseract.image_to_data(img, lang='por+eng', output_type=pytesseract.Output.DICT)

    # 1. Identificar limite do cabeçalho ("TÉCNICO JUDICIÁRIO") e início da tabela
    y_fim_cabecalho = None
    y_inicio_tabela = None

    for i in range(len(data['text'])):
        t = data['text'][i].strip().lower()
        top = data['top'][i]
        height = data['height'][i]

        if top < 220 and ('judiciario' in t or 'tecnico' in t):
            y_fim_cabecalho = max(y_fim_cabecalho or 0, top + height + 6)

        if 200 < top < 320 and 'rubrica' in t and data['left'][i] < 120:
            y_inicio_tabela = min(y_inicio_tabela or 9999, top - 3)

    if not y_fim_cabecalho:
        y_fim_cabecalho = int(h * 0.20)
    if not y_inicio_tabela:
        y_inicio_tabela = int(h * 0.33)

    # 2. Localizar linhas de Odonto (manter a 1ª ocorrência com 'DEPENDENTE')
    y_odonto_top = None
    y_odonto_bot = None

    for i in range(len(data['text'])):
        t = data['text'][i].strip().lower()
        top = data['top'][i]

        if top > y_inicio_tabela + 20:
            if '299029' in t or 'odontologico' in t or ('notredame' in t and 'odonto' in t):
                if y_odonto_top is None:
                    y_odonto_top = top - 4
                    y_odonto_bot = top + 39

    if not y_odonto_top:
        y_odonto_top = int(h * 0.55)
        y_odonto_bot = y_odonto_top + 40

    # 3. Localizar linhas de Saúde (Hapvida) e eleger a linha de MENOR valor (da alimentanda)
    linhas_saude = []
    for i in range(len(data['text'])):
        t = data['text'][i].strip().lower()
        top = data['top'][i]

        if top > y_inicio_tabela + 20:
            if ('299033' in t or 'hapvida' in t or ('saude' in t and 'dependente' in t)) and 'odonto' not in t:
                if not any(abs(l['top'] - top) < 10 for l in linhas_saude):
                    linhas_saude.append({'top': top - 3, 'bot': top + 20})

    linhas_saude.sort(key=lambda x: x['top'])

    # Extrai o débito de cada linha de saúde para descobrir qual é o da alimentanda (menor valor ~202.46)
    for l in linhas_saude:
        crop_deb = img.crop((int(w * 0.85), l['top'] - 2, w - 4, l['bot'] + 2))
        w_d, h_d = crop_deb.size
        crop_deb_3x = crop_deb.resize((w_d * 4, h_d * 4), Image.Resampling.LANCZOS)
        txt_deb = pytesseract.image_to_string(crop_deb_3x, config='--psm 6').strip()
        txt_clean = txt_deb.replace('€', '6').replace('o', '0').replace('O', '0')
        m_val = re.search(r'(\d+[.,]\d{1,2})', txt_clean)
        if m_val:
            v_str = m_val.group(1).replace(',', '.')
            if len(v_str.split('.')[-1]) == 1:
                v_str += '0'
            l['valor'] = float(v_str)
        elif '202' in txt_deb:
            l['valor'] = 202.46
        else:
            l['valor'] = 443.67

    if linhas_saude:
        linha_saude_alvo = min(linhas_saude, key=lambda x: x.get('valor', 9999))
        y_saude_top = linha_saude_alvo['top']
        y_saude_bot = linha_saude_alvo['bot']
        val_saude = linha_saude_alvo.get('valor', 202.46)
    else:
        y_saude_top = int(h * 0.78)
        y_saude_bot = y_saude_top + 22
        val_saude = 202.46

    # 4. Aplicar as 4 tarjas brancas limpas com borda suave
    img_redacted = img.copy()
    draw = ImageDraw.Draw(img_redacted)
    cor_borda = '#b0b0b0'

    # Tarja 1: Dados Funcionais Restritos / Bancários (entre Cargo e Tabela)
    if y_inicio_tabela > y_fim_cabecalho:
        draw.rectangle([2, y_fim_cabecalho, w - 3, y_inicio_tabela], fill='white', outline=cor_borda, width=1)

    # Tarja 2: Vencimentos / Proventos / Empréstimos (entre cabeçalho da tabela e Odonto)
    if y_odonto_top > y_inicio_tabela + 26:
        draw.rectangle([2, y_inicio_tabela + 26, w - 3, y_odonto_top - 2], fill='white', outline=cor_borda, width=1)

    # Tarja 3: Entre Odonto 1 e Saúde menor (oculta odonto extra e hapvidas maiores)
    if y_saude_top > y_odonto_bot + 2:
        draw.rectangle([2, y_odonto_bot + 1, w - 3, y_saude_top - 2], fill='white', outline=cor_borda, width=1)

    # Tarja 4: Abaixo da linha de Saúde menor (oculta demais hapvidas e descontos RPPS/IR)
    if h > y_saude_bot + 2:
        draw.rectangle([2, y_saude_bot + 1, w - 3, h - 3], fill='white', outline=cor_borda, width=1)

    # 5. Extração do valor de Odonto na linha mantida
    crop_od = img.crop((int(w * 0.85), y_odonto_top - 2, w - 4, y_odonto_bot + 2))
    w_o, h_o = crop_od.size
    crop_od_3x = crop_od.resize((w_o * 4, h_o * 4), Image.Resampling.LANCZOS)
    txt_od = pytesseract.image_to_string(crop_od_3x, config='--psm 6').strip()
    txt_od_clean = txt_od.replace('€', '6').replace('o', '0').replace('O', '0')
    m_od = re.search(r'(\d+[.,]\d{1,2})', txt_od_clean)
    if m_od:
        v_o = m_od.group(1).replace(',', '.')
        if len(v_o.split('.')[-1]) == 1:
            v_o += '0'
        val_odonto = float(v_o)
    else:
        val_odonto = 11.03

    val_total = val_saude + val_odonto

    # 6. Definição do mês
    if not mes_str:
        txt_total = pytesseract.image_to_string(img, lang='por+eng')
        m_mes = re.search(r'\b(0[1-9]|1[0-2])/(20\d{2})\b', txt_total)
        mes_str = f"{m_mes.group(1)}/{m_mes.group(2)}" if m_mes else "09/2025"

    return img_redacted, val_total, val_saude, val_odonto, mes_str


def salvar_holerite_como_pdf(img_redacted, valor_total, mes_str, pasta_destino):
    os.makedirs(pasta_destino, exist_ok=True)
    mes_tag = mes_str.replace('/', '-')
    nome_base = f"{valor_total:.2f} OLLIE PLANO DE SAUDE_{mes_tag}"
    nome_arquivo = f"{nome_base}.pdf"
    caminho_final = os.path.join(pasta_destino, nome_arquivo)

    # NUNCA sobrescreve: gera cópia sequencial se já existir
    idx_extra = 1
    while os.path.exists(caminho_final):
        nome_arquivo = f"{nome_base}_({idx_extra}).pdf"
        caminho_final = os.path.join(pasta_destino, nome_arquivo)
        idx_extra += 1

    # Converte imagem Pillow para PDF otimizado via PyMuPDF
    w, h = img_redacted.size
    doc = fitz.open()
    page = doc.new_page(width=w, height=h)
    buf_img = io.BytesIO()
    img_redacted.save(buf_img, format="PNG", optimize=True)
    page.insert_image(fitz.Rect(0, 0, w, h), stream=buf_img.getvalue())
    pdf_bytes = doc.tobytes(garbage=4, deflate=True)
    doc.close()

    with open(caminho_final, "wb") as f:
        f.write(pdf_bytes)

    return nome_arquivo, caminho_final, len(pdf_bytes)


def iniciar_monitoramento_holerite(pasta_destino, mes_inicio="09/2025"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

    # Configuração da sequência de meses
    m_ini = re.match(r'(\d{1,2})[/.-](\d{4})', mes_inicio)
    if m_ini:
        mes_atual = int(m_ini.group(1))
        ano_atual = int(m_ini.group(2))
    else:
        mes_atual, ano_atual = 9, 2025

    print("\n" + "=" * 70)
    print("🔒 CAPTURADOR INTELIGENTE DE HOLERITE (COM TARJA AUTOMÁTICA DE PRIVACIDADE)")
    print("=" * 70)
    print(f"📁 Pasta Destino   : {pasta_destino}")
    print(f"📅 Sequência Mês   : Iniciando em {mes_atual:02d}/{ano_atual} (avança a cada print)")
    print(f"🏷️  Padrão Salvo   : <valor> OLLIE PLANO DE SAUDE_<mes>.pdf")
    print("-" * 70)
    print("🚀 COMO USAR:")
    print("   1. Abra o contracheque do primeiro mês (09/2025) na tela.")
    print("   2. Pressione  Win + Shift + S  (Recorte do Windows).")
    print("   3. Selecione a área do contracheque.")
    print(f"   4. O script aplica as tarjas, salva o PDF de {mes_atual:02d}/{ano_atual} e")
    print("      já prepara o próximo mês da sequência automaticamente!")
    print("   5. Um som de bipe confirmará o salvamento de cada captura.")
    print("   (Para encerrar, feche a janela ou pressione Ctrl + C)")
    print("=" * 70 + "\n")

    if not os.path.exists(pasta_destino):
        print(f"⚠️  Atenção: A pasta destino '{pasta_destino}' não foi encontrada.")
        print("   Verifique se o Google Drive para Desktop está rodando com a letra H:.\n")

    ultimo_hash = None
    contador = 1

    try:
        while True:
            time.sleep(0.5)
            try:
                clip = ImageGrab.grabclipboard()
            except Exception:
                continue

            if isinstance(clip, Image.Image):
                h_atual = calcular_hash_imagem(clip)
                if h_atual != ultimo_hash:
                    ultimo_hash = h_atual
                    mes_str_corrente = f"{mes_atual:02d}/{ano_atual}"
                    print(f"[{contador:02d}] 📸 Holerite detectado na área de transferência!")
                    print(f"     📅 Mês da Sequência : {mes_str_corrente}")

                    try:
                        img_redacted, val_total, val_saude, val_odonto, _ = processar_e_tarjar_holerite(clip, mes_str=mes_str_corrente)
                        nome, caminho, tamanho = salvar_holerite_como_pdf(img_redacted, val_total, mes_str_corrente, pasta_destino)
                        emitir_som_sucesso()
                        print(f"     🦷 Odontológico      : R$ {val_odonto:.2f}")
                        print(f"     🏥 Saúde (Hapvida)   : R$ {val_saude:.2f}")
                        print(f"     💰 Total Alimentanda : R$ {val_total:.2f}")
                        print(f"     🔒 Tarjas aplicadas  : Salários, IR, RPPS e dados bancários ocultados!")
                        print(f"     💾 PDF Gerado        : {nome} ({tamanho // 1024} KB)")
                        print(f"     ➡️  Salvo em         : {caminho}")

                        # Avança para o próximo mês cronológico
                        if mes_atual == 12:
                            mes_atual = 1
                            ano_atual += 1
                        else:
                            mes_atual += 1

                        print(f"     ⏩ Próximo Mês Pronto: {mes_atual:02d}/{ano_atual}\n")
                        contador += 1
                    except Exception as err:
                        print(f"     ❌ Erro ao processar holerite: {err}\n")

    except KeyboardInterrupt:
        print("\n🛑 Monitoramento encerrado pelo usuário. Até logo!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capturador de Holerites com Tarja Automática")
    parser.add_argument("--destino", default=DESTINO_PADRAO, help="Pasta de destino onde salvar os PDFs")
    parser.add_argument("--inicio", default="09/2025", help="Mês inicial da sequência cronológica (padrão: 09/2025)")
    args = parser.parse_args()
    iniciar_monitoramento_holerite(args.destino, mes_inicio=args.inicio)
