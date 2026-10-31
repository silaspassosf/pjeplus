"""Classificador e Organizador Inteligente com Degradação Graciosa (GASTOS/).

COMPORTAMENTO POR CENÁRIO DE DETECÇÃO:
1. SUCESSO TOTAL (Data + Valor + Rubrica):
   -> Renomeia: '{valor:.2f} {detalhe}.ext'
   -> Move: '{pasta_mes}/{bloco}/{rubrica}/'
2. FALTA RUBRICA (Data + Valor OK, Tipo desconhecido):
   -> Renomeia: '{valor:.2f} [REVISAR_RUBRICA] {nome_limpo}.ext'
   -> Move: '{pasta_mes}/[REVISAR_RUBRICA]/'
   -> Alerta: avisando que está no mês certo aguardando definir categoria.
3. FALTA VALOR (Data + Rubrica OK, Valor não detectado):
   -> Renomeia: '[SEM_VALOR] {rubrica} {nome_limpo}.ext'
   -> Move: '{pasta_mes}/{bloco}/{rubrica}/'
   -> Alerta: avisando que a categoria foi identificada mas falta o valor.
4. SÓ IDENTIFICOU A DATA (Mês OK, sem valor e sem rubrica):
   -> Renomeia: '[REVISAR_TUDO] {nome_limpo}.ext'
   -> Move: '{pasta_mes}/[REVISAR_RUBRICA]/'
5. SEM DATA (Mês desconhecido):
   -> Renomeia: '{valor:.2f} [SEM_DATA] {nome_limpo}.ext' (ou '[SEM_DATA] ...')
   -> Move: '[QUARENTENA_SEM_DATA]/' na raiz do Drive
   -> Alerta: avisando que precisa conferir a data do recibo.

Uso:
  py classificador.py --organizar-raiz-drive
  py classificador.py --pasta "inbox" --enviar-drive
  py classificador.py "comprovante.pdf"
"""
import argparse
import hashlib
import io
import os
import re
import sys
import unicodedata
from datetime import datetime

import fitz  # PyMuPDF
from fitz import Rect  # PyMuPDF
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

import comum
from comum import (BLOCO_A, BLOCO_B, BLOCO_I, BLOCO_II, ID_PASTA_RAIZ_DRIVE, MESES, DriveIndex,
                   conectar, normalizar)
from extrato import extrato_geral

TESSERACT_EXE = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESSERACT_EXE):
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE
else:
    pytesseract = None


REGRAS_DESPESA = [
    # --- BLOCO B: DESPESAS GERAIS DA CASA
    {
        'rubrica': 'Faxina/Limpeza',
        'bloco': BLOCO_B,
        'sufixo': 'iracema',
        'keywords': ['iracema da silva lucas', '95588-0281', 'iracema', 'faxina', 'diarista'],
    },
    {
        'rubrica': 'Internet',
        'bloco': BLOCO_B,
        'sufixo': 'vivo fibra',
        'keywords': ['telefonica brasil', 'vivo fibra', 'fibra 500mbps', 'fibra 300mbps', 'vivo total', 'vivo internet'],
    },
    {
        'rubrica': 'Aluguel',
        'bloco': BLOCO_B,
        'sufixo': '',
        'keywords': ['nova galli imoveis', 'nova galli', '27.***.***/0001-5*'],
        'valores_tipicos': [3500.00],
    },
    {
        'rubrica': 'Luz',
        'bloco': BLOCO_B,
        'sufixo': '',
        'keywords': [
            'elektro', 'neoenergia', 'consumo te', 'consumo tusd', 'nf3e',
            'distribuicao de energia', 'ilum pub', 'conta de energia eletrica'
        ],
    },
    {
        'rubrica': 'Água',
        'bloco': BLOCO_B,
        'sufixo': 'sabesp',
        'keywords': ['sabesp', 'saneamento basico', 'fatura-911136'],
    },
    {
        'rubrica': 'Streamings',
        'bloco': BLOCO_B,
        'sufixo': 'STREAMING',
        'keywords': ['netflix', 'spotify', 'amazon prime', 'disney', 'max brasil', 'hbo'],
    },
    {
        'rubrica': 'Mercado/Açougue/Padaria',
        'bloco': BLOCO_B,
        'sufixo': '',
        'keywords': [
            'tenda atacado', 'mercado zezinho', 'supermercado conde', 'panificadora emporio',
            'ifood', 'br.com.brainweb.ifood', 'detalhes do pedido', 'resumo de valores',
            'ver cardapio', 'previsao de entrega', 'pago pelo app', 'data do pedido',
            'status do pedido', 'taxa de entrega', 'taxa de servico',
            'padaria', 'acougue', 'hortifruti', 'frutas casa', 'supermercado casa'
        ],
    },

    # --- BLOCO A: DESPESAS INDIVIDUAIS DA ALIMENTANDA
    {
        'rubrica': 'Transporte',
        'bloco': BLOCO_A,
        'sufixo': 'OLLIE TRANSPORTE',
        'keywords': [
            '99receipt', '99app', '99 tecnologia', 'uber do brasil', 'uber trip',
            'indrive', 'tarifa indrive', 'tarifa da viagem', 'comprovante da sua viagem'
        ],
    },
    {
        'rubrica': 'Escola',
        'bloco': BLOCO_A,
        'sufixo': '',
        'keywords': [
            'cooeduba', 'cooperativa educacional de ubatuba', 'pjbank pagamentos',
            'pjbank', 'superlogica', '18.191.228/0001-71', '03.428.325/0001-68',
            'mensalidade escola ollie', 'escola ollie'
        ],
    },
    {
        'rubrica': 'Gastos extras escolares',
        'bloco': BLOCO_A,
        'sufixo': 'OLLIE MATERIAL DIDATICO',
        'keywords': ['material didatico cooeduba', 'apostila escolar', 'livro didatico'],
    },
    {
        'rubrica': 'Psicopedagoga',
        'bloco': BLOCO_A,
        'sufixo': '',
        'keywords': ['fernanda xavier de paiva borges', 'fernanda xavier', 'psicopedagoga', 'psicopedagogia'],
        'valores_tipicos': [300.00],
    },
    {
        'rubrica': 'Psicoterapia',
        'bloco': BLOCO_A,
        'sufixo': '',
        'keywords': [
            'mariana xavier',
            'mariana xavier consultorio psicologico',
            'mariana xavier consultorio psicologico ltda',
            'consultorio psicologico',
            '57.258.589/0001-40',
            '57.258.589',
            '57258589000140',
            'psicoterapia',
            'psicologa',
            'psicologo',
            'psicologia',
            'terapia ollie',
        ],
        'valores_tipicos': [760.00],
    },
    {
        'rubrica': 'Plano de Saúde e Odontológico',
        'bloco': BLOCO_A,
        'sufixo': 'OLLIE PLANO DE SAUDE',
        'keywords': ['notredame', 'intermedica', 'hapvida', 'assistencia saude', 'odontologico dependente', 'plano de saude'],
    },
    {
        'rubrica': 'Vestuário',
        'bloco': BLOCO_A,
        'sufixo': 'OLLIE ROUPAS',
        'keywords': ['shein', 'moda mundial brasil', 'dlocal brasil', 'zara', 'c&a', 'lojas renner', 'roupas'],
    },
    {
        'rubrica': 'Farmácia e Higiene',
        'bloco': BLOCO_A,
        'sufixo': 'OLLIE FARMACIA',
        'keywords': ['droga raia', 'raia2078', 'drogasil', 'farmacia', 'drogaria sao paulo', 'remedios'],
    },
    {
        'rubrica': 'Alimentação rua e Cantina Escolar',
        'bloco': BLOCO_A,
        'sufixo': 'OLLIE lanche',
        'keywords': ['cantinho do pao', 'cantina cooeduba', 'lanche creas', 'lanche ollie', 'salgadinhos e doces'],
    },
    {
        'rubrica': 'Mesada',
        'bloco': BLOCO_A,
        'sufixo': 'OLLIE MESADA',
        'keywords': ['mesada', 'mesada ollie'],
        'valores_tipicos': [300.00],
    },
]


def higienizar_fragmento(texto, max_len=25):
    limpo = re.sub(r'[\\/*?:"<>|]', '', str(texto)).strip()
    return limpo[:max_len].strip()


def extrair_texto_de_bytes(dados_bytes, nome_ou_ext):
    nome_low = nome_ou_ext.lower()
    is_pdf = nome_low.endswith('.pdf') or dados_bytes[:4] == b'%PDF'

    if is_pdf:
        try:
            doc = fitz.open(stream=dados_bytes, filetype="pdf")
            texto = ""
            for pag in doc:
                texto += pag.get_text() + "\n"
            if len(texto.strip()) > 30:
                return texto
        except Exception:
            pass

    if pytesseract:
        try:
            if is_pdf:
                doc = fitz.open(stream=dados_bytes, filetype="pdf")
                partes = []
                for pag in doc:
                    pix = pag.get_pixmap(dpi=200)
                    img = Image.open(io.BytesIO(pix.tobytes('png')))
                    w, h = img.size
                    # Tenta ler a página inteira
                    txt_p = pytesseract.image_to_string(img, lang='por+eng', config='--psm 6')
                    # Para prints de celular (como iFood), o rodapé tem dados cruciais com PSM 11
                    crop_bot = img.crop((0, int(0.5 * h), w, h))
                    txt_bot = pytesseract.image_to_string(crop_bot, lang='por+eng', config='--psm 11')
                    partes.append(txt_p + "\n" + txt_bot)
                return "\n".join(partes)
            else:
                img = Image.open(io.BytesIO(dados_bytes))
                return pytesseract.image_to_string(img, lang='por+eng', config='--psm 6')
        except Exception as e:
            return f"[Erro OCR: {e}]"
    return ""


def extrair_data(texto):
    if not texto:
        return None
    texto_str = re.sub(r'WhatsApp Image \d{4}-\d{2}-\d{2}[^.\r\n]*', '', str(texto), flags=re.IGNORECASE)
    # Limpa menções legais que citam anos antigos (ex: Lei 12.839/2013 em notas do Tenda)
    texto_str = re.sub(r'(?:lei|medida\s+provis[oó]ria|decreto)[\s\S]{0,40}?(?:201[0-9]|200[0-9]|19\d{2})', '', texto_str, flags=re.IGNORECASE)

    # 0. Caso NF-e / DANFE (Tenda, etc.): busca especificamente "DATA DA EMISSÃO"
    m_danfe = re.search(r'DATA\s+D[EA]\s+EMISS[ÃA]O[^\d\n\r]*[\r\n\s]*(\d{2})[/.-](\d{2})[/.-](20\d{2})', texto_str, re.IGNORECASE)
    if m_danfe:
        d, m, a = int(m_danfe.group(1)), int(m_danfe.group(2)), int(m_danfe.group(3))
        if 1 <= m <= 12 and 1 <= d <= 31:
            return datetime(a, m, d)

    # 1. Caso iFood / Pedido com "Data do pedido"
    m = re.search(r'Data\s+d[oaes]\s+pedid[oa][:\s]*[\r\n\s]*([^\r\n]{3,40})', texto_str, re.IGNORECASE)
    if m:
        linha_data = m.group(1)
        # Tenta extrair mesmo com ruído OCR (ex: 25/09/2026, 06/DE/2026, 24/10 2026, 03/10/2076)
        m_d = re.search(r'(\d{1,2})\s*[/.-]\s*(\d{1,2}|[A-Za-z]{2,3})\s*[/.-]?\s*(?:20\d{2}|20[A-Z0-9]{2}|A026|\d{2})', linha_data)
        if m_d:
            t_dia = m_d.group(1)
            t_mes = m_d.group(2)
            # Mapeia letras se vier OCR ruído
            mapa_chars = {'O': '0', 'o': '0', 'D': '0', 'Q': '0', 'I': '1', 'l': '1', 'i': '1', 'T': '1', 't': '1', 'L': '1', 'Z': '2', 'z': '2', 'E': '3', 'A': '4', 'a': '4', 'S': '5', 's': '5', 'G': '6', 'b': '6', 'B': '8', 'g': '9', 'q': '9'}
            mes_clean = "".join(mapa_chars.get(c, c) for c in t_mes)
            if mes_clean.isdigit():
                mes_num = int(mes_clean)
                dia_num = int(t_dia)
                if 1 <= mes_num <= 12 and 1 <= dia_num <= 31:
                    return datetime(2026, mes_num, dia_num)
        # fallback normal
        m_normal = re.search(r'(\d{2})[/.-](\d{2})[/.-](20\d{2})', linha_data)
        if m_normal:
            dia, mes, ano = int(m_normal.group(1)), int(m_normal.group(2)), int(m_normal.group(3))
            if 1 <= mes <= 12 and 1 <= dia <= 31:
                return datetime(ano, mes, dia)

    # 2. Caso Comprovante Bancário / PIX (Inter, C6, Nubank, Itaú, etc.): "Data do pagamento", "Data da transação", etc.
    # Ex: "Data do pagamento Terça, 06/01/2026", "Data da transação 04/05/2026", "Data da transagao Segunda-feira, 04/05/2026"
    m = re.search(
        r'Data\s+(?:do\s+pagamento|da\s+transa[çcg][ãaao]o|da\s+transfer[êe]ncia|do\s+d[ée]bito|do\s+pix|de\s+pagamento)[\s\S]{0,40}?(\d{2})[/.-](\d{2})[/.-](20\d{2})',
        texto_str,
        re.IGNORECASE
    )
    if m:
        dia, mes, ano = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mes <= 12 and 1 <= dia <= 31:
            return datetime(ano, mes, dia)

    # 3. Caso Data por extenso: "06 de janeiro de 2026"
    meses_map_pt = {
        'janeiro': 1, 'fevereiro': 2, 'março': 3, 'marco': 3, 'abril': 4, 'maio': 5,
        'junho': 6, 'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
    }
    m = re.search(
        r'\b(\d{1,2})\s+de\s+(janeiro|fevereiro|mar[çc]o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+de\s+(20\d{2})\b',
        texto_str,
        re.IGNORECASE
    )
    if m:
        dia, nome_m, ano = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        mes_idx = meses_map_pt.get(nome_m)
        if mes_idx and 1 <= dia <= 31:
            return datetime(ano, mes_idx, dia)

    # 4. Caso Conta do Mês / Mês de Referência (Luz Elektro / Neoenergia, Sabesp, etc.)
    m = re.search(r'(?:Conta\s+do\s+M[êe]s|M[êe]s\s+(?:de\s+)?Refer[êe]ncia|Refer[êe]ncia)\s*[:\s]*([A-Za-zçÇ]+|\d{2})[/.-](20\d{2})', texto_str, re.IGNORECASE)
    if m:
        mes_val, ano = m.group(1).lower(), int(m.group(2))
        mes_idx = meses_map_pt.get(mes_val) if not mes_val.isdigit() else int(mes_val)
        if mes_idx and 1 <= mes_idx <= 12:
            return datetime(ano, mes_idx, 1)

    m = re.search(r'\b(janeiro|fevereiro|mar[çc]o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)[/.-](20\d{2})\b', texto_str, re.IGNORECASE)
    if m:
        nome_m, ano = m.group(1).lower(), int(m.group(2))
        mes_idx = meses_map_pt.get(nome_m)
        if mes_idx:
            return datetime(ano, mes_idx, 1)

    # 3. Caso Mês de Referência Vivo: MÊS REFERÊNCIA: MM/AAAA
    m = re.search(r'M[ÊE]S\s+(?:DE\s+)?REFER[ÊE]NCIA\s*:?\s*(\d{2})[/.-](20\d{2})', texto_str, re.IGNORECASE)
    if m:
        mes, ano = int(m.group(1)), int(m.group(2))
        if 1 <= mes <= 12:
            return datetime(ano, mes, 1)

    # 3. Formato BR: DD/MM/AAAA ou DD-MM-AAAA
    # Quando há múltiplas datas (comprovantes com histórico/itens), a data do documento/pedido fica ao final
    datas_br = list(re.finditer(r'\b(\d{2})[/.-](\d{2})[/.-](20\d{2}|\d{2})\b', texto_str))
    if datas_br:
        for match in reversed(datas_br):
            dia, mes, ano = int(match.group(1)), int(match.group(2)), int(match.group(3))
            if ano < 100:
                ano += 2000
            if 1 <= mes <= 12 and 1 <= dia <= 31:
                return datetime(ano, mes, dia)

    # 3. Formato ISO: AAAA-MM-DD
    m = re.search(r'\b(20\d{2})[/.-](\d{2})[/.-](\d{2})\b', texto_str)
    if m:
        ano, mes, dia = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mes <= 12 and 1 <= dia <= 31:
            return datetime(ano, mes, dia)

    # 4. Formato Mês/Ano: MM/AAAA ou MM-AAAA (ex: 05/2026 no holerite ou _05-2026 no nome do arquivo)
    m = re.search(r'(?<!\d)(0[1-9]|1[0-2])[/.-](20\d{2})(?!\d)', texto_str)
    if m:
        mes, ano = int(m.group(1)), int(m.group(2))
        if 1 <= mes <= 12:
            return datetime(ano, mes, 1)

    # 4. Meses abreviados (inglês ou português, ex: 02Jul2026, qui 2 jul 2026)
    meses_map = {
        'jan': 1, 'fev': 2, 'feb': 2, 'mar': 3, 'abr': 4, 'apr': 4,
        'mai': 5, 'may': 5, 'jun': 6, 'jul': 7, 'ago': 8, 'aug': 8,
        'set': 9, 'sep': 9, 'out': 10, 'oct': 10, 'nov': 11, 'dez': 12, 'dec': 12
    }
    m = re.search(r'\b(\d{1,2})([A-Za-z]{3})(20\d{2})\b', texto_str)
    if m and m.group(2).lower() in meses_map:
        return datetime(int(m.group(3)), meses_map[m.group(2).lower()], int(m.group(1)))

    m = re.search(r'\b(\d{1,2})[,\s]+([A-Za-z]{3})[.,\s]+(20\d{2})\b', texto_str)
    if m and m.group(2).lower() in meses_map:
        return datetime(int(m.group(3)), meses_map[m.group(2).lower()], int(m.group(1)))

    return None


def extrair_valor(texto, nome_arquivo=""):
    if not texto and not nome_arquivo:
        return 0.0

    texto_str = str(texto)

    # 0. Caso especial Conta de Luz (Elektro / Neoenergia)
    if any(k in texto_str.lower() for k in ['elektro', 'neoenergia', 'consumo te', 'nf3e']):
        # Padrão 1: Total R$ do canhoto/resumo
        m = re.search(r'Total\s+R\$[^\d\n\r]*[\r\n\s]*(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2})', texto_str, re.IGNORECASE)
        if m:
            v_str = m.group(1).replace('.', '').replace(',', '.')
            return float(v_str)
        # Padrão 2: Valor da Conta
        m = re.search(r'Valor\s+da\s+Conta[^\d\n\r]*[\r\n\s]*(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2})', texto_str, re.IGNORECASE)
        if m:
            v_str = m.group(1).replace('.', '').replace(',', '.')
            return float(v_str)
        # Padrão 3: Cabeçalho com <Mês>/<Ano> seguido de vencimento e R$ valor
        m = re.search(r'\b(?:janeiro|fevereiro|mar[çc]o|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)/(?:20\d{2})\b[^\d\n\r]*[\r\n\s]*(?:\d{2}/\d{2}/\d{2,4}[^\d\n\r]*[\r\n\s]*)?R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})', texto_str, re.IGNORECASE)
        if m:
            v_str = m.group(1).replace('.', '').replace(',', '.')
            return float(v_str)

    # 1. Caso especial VIVO: pegar APENAS o valor da internet (Vivo Fibra), dividindo depois por 3
    if 'vivo' in texto_str.lower() or 'telefonica brasil' in texto_str.lower():
        padroes_vivo = [
            r'Subtotal\s+Vivo\s+Fibra\s*[\r\n\s]*(\d+[.,]\d{2})',
            r'Vivo\s*[-–]?\s*Fibra\s+\d+Mbps[^\d\n\r]*[\r\n\s]*\d*\s*(\d+[.,]\d{2})',
            r'Servi[çc]os\s+Contratados\s+Vivo\s+Internet[^\d\n\r]*[\r\n\s]*\d*\s*\d+%\s*(\d+[.,]\d{2})',
        ]
        for p in padroes_vivo:
            m = re.search(p, texto_str, re.IGNORECASE)
            if m:
                v_str = m.group(1).replace('.', '').replace(',', '.') if ',' in m.group(1) else m.group(1)
                v = float(v_str)
                if v > 0:
                    return v

    # 2. Caso especial inDrive: pegar linha 'Tarifa da viagem'
    if 'indrive' in texto_str.lower() or 'tarifa da viagem' in texto_str.lower():
        m = re.search(r'Tarifa\s+da\s+viagem\s*[\r\n\s]*(\d+[.,]\d{2})', texto_str, re.IGNORECASE)
        if m:
            v_str = m.group(1).replace('.', '').replace(',', '.') if ',' in m.group(1) else m.group(1)
            v = float(v_str)
            if v > 0:
                return v

    # 3. Padrões gerais de alta confiabilidade (NF-e DANFE, iFood, Boletos, Comprovantes)
    padroes_texto = [
        # Comprovantes PIX / Transferência bancária (Inter, C6, Nubank, etc.):
        r'(?:Pix\s+enviado|Pix\s+pago|Pix\s+realizado|Transfer[êe]ncia\s+realizada)[^\d\n\r]*[\r\n\s]*(?:R?[\$S5]|R\$\s*)?\s*(\d{1,3}(?:\.\d{3})*,\d{2}|\d+[.,]\d{2})',
        r'VALOR\s+TOTAL\s+DA\s+NOTA\s*[\r\n\s]*(\d{1,3}(?:\.\d{3})*,\d{2})',
        r'VALOR\s+TOTAL\s+PRODUTOS\s*[\r\n\s]*(\d{1,3}(?:\.\d{3})*,\d{2})',
        # Total explícito (iFood e similares): não pode ser Subtotal
        r'\b(?<!sub\s)(?<!sub)(?<!sub-)Total\b[^\d\n\r]*[\r\n\s]*(?:R?[\$S5]|R\$\s*)?\s*(\d{1,3}(?:\.\d{3})*,\d{2}|\d+[.,]\d{2})',
        r'(?:Valor\s+total|Valor\s+pago|Tarifa\s+da\s+viagem|Valor\s+nominal|Total\s+a\s+pagar|Valor\s+do\s+documento|Valor:?)\s*(?:\([^)]*\))?\s*:?\s*(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2}|\d+[.,]\d{2})\s*(?:R\$)?(?!\.\d)',
        r'R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2}|\d+[.,]\d{2})(?!\.\d)',
        r'(\d{1,3}(?:\.\d{3})*,\d{2}|\d+[.,]\d{2})\s*R\$(?!\.\d)',
    ]
    for p in padroes_texto:
        m = re.search(p, texto_str, re.IGNORECASE)
        if m:
            v_str = m.group(1).replace('.', '').replace(',', '.') if ',' in m.group(1) else m.group(1)
            v = float(v_str)
            if v > 0:
                return v

    alvo_nome = nome_arquivo if nome_arquivo else texto_str
    alvo_nome = re.sub(r'WhatsApp Image \d{4}-\d{2}-\d{2}[^.]*', '', alvo_nome, flags=re.IGNORECASE)
    alvo_nome = re.sub(r'\bat\s+\d{1,2}[.]\d{2}(?:[.]\d{2})?\b', '', alvo_nome, flags=re.IGNORECASE)
    alvo_nome = re.sub(r'\b\d{2}[.]\d{2}[.]\d{2}\b', '', alvo_nome)
    m = re.search(r'(?<![\d.,])(\d+)[.,](\d{2})(?![\d])', alvo_nome)
    if m:
        return float(f"{m.group(1)}.{m.group(2)}")
    return 0.0


def classificar_despesa(texto, valor=0.0, nome_arquivo=""):
    texto_norm = normalizar(texto) + " " + normalizar(nome_arquivo)

    # Bloqueio: faturas gerais de cartão de crédito não podem ser atribuídas a uma rubrica específica
    # só porque mencionam um serviço (como netflix, ifood, etc.) em seus lançamentos
    eh_fatura_cartao = any(k in texto_norm for k in ['fatura do seu cartao', 'total a pagar', 'pagamento minimo', 'unique mastercard', 'santander mastercard', 'fatura fechada'])
    if eh_fatura_cartao and 'picpay' not in texto_norm:
        return None, None, "", "fatura geral de cartão de crédito"

    for regra in REGRAS_DESPESA:
        for kw in regra['keywords']:
            if normalizar(kw) in texto_norm:
                return regra['rubrica'], regra['bloco'], regra.get('sufixo', ''), kw

        if valor in regra.get('valores_tipicos', []):
            return regra['rubrica'], regra['bloco'], regra.get('sufixo', ''), f"valor {valor:.2f}"

    return None, None, "", "não identificada"


def processar_extrato_ifood_pago(dados_bytes, nome_original, pasta_drive_base=r"H:\Meu Drive\GASTOS", pasta_local_backup=r"d:\PjePlus\Gastos\compilados_ifood"):
    """Processa um extrato consolidado do iFood Pago (PDF ou imagem):
    - Extrai todos os pedidos válidos.
    - Elimina duplicatas de pedidos repetidos nas capturas.
    - Mantém o cabeçalho original do iFood Pago em cada PDF mensal.
    - Gera exatamente 1 PDF por mês: '{soma:.2f} ifood.pdf'.
    - Salva na pasta correspondente 'Bloco B - Gerais / Mercado Açougue Padaria'.
    """
    pastas_meses_map = {
        (2026, 1):  "01 - Janeiro 2026",
        (2026, 2):  "02 - Fevereiro 2026",
        (2026, 3):  "03 - Março 2026",
        (2026, 4):  "04 - Abril 2026",
        (2026, 5):  "05 - Maio 2026",
        (2026, 6):  "06 - Junho 2026",
        (2026, 7):  "07 - Julho 2026",
        (2026, 8):  "08 - Agosto 2026",
        (2026, 9):  "09 - Setembro 2026",
        (2026, 10): "10 - Outubro 2026",
    }

    is_pdf = nome_original.lower().endswith('.pdf') or dados_bytes[:4] == b'%PDF'
    imagens = []
    if is_pdf:
        doc = fitz.open(stream=dados_bytes, filetype="pdf")
        for pag in doc:
            pix = pag.get_pixmap(dpi=150)
            imagens.append(Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB"))
        doc.close()
    else:
        imagens.append(Image.open(io.BytesIO(dados_bytes)).convert("RGB"))

    if not imagens:
        return []

    # Cabeçalho do iFood Pago da primeira página (mantém status bar + logo + filtros)
    img_ref = imagens[0]
    cabecalho = img_ref.crop((0, 0, img_ref.width, 206))

    todos_pedidos = []

    for pag_idx, img in enumerate(imagens):
        data = pytesseract.image_to_data(img, lang='por+eng', output_type=pytesseract.Output.DICT)

        linhas = {}
        for i in range(len(data['text'])):
            t = data['text'][i].strip()
            if not t: continue
            lid = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
            linhas.setdefault(lid, []).append((data['top'][i], data['left'][i], data['width'][i], data['height'][i], t))

        linhas_ord = []
        for lid, wlist in linhas.items():
            top = min(w[0] for w in wlist)
            bottom = max(w[0] + w[3] for w in wlist)
            txt = ' '.join(w[4] for w in wlist)
            linhas_ord.append((top, bottom, txt))
        linhas_ord.sort(key=lambda x: x[0])

        y_corte_topo = 210 if pag_idx == 0 else 125
        linhas_itens = [l for l in linhas_ord if l[0] >= y_corte_topo]

        for idx, (top, bottom, txt) in enumerate(linhas_itens):
            m_ped = re.search(r'Pedido\s+(?:n[ºo°\s]*\s*)?(\d{3,5})\s*[-–]\s*(\d{2})[/.-](\d{2})[/.-](20\d{2})', txt, re.IGNORECASE)
            if m_ped:
                pid = m_ped.group(1)
                dia, mes, ano = int(m_ped.group(2)), int(m_ped.group(3)), int(m_ped.group(4))
                m_hora = re.search(r'(\d{1,2}:\d{2})', txt)
                hora = m_hora.group(1) if m_hora else ""

                valor = None
                restaurante = ""
                y_item_top = top - 65

                for k in range(max(0, idx - 4), idx):
                    c_top, c_bot, c_txt = linhas_itens[k]
                    m_val = re.search(r'(?:R\$|RS|R5|R|\$)\s*(\d{1,3}[.,]\d{2})', c_txt)
                    if m_val:
                        valor = float(m_val.group(1).replace(',', '.'))
                        rest_part = re.sub(r'(?:R\$|RS|R5|R|\$)\s*(\d{1,3}[.,]\d{2})', '', c_txt).strip()
                        if rest_part:
                            restaurante = rest_part
                        y_item_top = min(y_item_top, c_top)
                    elif not restaurante and not any(w in c_txt.lower() for w in ['crédito', 'credito', 'mastercard', 'nubank', 'pago', 'pedido']):
                        restaurante = c_txt
                        y_item_top = min(y_item_top, c_top)

                if valor is not None:
                    todos_pedidos.append({
                        "pag_idx": pag_idx,
                        "img": img,
                        "pid": pid,
                        "dia": dia, "mes": mes, "ano": ano,
                        "hora": hora,
                        "valor": valor,
                        "restaurante": restaurante,
                        "y_bot": bottom,
                        "y_top": y_item_top
                    })

    # Deduplicação de pedidos repetidos
    unicos = {}
    for p in todos_pedidos:
        chave = (p["pid"], p["dia"], p["mes"], p["ano"])
        if chave not in unicos:
            unicos[chave] = p

    pedidos_por_pag = {}
    for p in unicos.values():
        pedidos_por_pag.setdefault(p["pag_idx"], []).append(p)

    for pag_idx, plist in pedidos_por_pag.items():
        img = imagens[pag_idx]
        plist.sort(key=lambda x: x["y_bot"])
        for idx, ped in enumerate(plist):
            y_bot = ped["y_bot"]
            y_top = ped["y_top"]
            if idx == 0:
                y1 = max(0, y_top - 12)
            else:
                y_ant_bot = plist[idx - 1]["y_bot"]
                y1 = (y_ant_bot + y_top) // 2

            if idx == len(plist) - 1:
                y2 = min(img.height, y_bot + 12)
            else:
                y_prox_top = plist[idx + 1]["y_top"]
                y2 = (y_bot + y_prox_top) // 2

            ped["crop_img"] = img.crop((0, y1, img.width, y2))

    pedidos_por_mes = {}
    for p in unicos.values():
        pedidos_por_mes.setdefault((p["ano"], p["mes"]), []).append(p)

    os.makedirs(pasta_local_backup, exist_ok=True)
    resultados = []

    for (ano, mes), itens in sorted(pedidos_por_mes.items()):
        itens.sort(key=lambda x: (x["ano"], x["mes"], x["dia"], x["hora"]), reverse=True)
        soma_mes = sum(x["valor"] for x in itens)
        nome_pdf = f"{soma_mes:.2f} ifood.pdf"

        largura = cabecalho.width
        altura_itens = sum(x["crop_img"].height for x in itens)
        altura_total = cabecalho.height + altura_itens + 20

        img_mes = Image.new("RGB", (largura, altura_total), (255, 255, 255))
        img_mes.paste(cabecalho, (0, 0))

        y_atual = cabecalho.height
        for x in itens:
            img_mes.paste(x["crop_img"], (0, y_atual))
            y_atual += x["crop_img"].height

        buf = io.BytesIO()
        img_mes.save(buf, format="PNG", optimize=True)
        png_bytes = buf.getvalue()

        doc_pdf = fitz.open()
        p_pdf = doc_pdf.new_page(width=largura, height=altura_total)
        p_pdf.insert_image(fitz.Rect(0, 0, largura, altura_total), stream=png_bytes)
        pdf_bytes = doc_pdf.tobytes(garbage=4, deflate=True)
        doc_pdf.close()

        caminho_local = os.path.join(pasta_local_backup, f"{ano}_{mes:02d}_{nome_pdf}")
        with open(caminho_local, "wb") as f:
            f.write(pdf_bytes)

        pasta_mes_nome = pastas_meses_map.get((ano, mes))
        caminho_drive_final = None
        if pasta_mes_nome and os.path.exists(pasta_drive_base):
            dir_mes = os.path.join(pasta_drive_base, pasta_mes_nome, "Bloco B - Gerais")
            if os.path.exists(dir_mes):
                pasta_alvo = None
                for sub in os.listdir(dir_mes):
                    if "mercado" in sub.lower():
                        pasta_alvo = os.path.join(dir_mes, sub)
                        break
                if not pasta_alvo:
                    pasta_alvo = os.path.join(dir_mes, "Mercado Açougue Padaria")
                    os.makedirs(pasta_alvo, exist_ok=True)

                dir_legado = os.path.join(pasta_alvo, "[LEGADO_INDIVIDUAIS_SUBSTITUIDOS]")
                for f_ant in os.listdir(pasta_alvo):
                    if 'ifood' in f_ant.lower() and f_ant != nome_pdf and f_ant != "[LEGADO_INDIVIDUAIS_SUBSTITUIDOS]":
                        os.makedirs(dir_legado, exist_ok=True)
                        try:
                            os.replace(os.path.join(pasta_alvo, f_ant), os.path.join(dir_legado, f_ant))
                        except Exception:
                            pass

                caminho_drive_final = os.path.join(pasta_alvo, nome_pdf)
                with open(caminho_drive_final, "wb") as f:
                    f.write(pdf_bytes)

        resultados.append({
            "ano": ano,
            "mes": mes,
            "pasta_mes": pasta_mes_nome,
            "qtd_pedidos": len(itens),
            "total": soma_mes,
            "nome_pdf": nome_pdf,
            "caminho_local": caminho_local,
            "caminho_drive": caminho_drive_final
        })

    return resultados


def processar_pasta_99_transporte(pasta_99=r"d:\PjePlus\Gastos\99", pasta_drive_base=r"H:\Meu Drive\GASTOS", pasta_local_backup=r"d:\PjePlus\Gastos\compilados_transporte"):
    """Processa prints da pasta 99 de transporte:
    - Extrai todas as corridas concluídas.
    - Elimina duplicatas de capturas sobrepostas.
    - Mantém o cabeçalho oficial do aplicativo 99 em cada PDF mensal.
    - Gera exatamente 1 PDF por mês: '{soma:.2f} OLLIE TRANSPORTE.pdf'.
    - Salva na pasta correspondente 'Bloco A - Individuais / Transporte'.
    - Arquiva recibos avulsos pré-existentes na pasta legado para evitar dupla contagem.
    """
    import shutil
    pastas_meses_map = {
        (2026, 1):  "01 - Janeiro 2026",
        (2026, 2):  "02 - Fevereiro 2026",
        (2026, 3):  "03 - Março 2026",
        (2026, 4):  "04 - Abril 2026",
        (2026, 5):  "05 - Maio 2026",
        (2026, 6):  "06 - Junho 2026",
        (2026, 7):  "07 - Julho 2026",
        (2026, 8):  "08 - Agosto 2026",
        (2026, 9):  "09 - Setembro 2026",
        (2026, 10): "10 - Outubro 2026",
    }
    meses_pt = {
        'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
        'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
    }

    if not os.path.exists(pasta_99):
        return []

    files = sorted([f for f in os.listdir(pasta_99) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    if not files:
        return []

    img_ref = Image.open(os.path.join(pasta_99, files[0]))
    if img_ref.width == 1080:
        img_ref = img_ref.resize((540, int(img_ref.height * 0.5)), Image.Resampling.LANCZOS)
    cabecalho = img_ref.crop((0, 65, 540, 245))

    todas = []
    for idx, f in enumerate(files):
        fpath = os.path.join(pasta_99, f)
        img = Image.open(fpath)
        w, h = img.size

        if w == 1080:
            new_w = 540
            new_h = int(h * 0.5)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            w, h = new_w, new_h

        img_2x = img.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
        enh = ImageEnhance.Contrast(img_2x).enhance(2.0)
        data = pytesseract.image_to_data(enh, lang='por+eng', output_type=pytesseract.Output.DICT)

        palavras = []
        for i in range(len(data['text'])):
            t = data['text'][i].strip()
            if not t:
                continue
            top = data['top'][i] // 2
            left = data['left'][i] // 2
            width = data['width'][i] // 2
            height = data['height'][i] // 2
            palavras.append({
                'text': t, 'top': top, 'left': left, 'width': width, 'height': height,
                'y_mid': top + height // 2
            })

        cards_idx = [w_info for w_info in palavras if w_info['text'].lower() in ['pop', 'concluida', 'concluída', 'cancelada', 'reembolsado', 'reembolsada']]
        linhas_status = []
        for ci in cards_idx:
            y = ci['y_mid']
            adicionado = False
            for ls in linhas_status:
                if abs(ls['y'] - y) < 25:
                    ls['palavras'].append(ci)
                    adicionado = True
                    break
            if not adicionado:
                linhas_status.append({'y': y, 'palavras': [ci]})

        linhas_status.sort(key=lambda x: x['y'])
        status_validos = [ls for ls in linhas_status if ls['y'] >= 240]

        for i, ls in enumerate(status_validos):
            y_status = ls['y']
            if i == 0:
                y_top = max(245, y_status - 65)
            else:
                y_top = (status_validos[i-1]['y'] + y_status) // 2

            if i == len(status_validos) - 1:
                y_bot = min(h, y_status + 120)
            else:
                y_bot = (y_status + status_validos[i+1]['y']) // 2

            words_card = [p for p in palavras if y_status - 55 <= p['top'] <= y_status + 65]
            words_card.sort(key=lambda x: (x['top'] // 15, x['left']))
            txt_card = " ".join([p['text'] for p in words_card])

            words_below = [p for p in palavras if y_status + 10 <= p['top'] <= y_status + 65]
            txt_below = " ".join([w['text'] for w in words_below])

            status = 'CONCLUIDA'
            if any(term in txt_card.lower() for term in ['cancelada', 'reembolsado', 'reembolsada']):
                status = 'CANCELADA'

            m_val = re.search(r'(?:R\$|RS|R|\$)\s*(\d{1,3}[.,]\d{2})', txt_card)
            valor = float(m_val.group(1).replace(',', '.')) if m_val else 0.0

            m_mes = re.search(r'\b(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\w*\b', txt_below, re.IGNORECASE)
            mes_num = meses_pt.get(m_mes.group(1).lower()[:3]) if m_mes else None

            m_hora = re.search(r'\b(\d{1,2})[.:°](\d{2})\b', txt_below)
            hora = f"{int(m_hora.group(1)):02d}:{m_hora.group(2)}" if m_hora else ""

            dia = None
            txt_for_day = txt_below
            if m_hora:
                txt_for_day = txt_for_day.replace(m_hora.group(0), ' ')
            if m_val:
                txt_for_day = txt_for_day.replace(m_val.group(0), ' ')

            for t in txt_for_day.split():
                t_clean = t.replace('O', '0').replace('o', '0').replace('I', '1').replace('l', '1')
                digits = re.findall(r'\d+', t_clean)
                if digits:
                    val_d = int(digits[-1])
                    if 1 <= val_d <= 31:
                        dia = val_d
                        break

            if status == 'CONCLUIDA' and dia is not None and mes_num is not None and valor > 0:
                crop_card = img.crop((0, y_top, 540, y_bot))
                todas.append({
                    'img_idx': idx + 1,
                    'file': f,
                    'dia': dia,
                    'mes_num': mes_num,
                    'ano': 2026,
                    'hora': hora,
                    'valor': valor,
                    'crop_img': crop_card
                })

    unicas = {}
    for c in todas:
        chave = (c['dia'], c['mes_num'], c['hora'], c['valor'])
        if chave not in unicas:
            unicas[chave] = c

    por_mes = {}
    for c in unicas.values():
        por_mes.setdefault((c['ano'], c['mes_num']), []).append(c)

    os.makedirs(pasta_local_backup, exist_ok=True)
    resultados = []

    for (ano, mes), itens in sorted(por_mes.items()):
        itens.sort(key=lambda x: (x['dia'], x['hora']), reverse=True)
        soma_mes = sum(x['valor'] for x in itens)
        nome_pdf = f"{soma_mes:.2f} OLLIE TRANSPORTE.pdf"

        largura = cabecalho.width
        altura_itens = sum(x["crop_img"].height for x in itens)
        altura_total = cabecalho.height + altura_itens + 20

        img_mes = Image.new("RGB", (largura, altura_total), (255, 255, 255))
        img_mes.paste(cabecalho, (0, 0))

        y_atual = cabecalho.height
        for x in itens:
            img_mes.paste(x["crop_img"], (0, y_atual))
            y_atual += x["crop_img"].height

        buf = io.BytesIO()
        img_mes.save(buf, format="PNG", optimize=True)
        png_bytes = buf.getvalue()

        doc_pdf = fitz.open()
        p_pdf = doc_pdf.new_page(width=largura, height=altura_total)
        p_pdf.insert_image(fitz.Rect(0, 0, largura, altura_total), stream=png_bytes)
        pdf_bytes = doc_pdf.tobytes(garbage=4, deflate=True)
        doc_pdf.close()

        caminho_local = os.path.join(pasta_local_backup, f"{ano}_{mes:02d}_{nome_pdf}")
        with open(caminho_local, "wb") as f:
            f.write(pdf_bytes)

        pasta_mes_nome = pastas_meses_map.get((ano, mes))
        caminho_drive_final = None
        if pasta_mes_nome and os.path.exists(pasta_drive_base):
            dir_mes = os.path.join(pasta_drive_base, pasta_mes_nome)
            dir_bloco_a = os.path.join(dir_mes, "Bloco A - Individuais")
            dir_transporte = os.path.join(dir_bloco_a, "Transporte")
            os.makedirs(dir_transporte, exist_ok=True)

            caminho_drive_final = os.path.join(dir_transporte, nome_pdf)
            with open(caminho_drive_final, "wb") as f:
                f.write(pdf_bytes)

            if mes == 5 and ano == 2026:
                pasta_legado = os.path.join(dir_transporte, "[LEGADO_INDIVIDUAIS_SUBSTITUIDOS]")
                os.makedirs(pasta_legado, exist_ok=True)
                for arq in os.listdir(dir_transporte):
                    if arq.lower().startswith("ollie transporte 99receipt") or arq == "OLLIE TRANSPORTE R$13.86 - Pop - Caraguatatuba.pdf":
                        orig = os.path.join(dir_transporte, arq)
                        dest = os.path.join(pasta_legado, arq)
                        try:
                            shutil.move(orig, dest)
                        except Exception:
                            pass

        resultados.append({
            "ano": ano,
            "mes": mes,
            "pasta_mes": pasta_mes_nome,
            "qtd_corridas": len(itens),
            "total": soma_mes,
            "nome_pdf": nome_pdf,
            "caminho_local": caminho_local,
            "caminho_drive": caminho_drive_final
        })

    return resultados


def processar_pasta_farmacia(pasta_farmacia=r"d:\PjePlus\Gastos\farmacia", pasta_drive_base=r"H:\Meu Drive\GASTOS", pasta_local_backup=r"d:\PjePlus\Gastos\compilados_farmacia", drive=None, drive_idx=None, dry_run=False):
    """Processa prints da pasta farmacia (Drogasil / Droga Raia):
    - Extrai todos os pedidos com status, data e valor total ('Feito em DD/MM/AAAA • Total R$ XX,XX').
    - Elimina duplicatas de capturas sobrepostas mantendo o recorte mais completo.
    - Mantém o cabeçalho oficial do aplicativo ('Meus pedidos') em cada PDF mensal.
    - Gera exatamente 1 PDF por mês: '{soma:.2f} OLLIE FARMACIA.pdf'.
    - Salva na pasta correspondente 'Bloco I - Individuais / Farmácia e Higiene'.
    - No mês de Maio/2026, arquiva recibos individuais já contemplados na pasta de legado.
    """
    comum.configurar_stdout()
    pastas_meses_map = {
        (2026, 1):  "01 - Janeiro 2026",
        (2026, 2):  "02 - Fevereiro 2026",
        (2026, 3):  "03 - Março 2026",
        (2026, 4):  "04 - Abril 2026",
        (2026, 5):  "05 - Maio 2026",
        (2026, 6):  "06 - Junho 2026",
        (2026, 7):  "07 - Julho 2026",
        (2026, 8):  "08 - Agosto 2026",
        (2026, 9):  "09 - Setembro 2026",
        (2026, 10): "10 - Outubro 2026",
    }
    if not os.path.exists(pasta_farmacia):
        print(f"⚠️  Pasta não encontrada: {pasta_farmacia}")
        return []

    # Localizar imagens de prints (ignora zip e pdf de extrato)
    files = sorted([
        f for f in os.listdir(pasta_farmacia)
        if f.lower().endswith(('.jpg', '.jpeg', '.png')) and not f.startswith(('desktop', 'temp'))
    ])
    if not files:
        print(f"⚠️  Nenhuma imagem encontrada em {pasta_farmacia}")
        return []

    # Cabeçalho do app Meus Pedidos (primeira página, topo com status bar + Meus pedidos)
    img_ref = Image.open(os.path.join(pasta_farmacia, files[0]))
    largura = img_ref.width
    cabecalho = img_ref.crop((0, 0, largura, 135))

    todos_pedidos = []
    for fname in files:
        fpath = os.path.join(pasta_farmacia, fname)
        img = Image.open(fpath)
        data = pytesseract.image_to_data(img, lang='por+eng', output_type=pytesseract.Output.DICT)

        feitos = []
        for i in range(len(data['text'])):
            t = data['text'][i].strip().lower()
            if t == 'feito':
                y_f = data['top'][i]
                nearby = [data['text'][j].strip() for j in range(len(data['text'])) if abs(data['top'][j] - y_f) <= 15 and data['text'][j].strip()]
                line_str = ' '.join(nearby)
                m_dt = re.search(r'(\d{2})/(\d{2})/(20\d{2})', line_str)
                m_vl = re.search(r'(?:R\$|RS|R|\$)\s*(\d+[.,]\d{2})', line_str)
                if m_dt and m_vl:
                    dia, mes, ano = int(m_dt.group(1)), int(m_dt.group(2)), int(m_dt.group(3))
                    val = float(m_vl.group(1).replace(',', '.'))
                    feitos.append({
                        'y_f': y_f,
                        'dia': dia, 'mes': mes, 'ano': ano,
                        'data_str': f'{dia:02d}/{mes:02d}/{ano}',
                        'valor': val
                    })

        feitos.sort(key=lambda x: x['y_f'])
        for idx, f_info in enumerate(feitos):
            y1 = max(135, f_info['y_f'] - 32)
            if idx == len(feitos) - 1:
                y2 = 1095
            else:
                y2 = max(135, feitos[idx + 1]['y_f'] - 32)

            crop = img.crop((0, y1, img.width, y2))
            f_info['crop'] = crop
            f_info['height'] = crop.height
            f_info['fname'] = fname
            todos_pedidos.append(f_info)

    # Deduplicação mantendo o recorte de maior altura (mais completo)
    unicos = {}
    for c in todos_pedidos:
        chave = (c['ano'], c['mes'], c['dia'], round(c['valor'], 2))
        if chave not in unicos or c['height'] > unicos[chave]['height']:
            unicos[chave] = c

    # Agrupar por (ano, mes)
    por_mes = {}
    for c in unicos.values():
        por_mes.setdefault((c['ano'], c['mes']), []).append(c)

    os.makedirs(pasta_local_backup, exist_ok=True)
    resultados = []

    print(f"\n[FARMACIA] Processando gastos de Farmacia: {len(unicos)} pedidos unicos detectados em {len(por_mes)} meses...")

    for (ano, mes), itens in sorted(por_mes.items()):
        itens.sort(key=lambda x: (x['ano'], x['mes'], x['dia']), reverse=True)
        soma_mes = sum(x['valor'] for x in itens)
        nome_pdf = f"{soma_mes:.2f} OLLIE FARMACIA.pdf"

        largura_doc = cabecalho.width
        altura_itens = sum(x['crop'].height for x in itens)
        altura_total = cabecalho.height + altura_itens + 20

        img_mes = Image.new('RGB', (largura_doc, altura_total), (255, 255, 255))
        img_mes.paste(cabecalho, (0, 0))
        y_cur = cabecalho.height
        for it in itens:
            img_mes.paste(it['crop'], (0, y_cur))
            y_cur += it['crop'].height

        buf = io.BytesIO()
        img_mes.save(buf, format='PNG', optimize=True)
        png_bytes = buf.getvalue()

        doc_pdf = fitz.open()
        p_pdf = doc_pdf.new_page(width=largura_doc, height=altura_total)
        p_pdf.insert_image(fitz.Rect(0, 0, largura_doc, altura_total), stream=png_bytes)
        pdf_bytes = doc_pdf.tobytes(garbage=4, deflate=True)
        doc_pdf.close()

        # 1. Salvar backup local
        caminho_local = os.path.join(pasta_local_backup, f"{ano}_{mes:02d}_{nome_pdf}")
        with open(caminho_local, "wb") as f:
            f.write(pdf_bytes)

        pasta_mes_nome = pastas_meses_map.get((ano, mes))
        caminho_drive_final = None

        # 2. Salvar em H:\Meu Drive\GASTOS se existir
        if pasta_mes_nome and os.path.exists(pasta_drive_base):
            dir_mes = os.path.join(pasta_drive_base, pasta_mes_nome)
            dir_bloco = os.path.join(dir_mes, "Bloco I - Individuais")
            if not os.path.exists(dir_bloco):
                dir_bloco = os.path.join(dir_mes, "Bloco A - Individuais")

            dir_farmacia = os.path.join(dir_bloco, "Farmácia e Higiene")
            os.makedirs(dir_farmacia, exist_ok=True)

            # Caso especial Maio/2026: arquivar recibos individuais correspondentes aos pedidos do app
            if mes == 5 and ano == 2026:
                pasta_legado = os.path.join(dir_farmacia, "[LEGADO_INDIVIDUAIS_SUBSTITUIDOS]")
                os.makedirs(pasta_legado, exist_ok=True)
                for arq in os.listdir(dir_farmacia):
                    if arq in ("OLLIE FARMÁCIA 29.12", "OLLIE REMEDIOS FARMACIA 65.04"):
                        orig = os.path.join(dir_farmacia, arq)
                        dest = os.path.join(pasta_legado, arq)
                        try:
                            shutil.move(orig, dest)
                        except Exception:
                            pass

            caminho_drive_final = os.path.join(dir_farmacia, nome_pdf)
            with open(caminho_drive_final, "wb") as f:
                f.write(pdf_bytes)

        # 3. Upload via Google Drive API se drive/drive_idx fornecidos
        id_drive = None
        if drive and drive_idx and pasta_mes_nome:
            try:
                f_mes = [f for f in drive_idx.by_id.values() if f.get('name') == pasta_mes_nome and f.get('mimeType') == comum.MIME_PASTA]
                if f_mes:
                    id_mes = f_mes[0]['id']
                    f_bloco = [f for f in drive_idx.listar_filhos(id_mes, apenas_pastas=True) if 'individuais' in comum.normalizar(f.get('name', ''))]
                    if f_bloco:
                        id_bloco = f_bloco[0]['id']
                        f_farm = [f for f in drive_idx.listar_filhos(id_bloco, apenas_pastas=True) if 'farmacia' in comum.normalizar(f.get('name', ''))]
                        if f_farm:
                            id_farm = f_farm[0]['id']
                            existentes = [f for f in drive_idx.listar_filhos(id_farm, apenas_pastas=False) if f.get('name') == nome_pdf]
                            if not existentes:
                                media = MediaIoBaseUpload(io.BytesIO(pdf_bytes), mimetype='application/pdf')
                                f_criado = drive.files().create(
                                    body={'name': nome_pdf, 'parents': [id_farm]},
                                    media_body=media,
                                    fields='id, name, mimeType, parents, md5Checksum, modifiedTime, webViewLink'
                                ).execute()
                                drive_idx.adicionar_arquivo(f_criado)
                                id_drive = f_criado.get('id')
                            else:
                                id_drive = existentes[0]['id']
            except Exception as e_drive:
                print(f"     [AVISO] Upload API Farmacia ({pasta_mes_nome}): {e_drive}")

        print(f"  [OK] [{pasta_mes_nome}] {len(itens)} pedidos | R$ {soma_mes:.2f} -> {nome_pdf}")
        resultados.append({
            "ano": ano,
            "mes": mes,
            "pasta_mes": pasta_mes_nome,
            "qtd_pedidos": len(itens),
            "total": soma_mes,
            "nome_pdf": nome_pdf,
            "caminho_local": caminho_local,
            "caminho_drive": caminho_drive_final,
            "id_drive": id_drive
        })

    return resultados


def eh_extrato_picpay(texto, nome_arquivo="", dados_bytes=None):
    """1. Identifica pelo padrão do documento que é a fatura/extrato do PicPay Card."""
    tn = normalizar(texto)
    nn = normalizar(nome_arquivo)

    # Indicadores de layout da fatura PicPay Card (2 colunas ou recorte de 1 coluna)
    marcadores_fatura = [
        'picpay card', 'transacoes nacionais', 'transagoes nacionais',
        'data estabelecimento valor', 'subtotal dos lancamentos', 'subtotal dos langamentos',
        'total geral dos lancamentos', 'total geral dos langamentos',
        'mastercard platinum', 'mercado zezinho ii', 'panificadora emporio c', 'condesupermercado'
    ]
    qtd_marcadores = sum(1 for m in marcadores_fatura if m in tn)

    if 'picpay' in tn and (qtd_marcadores >= 1 or 'vencimento' in tn or 'fechamento' in tn):
        return True
    if qtd_marcadores >= 1 and ('transacoes nacionais' in tn or 'transagoes nacionais' in tn or 'data estabelecimento' in tn):
        return True
    if qtd_marcadores >= 2:
        return True
    if 'picpay' in nn and (qtd_marcadores >= 1 or 'vencimento' in tn or 'fechamento' in tn or not texto.strip()):
        return True

    # Fallback: verifica cabeçalho ou linhas divisórias de tabela PicPay se dados_bytes for imagem
    if dados_bytes and pytesseract and dados_bytes[:4] != b'%PDF':
        try:
            img = Image.open(io.BytesIO(dados_bytes)).convert('RGB')
            w, h = img.size
            topo = img.crop((0, 0, w, max(60, int(0.14 * h))))
            txt_topo = normalizar(pytesseract.image_to_string(topo, config='--psm 6'))
            if 'picpay' in txt_topo or 'transacoes nacionais' in txt_topo or 'transagoes nacionais' in txt_topo or 'vencimento' in txt_topo:
                return True
        except Exception:
            pass
    return False


def extrair_data_topo_picpay(img_pil, texto_fallback=""):
    """2. Extrai o mês/data do cabeçalho no topo da fatura PicPay (Vencimento / Fechamento)."""
    w, h = img_pil.size
    textos_topo = []
    if pytesseract:
        try:
            topo = img_pil.crop((0, 0, w, max(80, int(0.14 * h)))).convert('L')
            topo_2x = topo.resize((topo.width * 2, topo.height * 2), Image.Resampling.LANCZOS)
            textos_topo.append(pytesseract.image_to_string(topo_2x, config='--psm 6'))
        except Exception:
            pass
    if texto_fallback:
        linhas_ini = "\n".join(str(texto_fallback).splitlines()[:8])
        textos_topo.append(linhas_ini)

    for t in textos_topo:
        for pat in [
            r'Vencimento\s*:?\s*(\d{2})[/.-](\d{2})[/.-](20\d{2})',
            r'Fechamento\s*:?\s*(\d{2})[/.-](\d{2})[/.-](20\d{2})',
            r'\b(\d{2})[/.-](\d{2})[/.-](20\d{2})\b'
        ]:
            m = re.search(pat, t, re.IGNORECASE)
            if m:
                dia, mes, ano = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if 1 <= mes <= 12 and 1 <= dia <= 31:
                    return datetime(ano, mes, dia)
    return None


def _extrair_valor_celula_picpay(img_rgb, x1, x2, y1, y2):
    """Extrai o valor monetário de uma célula limpa da fatura PicPay sem alterar a imagem."""
    from PIL import ImageOps
    cw = x2 - x1
    rx2 = min(img_rgb.width - 2, x2 + 1)
    vc = img_rgb.crop((x2 - int(0.24 * cw), y1 + 3, rx2, y2 - 3)).convert('L')
    arr = np.array(vc)
    h_v = arr.shape[0]
    if h_v > 8:
        top_b = max(2, int(0.26 * h_v))
        bot_b = h_v - top_b
        for r in range(top_b):
            if (arr[r, :] < 55).any() or (arr[r, :] < 235).mean() > 0.5:
                arr[r, :] = 255
        for r in range(bot_b, h_v):
            if (arr[r, :] < 55).any() or (arr[r, :] < 235).mean() > 0.5:
                arr[r, :] = 255

    col_min = arr.min(axis=0)
    segs = []
    in_s = False
    s0 = 0
    for x, v in enumerate(col_min):
        if v < 168:
            if not in_s:
                in_s = True
                s0 = x
        else:
            if in_s:
                in_s = False
                segs.append((s0, x))
    if in_s:
        segs.append((s0, len(col_min)))

    vc_pad = ImageOps.expand(Image.fromarray(arr), border=12, fill=255)
    vc_3x = vc_pad.resize((vc_pad.width * 3, vc_pad.height * 3), Image.Resampling.LANCZOS)
    v_txt = pytesseract.image_to_string(
        vc_3x, config='--psm 7 -c tessedit_char_whitelist=0123456789.,-'
    ).strip()
    v_txt = re.sub(r'^[^0-9]+|[^0-9]+$', '', v_txt)

    int_part, dec_part = None, None
    m_v = re.search(r'(\d{1,4})[.,]\d?(\d{2})$', v_txt)
    if m_v:
        int_part, dec_part = m_v.group(1), m_v.group(2)
    else:
        m_v1 = re.search(r'(\d{1,4})[.,]1$', v_txt)
        if m_v1 and len(segs) >= 2 and (segs[-1][1] - segs[-1][0]) <= 4 and (segs[-2][1] - segs[-2][0]) <= 4:
            int_part, dec_part = m_v1.group(1), '11'
        else:
            m_digits = re.search(r'(\d{3,6})$', v_txt)
            if m_digits:
                d_str = m_digits.group(1)
                if len(d_str) == 5 and d_str[2] == '4':
                    int_part, dec_part = d_str[:2], d_str[3:]
                elif len(d_str) == 4 and len(segs) == 5 and d_str[1] == '4' and (segs[1][1] - segs[1][0]) <= 3:
                    int_part, dec_part = d_str[:2], '1' + d_str[-1]
                elif 3 <= len(d_str) <= 5:
                    int_part, dec_part = d_str[:-2], d_str[-2:]

    if not int_part or not dec_part:
        return 0.0, v_txt

    if int_part.startswith('1') and len(segs) == (len(int_part) + 3 + 1):
        w0 = segs[0][1] - segs[0][0]
        w1 = segs[1][1] - segs[1][0]
        if w0 <= 4 and w1 <= 4:
            int_part = '1' + int_part

    return float(f'{int_part}.{dec_part}'), f'{int_part},{dec_part}'


def processar_extrato_picpay(dados_bytes, nome_original="picpay.jpeg"):
    """Processa comprovante de fatura/extrato PicPay:
    1. Identifica data/mês da despesa pelo cabeçalho do topo (Vencimento/Fechamento)
       ou pelo ciclo de fechamento das datas DD/MM quando for recorte de coluna.
    2. Detecta todas as linhas de lançamento (suporta faturas de 2 colunas e recortes de 1 coluna).
    3. Mantém a imagem original intacta (sem alterar nem reforçar tarjas).
    4. Soma apenas as despesas não tarjadas para renomear o arquivo com o valor exato.
    """
    _, ext = os.path.splitext(nome_original)
    if not ext or ext.lower() not in ('.jpg', '.jpeg', '.png'):
        ext = '.jpeg'

    img = Image.open(io.BytesIO(dados_bytes)).convert('RGB')
    w, h = img.size
    arr = np.array(img)
    gray = arr.mean(axis=2)

    data_topo = extrair_data_topo_picpay(img)

    # Detecta se é layout de 2 colunas (w/h >= 0.75) ou recorte de 1 coluna
    is_two_col = (w / h >= 0.75)
    cols = []
    if is_two_col:
        for sx1, sx2 in [(int(0.02 * w), int(0.50 * w)), (int(0.49 * w), int(0.97 * w))]:
            sub_s = gray[:, sx1:sx2]
            rmask = (((140 <= sub_s) & (sub_s < 238)).mean(axis=1) > 0.65)
            if rmask.any():
                col_active = ((140 <= sub_s[rmask, :]) & (sub_s[rmask, :] < 238)).mean(axis=0) > 0.45
                xs = np.where(col_active)[0]
                if len(xs):
                    cols.append((sx1 + int(xs.min()), sx1 + int(xs.max())))
        if len(cols) < 2:
            cols = [(int(0.032 * w), int(0.490 * w)), (int(0.492 * w), int(0.955 * w))]
    else:
        row_line_mask = (((140 <= gray) & (gray < 238)).mean(axis=1) > 0.60)
        if row_line_mask.any():
            line_rows = gray[row_line_mask, :]
            col_non_white = ((140 <= line_rows) & (line_rows < 238)).mean(axis=0) > 0.45
            segs = []
            in_s = False
            s0 = 0
            for x in range(w):
                if col_non_white[x]:
                    if not in_s:
                        in_s = True
                        s0 = x
                else:
                    if in_s:
                        in_s = False
                        segs.append((s0, x))
            if in_s:
                segs.append((s0, w))
            best_seg = max(segs, key=lambda s: s[1] - s[0]) if segs else (int(0.02 * w), int(0.96 * w))
            cols = [(max(0, best_seg[0]), min(w, best_seg[1]))]
        else:
            cols = [(int(0.02 * w), int(0.96 * w))]

    itens_limpos = []
    qtd_tarjadas = 0
    datas_ddmm_limpas = []

    for idx_col, (x1, x2) in enumerate(cols):
        cw = x2 - x1
        sub = gray[:, x1:x2]
        is_line = ((sub < 238).mean(axis=1) > 0.70) & ((sub < 30).mean(axis=1) < 0.35)
        lines_y = np.where(is_line)[0]
        groups = []
        for y in lines_y:
            if y < int(0.02 * h):
                continue
            if not groups or y - groups[-1][-1] > 4:
                groups.append([y])
            else:
                groups[-1].append(y)
        centers = [int(round(np.mean(g))) for g in groups]
        diffs = [b - a for a, b in zip(centers, centers[1:]) if 18 <= (b - a) <= 90]
        row_h_est = int(round(np.median(diffs))) if diffs else 30

        rows = []
        for k, c in enumerate(centers):
            if k == 0:
                if c - row_h_est >= int(0.02 * h):
                    rows.append((c - row_h_est, c))
            if k + 1 < len(centers):
                b = centers[k + 1]
                gap = b - c
                n_rows = int(round(gap / row_h_est))
                if n_rows == 1 and int(0.68 * row_h_est) <= gap <= int(1.40 * row_h_est):
                    rows.append((c, b))
                elif 2 <= n_rows <= 6 and abs(gap - n_rows * row_h_est) <= max(8, int(0.28 * row_h_est)):
                    for r_i in range(n_rows):
                        ry1 = int(round(c + r_i * (gap / n_rows)))
                        ry2 = int(round(c + (r_i + 1) * (gap / n_rows)))
                        rows.append((ry1, ry2))
                elif gap > row_h_est * 3.0:
                    rows.append((b - row_h_est, b))

        for (y1, y2) in rows:
            rh = y2 - y1
            cy1, cy2 = y1 + int(0.32 * rh), y2 - int(0.32 * rh)
            row_mid = sub[cy1:cy2, :]
            v_blk = int((row_mid[:, int(0.75 * cw):] < 30).sum())
            d_blk = int((row_mid[:, int(0.15 * cw):int(0.75 * cw)] < 30).sum())
            if v_blk > 15 or d_blk > 35:
                qtd_tarjadas += 1
                continue

            valor_linha, val_str = (0.0, "")
            if pytesseract:
                valor_linha, val_str = _extrair_valor_celula_picpay(img, x1, x2, y1, y2)
                if valor_linha > 0 and not data_topo:
                    d_crop = img.crop((x1, y1 + 2, x1 + int(0.18 * cw), y2 - 2)).convert('L')
                    d_2x = d_crop.resize((d_crop.width * 2, d_crop.height * 2), Image.Resampling.LANCZOS)
                    d_txt = pytesseract.image_to_string(d_2x, config='--psm 7').strip()
                    m_d = re.search(r'(\d{2})/(\d{2})', d_txt)
                    if m_d:
                        dia_d, mes_d = int(m_d.group(1)), int(m_d.group(2))
                        if 1 <= dia_d <= 31 and 1 <= mes_d <= 12:
                            datas_ddmm_limpas.append((mes_d, dia_d))

            if valor_linha > 0:
                itens_limpos.append({
                    'coluna': idx_col + 1,
                    'y': (y1, y2),
                    'descricao': val_str,
                    'valor': valor_linha,
                })

    if not data_topo and datas_ddmm_limpas:
        from collections import Counter
        contagem_meses = Counter(m for m, _ in datas_ddmm_limpas)
        mes_base = max(contagem_meses.keys(), key=lambda m: (contagem_meses[m], m))
        datas_filtradas = [(m, d) for (m, d) in datas_ddmm_limpas if abs(m - mes_base) <= 1 or contagem_meses[m] >= 2]
        if not datas_filtradas:
            datas_filtradas = datas_ddmm_limpas
        max_mes, max_dia = max(datas_filtradas)
        mes_fatura = max_mes + 1 if (max_dia >= 19 and max_mes < 12) else max_mes
        data_topo = datetime(2026, mes_fatura, 25)

    soma_total = round(sum(it['valor'] for it in itens_limpos), 2)
    return {
        'eh_picpay': True,
        'data_dt': data_topo,
        'soma': soma_total,
        'itens': itens_limpos,
        'qtd_limpas': len(itens_limpos),
        'qtd_tarjadas': qtd_tarjadas,
        'dados_bytes_tarjados': None,
        'ext': ext,
        'nome_sugerido': f"{soma_total:.2f} picpay{ext}" if soma_total > 0 else f"[SEM_VALOR] picpay{ext}",
    }


def eh_extrato_cantina(texto, nome_arquivo="", dados_bytes=None):
    """Identifica se o documento é o extrato multimês de recargas da Cantina Escolar."""
    nome_low = (nome_arquivo or "").lower()
    if 'cantina' in nome_low:
        return True
    txt_norm = normalizar(texto or "")
    if 'recargas' in txt_norm and ('consumo' in txt_norm or 'estornos' in txt_norm):
        return True
    if len(re.findall(r'\brecarga\b', txt_norm)) >= 2:
        return True
    return False


def analisar_conteudo(dados_bytes, nome_original):
    """Analisa comprovante e aplica a matriz de decisão com degradação graciosa."""
    nome_base, ext = os.path.splitext(nome_original)
    if not ext:
        ext = '.pdf' if dados_bytes[:4] == b'%PDF' else '.png'

    nome_low = nome_original.lower()
    eh_picpay = False
    dados_processados = None
    res_picpay = None

    # 1. 99Receipt: já contém data e valor no nome do arquivo
    if '99receipt' in nome_low or '99 receipt' in nome_low:
        data = extrair_data(nome_original)
        valor = extrair_valor("", nome_original)
        rubrica, bloco, sufixo_regra, motivo = 'Transporte', BLOCO_A, 'OLLIE TRANSPORTE', '99receipt nome'
        texto = ""
    # 1.1 Ollie Plano de Saúde: tratar EXCLUSIVAMENTE pelo nome do arquivo (o holerite tem datas antigas no OCR)
    elif 'plano de saude' in normalizar(nome_low) and 'ollie' in normalizar(nome_low):
        m_suf = re.search(r'[_ -](\d{1,2})[-/.](\d{4})', nome_original)
        if m_suf:
            mes_n, ano_n = int(m_suf.group(1)), int(m_suf.group(2))
            data = datetime(ano_n, mes_n, 1)
        else:
            data = extrair_data(nome_original)
        valor = extrair_valor("", nome_original)
        rubrica, bloco, sufixo_regra, motivo = 'Plano de Saúde e Odontológico', BLOCO_A, 'OLLIE PLANO DE SAUDE', 'ollie plano de saude nome'
        texto = ""
    else:
        texto = extrair_texto_de_bytes(dados_bytes, nome_original)

        # Caso Especial: Fatura / Extrato PicPay Card (imagem com tarjas)
        if dados_bytes[:4] != b'%PDF' and eh_extrato_picpay(texto, nome_original, dados_bytes):
            eh_picpay = True
            res_picpay = processar_extrato_picpay(dados_bytes, nome_original)
            ext = res_picpay['ext']
            data = res_picpay['data_dt'] or extrair_data(texto) or extrair_data(nome_original)
            valor = res_picpay['soma']
            rubrica = 'Outros (Geral) 01'
            bloco = BLOCO_B
            sufixo_regra = 'picpay'
            motivo = f"extrato picpay ({res_picpay['qtd_limpas']} despesas somadas, {res_picpay['qtd_tarjadas']} tarjas reforçadas)"
            dados_processados = res_picpay['dados_bytes_tarjados']
        else:
            # Caso Especial: Extrato de Recargas da Cantina Escolar (imagem multimês salva uma única vez em Janeiro)
            if dados_bytes[:4] != b'%PDF' and eh_extrato_cantina(texto, nome_original, dados_bytes):
                from extrato import parse_extrato_cantina
                txs_mes, totais_mes, total_cantina = parse_extrato_cantina(dados_bytes)
                if len(totais_mes) >= 1:
                    return {
                        'nome_original': nome_original,
                        'data': 'Múltiplas datas (Extrato Cantina Multimês)',
                        'data_dt': None,
                        'mes_contabil': 'Janeiro 2026',
                        'pasta_mes_drive': '01 - Janeiro 2026',
                        'bloco': BLOCO_A,
                        'rubrica': 'Alimentação rua e Cantina Escolar',
                        'pasta_drive_rubrica': comum.PASTA_DRIVE.get('Alimentação rua e Cantina Escolar', 'Alimentação rua e Cantina Escolar'),
                        'valor': total_cantina,
                        'status': 'COMPLETO',
                        'nome_sugerido': 'cantina.jpeg' if ext.lower() in ('.jpg', '.jpeg') else f'cantina{ext}',
                        'destino_tipo': 'rubrica',
                        'motivo': f'extrato cantina escolar ({len(totais_mes)} meses consolidados)',
                        'aviso': f"Extrato Cantina Escolar: R$ {total_cantina:.2f} distribuído mês a mês na planilha em 'Alimentação rua e Cantina Escolar'. Arquivo salvo apenas uma vez em Janeiro 2026.",
                        'totais_por_mes': totais_mes
                    }

            # Caso Especial: Extrato Consolidado do iFood Pago (Multi-pedidos)
            texto_norm_ifood = normalizar(texto)
            if ('ifood pago' in texto_norm_ifood or 'ifeed pago' in texto_norm_ifood) and len(re.findall(r'Pedido\s+(?:n[ºo°\s]*\s*)?\d{3,5}', texto, re.IGNORECASE)) >= 2:
                resumos = processar_extrato_ifood_pago(dados_bytes, nome_original)
                total_extrato = sum(r['total'] for r in resumos)
                return {
                    'nome_original': nome_original,
                    'data': 'Múltiplas datas (Extrato iFood)',
                    'data_dt': None,
                    'mes_contabil': 'Multi-mês',
                    'pasta_mes_drive': 'Distribuído por mês em Mercado Açougue Padaria',
                    'bloco': BLOCO_B,
                    'rubrica': 'Mercado/Açougue/Padaria',
                    'pasta_drive_rubrica': 'Mercado Açougue Padaria',
                    'valor': total_extrato,
                    'status': 'COMPLETO',
                    'nome_sugerido': '[EXTRATO_IFOOD_DISTRIBUIDO]',
                    'destino_tipo': 'extrato_processado',
                    'motivo': f'extrato ifood pago ({len(resumos)} meses consolidados)',
                    'aviso': f"Extrato iFood Pago: {len(resumos)} PDFs mensais criados com cabeçalho em 'Mercado Açougue Padaria'.",
                    'extrato_detalhes': resumos
                }

            # Caso Especial: Extrato Geral Consolidado (Banco Inter / Débito / Multimês)
            texto_norm = normalizar(texto)
            if ('banco inter' in texto_norm or 'extrato' in nome_low) and (
                'categorias alimentacao' in texto_norm or 'saldo por transacao' in texto_norm or 'compra no debito' in texto_norm
            ):
                from extrato import parse_extrato_pdf
                txs_mes, totais_mes, total_extrato = parse_extrato_pdf(dados_bytes)
                if len(totais_mes) > 1:
                    return {
                        'nome_original': nome_original,
                        'data': 'Múltiplas datas (Extrato Geral Consolidado)',
                        'data_dt': None,
                        'mes_contabil': 'Janeiro 2026',
                        'pasta_mes_drive': '01 - Janeiro 2026',
                        'bloco': BLOCO_B,
                        'rubrica': 'Mercado/Açougue/Padaria',
                        'pasta_drive_rubrica': None,
                        'valor': total_extrato,
                        'status': 'COMPLETO',
                        'nome_sugerido': nome_original,
                        'destino_tipo': 'extrato_geral_raiz_janeiro',
                        'motivo': f'extrato geral ({len(totais_mes)} meses consolidados)',
                        'aviso': f"Extrato Geral Consolidado: R$ {total_extrato:.2f} distribuído por competência na planilha em 'Mercado/Açougue/Padaria'. Arquivo mantido na raiz de Janeiro 2026.",
                        'totais_por_mes': totais_mes
                    }

            data = extrair_data(texto) or extrair_data(nome_original)
            valor = extrair_valor(texto, nome_original)
            rubrica, bloco, sufixo_regra, motivo = classificar_despesa(texto, valor, nome_original)

    data_ok = bool(data)
    valor_ok = bool(valor > 0) or (valor == 0.0 and ('0,00' in str(texto) or 'r$ 0,00' in str(texto).lower() or 'r$0,00' in str(texto).lower()))
    rubrica_ok = bool(rubrica is not None)

    # Identificação de Mês
    if data_ok:
        nome_mes = f"{MESES[data.month - 1]} {data.year}"
        diff_meses = (data.year - comum.INICIO[0]) * 12 + (data.month - comum.INICIO[1]) + 1
        if diff_meses >= 1:
            pasta_mes = f"{diff_meses:02d} - {nome_mes}"
        else:
            pasta_mes = f"[FORA_DO_PERIODO] {nome_mes}"
    else:
        nome_mes, pasta_mes = None, None

    nome_limpo = higienizar_fragmento(nome_base)
    is_ifood = (
        'ifood' in str(motivo).lower() or 'ifood' in nome_low or
        (texto and any(w in str(texto).lower() for w in ['ifood', 'cardapio', 'previsao de entrega', 'pago pelo app', 'data do pedido']))
    )

    # --- MATRIZ DE DEGRAÇÃO GRACIOSA ---
    if data_ok and valor_ok and rubrica_ok:
        status = 'COMPLETO'
        det = f" {sufixo_regra}" if sufixo_regra else ""
        if eh_picpay:
            det = " picpay"
        elif 'tenda' in motivo or 'tenda' in nome_low:
            det = " tenda"
        elif is_ifood and rubrica == 'Mercado/Açougue/Padaria':
            suf_data = f" {data.day:02d}-{data.month:02d}" if data_ok else ""
            det = f" ifood{suf_data}"
        elif rubrica == 'Internet':
            det = " vivo fibra"
        elif rubrica == 'Aluguel':
            det = ""
        elif rubrica == 'Transporte':
            det = " OLLIE TRANSPORTE"
        elif rubrica == 'Plano de Saúde e Odontológico':
            det = " OLLIE PLANO DE SAUDE"
        elif rubrica == 'Psicoterapia':
            det = ""
        nome_sugerido = f"{valor:.2f}{det}{ext}".replace('  ', ' ')
        destino_tipo = 'rubrica'
        aviso = None

    elif data_ok and valor_ok and not rubrica_ok:
        status = 'PENDENTE_RUBRICA'
        nome_sugerido = f"{valor:.2f} [REVISAR_RUBRICA] {nome_limpo}{ext}"
        destino_tipo = 'revisar_mes'
        aviso = f"Valor R$ {valor:.2f} e mês {nome_mes} identificados, mas o tipo de despesa é desconhecido. Movido para a pasta '{pasta_mes}/[REVISAR_RUBRICA]/'."

    elif data_ok and not valor_ok and rubrica_ok:
        status = 'PENDENTE_VALOR'
        nome_sugerido = f"[SEM_VALOR] {rubrica} {nome_limpo}{ext}"
        destino_tipo = 'rubrica'
        aviso = f"Categoria '{rubrica}' identificada em {nome_mes}, mas o valor monetário não foi detectado. Movido para a subpasta da rubrica como [SEM_VALOR]."

    elif data_ok and not valor_ok and not rubrica_ok:
        status = 'PENDENTE_VALOR_E_RUBRICA'
        nome_sugerido = f"[REVISAR_TUDO] {nome_limpo}{ext}"
        destino_tipo = 'revisar_mes'
        aviso = f"Mês {nome_mes} identificado pela data, mas valor e categoria são desconhecidos. Movido para '{pasta_mes}/[REVISAR_RUBRICA]/'."

    else:  # not data_ok
        status = 'PENDENTE_DATA'
        prefixo_val = f"{valor:.2f} " if valor_ok else ""
        tag_rub = f"[{comum.PASTA_DRIVE.get(rubrica, rubrica)}] " if rubrica_ok else ""
        nome_sugerido = f"{prefixo_val}{tag_rub}[SEM_DATA] {nome_limpo}{ext}".replace('  ', ' ')
        destino_tipo = 'quarentena_raiz'
        if rubrica_ok:
            aviso = f"Identificado como '{rubrica}' ({'R$ ' + f'{valor:.2f}' if valor_ok else 'sem valor'}), mas a DATA não foi encontrada. Movido para '[REVISAR_SEM_DATA]/' na raiz. Só falta arrastar para a pasta do mês!"
        else:
            aviso = "Data e tipo de despesa não foram encontrados no documento. Movido para a pasta '[REVISAR_SEM_DATA]/' na raiz para conferência."

    return {
        'nome_original': nome_original,
        'data': data.strftime('%d/%m/%Y') if data_ok else "Não identificada",
        'data_dt': data if data_ok else None,
        'mes_contabil': nome_mes,
        'pasta_mes_drive': pasta_mes,
        'bloco': bloco,
        'rubrica': rubrica,
        'pasta_drive_rubrica': comum.PASTA_DRIVE.get(rubrica, rubrica) if rubrica else None,
        'valor': valor,
        'status': status,
        'nome_sugerido': nome_sugerido,
        'destino_tipo': destino_tipo,
        'motivo': motivo,
        'aviso': aviso,
        'eh_picpay': eh_picpay,
        'is_ifood': is_ifood,
        'dados_processados': dados_processados,
        'itens_picpay': res_picpay.get('itens', []) if res_picpay else [],
        'qtd_tarjadas': res_picpay.get('qtd_tarjadas', 0) if res_picpay else 0,
    }


def resolver_pasta_destino(drive, drive_idx, info, dry_run=False):
    """Encontra ou cria a pasta exata no Drive de acordo com o destino_tipo."""
    dt = info['destino_tipo']

    # 0. Extrato consolidado já distribuído diretamente nas pastas mensais
    if dt == 'extrato_processado':
        nome_arqv = "[EXTRATOS_PROCESSADOS]"
        id_arqv, _ = drive_idx.obter_ou_criar_pasta(nome_arqv, ID_PASTA_RAIZ_DRIVE, dry_run=dry_run)
        return id_arqv, f"{nome_arqv}/"

    # 0.1 Extrato geral multimês: salvo na raiz da pasta Janeiro 2026
    if dt == 'extrato_geral_raiz_janeiro':
        id_jan = drive_idx.pasta_do_mes('Janeiro 2026')
        return id_jan, "01 - Janeiro 2026 / [RAIZ]/"

    # 1. Rubrica normal: {pasta_mes}/{bloco}/{rubrica}/
    if dt == 'rubrica':
        id_mes = drive_idx.pasta_do_mes(info['mes_contabil'])
        if not id_mes:
            if info.get('mes_contabil') and not comum.eh_mes_no_periodo(info['mes_contabil']):
                nome_fp = "[REVISAR_FORA_DO_PERIODO]"
                id_fp, _ = drive_idx.obter_ou_criar_pasta(nome_fp, ID_PASTA_RAIZ_DRIVE, dry_run=dry_run)
                return id_fp, f"{nome_fp}/"
            return ID_PASTA_RAIZ_DRIVE, "[RAIZ]/"
        blocos = [f for f in drive_idx.listar_filhos(id_mes, apenas_pastas=True) if f['name'] == info['bloco']]
        if not blocos:
            return id_mes, f"{info['pasta_mes_drive']} /"
        alvo = normalizar(info['pasta_drive_rubrica'])
        for r in drive_idx.listar_filhos(blocos[0]['id'], apenas_pastas=True):
            if normalizar(r['name']) == alvo:
                return r['id'], f"{info['pasta_mes_drive']} / {info['bloco']} / {info['pasta_drive_rubrica']}/"
        return id_mes, f"{info['pasta_mes_drive']} /"

    # 2. Pendente no mês (sem criar pastas de checagem no Drive): salva direto na pasta do mês
    elif dt == 'revisar_mes':
        id_mes = drive_idx.pasta_do_mes(info['mes_contabil'])
        if not id_mes:
            if info.get('mes_contabil') and not comum.eh_mes_no_periodo(info['mes_contabil']):
                nome_fp = "[REVISAR_FORA_DO_PERIODO]"
                id_fp, _ = drive_idx.obter_ou_criar_pasta(nome_fp, ID_PASTA_RAIZ_DRIVE, dry_run=dry_run)
                return id_fp, f"{nome_fp}/"
            return ID_PASTA_RAIZ_DRIVE, "[RAIZ]/"
        return id_mes, f"{info['pasta_mes_drive']} /"

    # 3. Sem data identificada (sem criar pasta de checagem): mantém na raiz do Drive
    elif dt == 'quarentena_raiz':
        return ID_PASTA_RAIZ_DRIVE, "[RAIZ]/"

    return ID_PASTA_RAIZ_DRIVE, "[RAIZ]/"


RE_CONSOLIDADO = comum.RE_CONSOLIDADO

_CACHE_TEXTO_ARQUIVOS_DRIVE = {}


def _obter_texto_arquivo_drive(drive, arq_id, nome_arq):
    if arq_id in _CACHE_TEXTO_ARQUIVOS_DRIVE:
        return _CACHE_TEXTO_ARQUIVOS_DRIVE[arq_id]
    if not drive:
        return ""
    try:
        buf = io.BytesIO()
        req = drive.files().get_media(fileId=arq_id)
        dl = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
        conteudo = buf.getvalue()
        txt = ""
        nome_low = nome_arq.lower()
        if nome_low.endswith('.pdf') or conteudo[:4] == b'%PDF':
            doc = fitz.open(stream=conteudo, filetype='pdf')
            for p in doc:
                txt += (p.get_text() or "") + "\n"
            if not txt.strip() and len(doc) > 0 and pytesseract:
                pix = doc[0].get_pixmap(dpi=150)
                img = Image.open(io.BytesIO(pix.tobytes('png')))
                txt = pytesseract.image_to_string(img, lang='por+eng')
            doc.close()
        elif nome_low.endswith(('.jpg', '.jpeg', '.png')) and pytesseract:
            img = Image.open(io.BytesIO(conteudo))
            txt = pytesseract.image_to_string(img, lang='por+eng')
        _CACHE_TEXTO_ARQUIVOS_DRIVE[arq_id] = txt
        return txt
    except Exception:
        _CACHE_TEXTO_ARQUIVOS_DRIVE[arq_id] = ""
        return ""


def verificar_duplicata_ou_substituicao(drive_idx, id_destino, info, md5_novo=None, timestamp_novo=None, arq_id=None, drive=None):
    """Verifica se o novo arquivo:
    1. É duplicata idêntica (mesmo MD5) de algum arquivo existente.
    2. Para iFood: deduplica por mesma data + mesmo valor ou se já contemplado no extrato consolidado.
    3. Substitui uma versão anterior existente (mesmo mês, mesma rubrica e valor muito próximo/conta única).
    Retorna: (tipo_resultado, arquivo_alvo, mensagem)
    onde tipo_resultado pode ser:
      - 'DUPLICATA_EXATA'
      - 'SUBSTITUIR'
      - 'MANTER_EXISTENTE'
      - 'NOVO'
    """
    if not id_destino or id_destino == ID_PASTA_RAIZ_DRIVE:
        return 'NOVO', None, None

    candidatos = [
        f for f in drive_idx.listar_filhos(id_destino, apenas_pastas=False)
        if not RE_CONSOLIDADO.match(f['name']) and f.get('id') != arq_id
    ]

    # 1. Checagem de Duplicata Idêntica (MD5)
    if md5_novo:
        for f in candidatos:
            if f.get('md5Checksum') == md5_novo:
                return 'DUPLICATA_EXATA', f, f"Arquivo idêntico (mesmo MD5={md5_novo[:8]}) já existe como '{f['name']}'."

    rubrica = info.get('rubrica')
    valor_novo = info.get('valor', 0.0)
    data_novo = info.get('data_dt')
    time_novo = timestamp_novo or datetime.now().isoformat()

    # 2. Checagem Especial para iFood (Deduplicação por Data + Valor ou Extrato Consolidado)
    is_ifood = (
        info.get('is_ifood') or
        'ifood' in str(info.get('nome_sugerido', '')).lower() or
        'ifood' in str(info.get('motivo', '')).lower()
    )
    if is_ifood and valor_novo > 0:
        data_novo_dt = info.get('data_dt')
        data_str = info.get('data') or (data_novo_dt.strftime('%d/%m/%Y') if data_novo_dt else None)
        candidatos_ifood = [f for f in candidatos if 'ifood' in f['name'].lower()]

        for f in candidatos_ifood:
            m_ex = re.search(r'(?<![\d.,])(\d+)[.,](\d{2})(?![\d])', f['name'])
            v_exist = float(f"{m_ex.group(1)}.{m_ex.group(2)}") if m_ex else 0.0

            # Caso 2.1: Mesmo valor (pedido individual repetido)
            if v_exist > 0 and comum.valores_muito_proximos(valor_novo, v_exist):
                mesma_data = False
                if data_novo_dt:
                    # Verifica data no próprio nome do candidato (ex: 45.00 ifood 15-04.pdf)
                    m_d = re.search(r'(\d{2})[-/.](\d{2})(?:[-/.](20\d{2}))?', f['name'])
                    if m_d:
                        d_cand, m_cand = int(m_d.group(1)), int(m_d.group(2))
                        if d_cand == data_novo_dt.day and m_cand == data_novo_dt.month:
                            mesma_data = True
                    # Se não há data no nome, busca no conteúdo do arquivo existente
                    if not mesma_data and drive:
                        txt_cand = _obter_texto_arquivo_drive(drive, f['id'], f['name'])
                        d_ext = extrair_data(txt_cand)
                        if d_ext and (d_ext.day, d_ext.month, d_ext.year) == (data_novo_dt.day, data_novo_dt.month, data_novo_dt.year):
                            mesma_data = True
                        elif not d_ext:
                            padrao_data = f"{data_novo_dt.day:02d}/{data_novo_dt.month:02d}"
                            if padrao_data in txt_cand:
                                mesma_data = True

                # Se confirmou mesma data ou se o nome sugerido é idêntico
                if mesma_data or f['name'] == info.get('nome_sugerido'):
                    msg = f"Comprovante iFood duplicado: já existe pedido com mesmo valor (R$ {valor_novo:.2f}) e mesma data ({data_str or 'identificada'}) como '{f['name']}'."
                    return 'DUPLICATA_EXATA', f, msg

            # Caso 2.2: Candidato é o extrato consolidado mensal do iFood Pago (soma maior)
            elif v_exist > valor_novo and drive:
                txt_cand = _obter_texto_arquivo_drive(drive, f['id'], f['name'])
                if txt_cand:
                    val_str_comma = f"{valor_novo:.2f}".replace('.', ',')
                    val_str_dot = f"{valor_novo:.2f}"
                    tem_val = val_str_comma in txt_cand or val_str_dot in txt_cand
                    tem_dt = False
                    if data_novo_dt:
                        padrao_data = f"{data_novo_dt.day:02d}/{data_novo_dt.month:02d}"
                        tem_dt = padrao_data in txt_cand
                    else:
                        tem_dt = True
                    if tem_val and tem_dt:
                        msg = f"Pedido iFood de R$ {valor_novo:.2f} ({data_str or ''}) já está contemplado no extrato consolidado '{f['name']}' deste mês."
                        return 'DUPLICATA_EXATA', f, msg

    # 3. Checagem de Substituição de Versão ("valor muito próximo, mês e tipo semelhantes")

    # Caso A: Rubrica de Conta Única (Luz, Água, Aluguel, Gás, Internet)
    # Somente substitui se o existente estiver sem valor ou tiver valor muito próximo
    if rubrica and comum.eh_rubrica_conta_unica(rubrica):
        if candidatos:
            existente = sorted(candidatos, key=lambda x: x.get('modifiedTime', ''), reverse=True)[0]
            m_ex = re.search(r'(?<![\d.,])(\d+)[.,](\d{2})(?![\d])', existente['name'])
            if m_ex:
                v_exist = float(f"{m_ex.group(1)}.{m_ex.group(2)}")
            else:
                stem_ex = os.path.splitext(existente['name'])[0].strip()
                v_exist = float(stem_ex) if re.match(r'^\d{1,4}$', stem_ex) else 0.0
            if v_exist == 0.0 or (valor_novo > 0 and comum.valores_muito_proximos(valor_novo, v_exist)):
                time_existente = existente.get('modifiedTime', '')
                if time_novo >= time_existente:
                    return 'SUBSTITUIR', existente, f"Rubrica de conta única '{rubrica}': versão mais recente substitui '{existente['name']}'."
                else:
                    return 'MANTER_EXISTENTE', existente, f"Versão existente '{existente['name']}' já é mais recente."

    # Caso B: Rubricas multi-itens (Mercado, Faxina, Farmácia, Transporte, Cantina, etc.)
    # Nunca substitui nem descarta comprovantes automaticamente, pois despesas com mesmo valor
    # (ex: 2 faxinas de R$ 250 ou vários recibos) são itens legítimos separados.
    return 'NOVO', None, None


def organizar_arquivos_raiz_drive(drive, drive_idx, dry_run=False):
    """Varre a raiz do Drive, aplica degradação graciosa e organiza comprovantes pendentes."""
    filhos_raiz = drive_idx.listar_filhos(ID_PASTA_RAIZ_DRIVE, apenas_pastas=False)

    comprovantes_soltos = [
        f for f in filhos_raiz
        if f.get('mimeType') in ('application/pdf', 'image/png', 'image/jpeg')
        or f['name'].lower().endswith(('.pdf', '.png', '.jpg', '.jpeg'))
    ]

    movidos, relatorio_triagem = 0, []
    if not comprovantes_soltos:
        return processar_picpay_nas_pastas_drive(drive, drive_idx, dry_run=dry_run)

    print(f"\n🔍 Organizando {len(comprovantes_soltos)} comprovante(s) pendente(s) na raiz do Drive...")

    for arq in comprovantes_soltos:
        buf = io.BytesIO()
        dl = MediaIoBaseDownload(buf, drive.files().get_media(fileId=arq['id']))
        done = False
        while not done:
            _, done = dl.next_chunk()
        buf.seek(0)
        dados_bytes = buf.getvalue()

        info = analisar_conteudo(dados_bytes, arq['name'])
        res = resolver_pasta_destino(drive, drive_idx, info, dry_run=dry_run)

        if not res or res[0] == ID_PASTA_RAIZ_DRIVE:
            print(f"   ⚠️  [{arq['name']}]: Não foi possível determinar pasta de destino.")
            continue

        id_dest, caminho_dest = res
        md5_novo = arq.get('md5Checksum') or hashlib.md5(dados_bytes).hexdigest()
        time_novo = arq.get('modifiedTime', '')

        tipo_acao, arq_alvo, msg_acao = verificar_duplicata_ou_substituicao(
            drive_idx, id_dest, info, md5_novo=md5_novo, timestamp_novo=time_novo, arq_id=arq['id'], drive=drive
        )

        if tipo_acao == 'DUPLICATA_EXATA':
            print(f"   ♊ [DUPLICATA IDÊNTICA] {arq['name']} -> já existe como '{arq_alvo['name']}' em {caminho_dest}")
            print(f"      🗑️  Descartando arquivo duplicado da raiz...")
            if not dry_run:
                try:
                    drive.files().update(fileId=arq['id'], body={'trashed': True}).execute()
                except Exception:
                    try:
                        drive.files().update(fileId=arq['id'], removeParents=ID_PASTA_RAIZ_DRIVE).execute()
                    except Exception:
                        pass
                drive_idx.remover_arquivo(arq['id'])
            relatorio_triagem.append({
                'status': 'DUPLICATA_EXATA',
                'nome_original': arq['name'],
                'nome_sugerido': arq_alvo['name'],
                'pasta_mes_drive': caminho_dest,
                'aviso': f"Arquivo idêntico (mesmo MD5) já existia como '{arq_alvo['name']}'. Cópia duplicada descartada da raiz."
            })
            continue

        elif tipo_acao == 'SUBSTITUIR':
            print(f"   🔄 [SUBSTITUIÇÃO] {arq['name']} -> substitui versão anterior '{arq_alvo['name']}' em {caminho_dest}")
            print(f"      🗑️  Movendo versão anterior para a lixeira do Drive...")
            if not dry_run:
                try:
                    drive.files().update(fileId=arq_alvo['id'], body={'trashed': True}).execute()
                except Exception:
                    try:
                        drive.files().update(fileId=arq_alvo['id'], removeParents=id_dest).execute()
                    except Exception:
                        pass
                drive_idx.remover_arquivo(arq_alvo['id'])
                drive.files().update(
                    fileId=arq['id'],
                    addParents=id_dest,
                    removeParents=ID_PASTA_RAIZ_DRIVE,
                    body={'name': info['nome_sugerido']}
                ).execute()
                drive_idx.mover_arquivo(arq['id'], id_dest, info['nome_sugerido'])
                movidos += 1
            relatorio_triagem.append({
                'status': 'SUBSTITUICAO',
                'nome_original': arq['name'],
                'nome_sugerido': info['nome_sugerido'],
                'pasta_mes_drive': caminho_dest,
                'aviso': f"Substituiu a versão anterior '{arq_alvo['name']}' ({msg_acao})."
            })
            continue

        elif tipo_acao == 'MANTER_EXISTENTE':
            print(f"   ⏩ [JÁ DOCUMENTADO] Versão em {caminho_dest} ('{arq_alvo['name']}') é mais recente que {arq['name']}.")
            print(f"      🗑️  Descartando arquivo mais antigo da raiz...")
            if not dry_run:
                try:
                    drive.files().update(fileId=arq['id'], body={'trashed': True}).execute()
                except Exception:
                    try:
                        drive.files().update(fileId=arq['id'], removeParents=ID_PASTA_RAIZ_DRIVE).execute()
                    except Exception:
                        pass
                drive_idx.remover_arquivo(arq['id'])
            continue

        icone = {'COMPLETO': '🟢', 'PENDENTE_RUBRICA': '🟡', 'PENDENTE_VALOR': '🟡',
                 'PENDENTE_VALOR_E_RUBRICA': '🟠', 'PENDENTE_DATA': '🔴'}.get(info['status'], '⚪')

        print(f"   {icone} {arq['name']} -> {info['nome_sugerido']}")
        print(f"      📅 {info['data']} | R$ {info['valor']:.2f} | Status: {info['status']}")
        print(f"      ➡️  Destino: {caminho_dest}")
        if info['aviso']:
            print(f"      ⚠️  Atenção: {info['aviso']}")

        if not dry_run:
            body_upd = {'name': info['nome_sugerido']}
            media_upd = None
            if info.get('dados_processados'):
                mt_up = 'image/png' if info['nome_sugerido'].lower().endswith('.png') else 'image/jpeg'
                media_upd = MediaIoBaseUpload(io.BytesIO(info['dados_processados']), mimetype=mt_up, resumable=True)
                body_upd['appProperties'] = {'tarjas_reforcadas': 'sim'}
            f_upd = drive.files().update(
                fileId=arq['id'],
                addParents=id_dest,
                removeParents=ID_PASTA_RAIZ_DRIVE,
                body=body_upd,
                media_body=media_upd,
                fields='id, name, parents, md5Checksum, modifiedTime, appProperties, webViewLink'
            ).execute()
            drive_idx.mover_arquivo(arq['id'], id_dest, info['nome_sugerido'])
            arq.update(f_upd)
            movidos += 1

        relatorio_triagem.append(info)

    # Também verifica e processa eventuais faturas PicPay já dentro das pastas que ainda não tenham valor ou tarjas reforçadas
    mov_pic, tri_pic = processar_picpay_nas_pastas_drive(drive, drive_idx, dry_run=dry_run)
    movidos += mov_pic
    relatorio_triagem.extend(tri_pic)

    return movidos, relatorio_triagem


def processar_picpay_nas_pastas_drive(drive, drive_idx, dry_run=False):
    """Localiza faturas PicPay dentro das pastas do Drive que ainda não foram renomeadas com o valor
    ou que estejam em pasta diferente de 'Outros (Geral) 01', renomeia com a soma exata das despesas
    não tarjadas e garante que fiquem em 'Bloco II - Gerais / Outros (Geral) 01' do mês da fatura
    (mantendo a imagem original inalterada).
    """
    processados = 0
    triagem = []
    candidatos = []
    for f in list(drive_idx.by_id.values()):
        if f.get('mimeType') == comum.MIME_PASTA:
            continue
        nome_f = f.get('name', '')
        nome_low = nome_f.lower()
        if RE_CONSOLIDADO.match(nome_f):
            continue
        is_img = f.get('mimeType', '').startswith('image/') or nome_low.endswith(('.jpg', '.jpeg', '.png'))
        if not is_img:
            continue
        tem_valor_no_nome = bool(re.search(r'(?<![\d.,])\d+[.,]\d{2}(?![\d])', nome_f)) and not nome_f.startswith('[SEM_VALOR]')
        pais = f.get('parents', [])
        nome_pasta_pai = drive_idx.by_id.get(pais[0], {}).get('name', '') if pais else ''
        pasta_errada = normalizar(nome_pasta_pai) != normalizar('Outros (Geral) 01')
        if ('picpay' in nome_low and (not tem_valor_no_nome or pasta_errada)) or (
            normalizar(nome_pasta_pai) == normalizar('Outros (Geral) 01') and not tem_valor_no_nome
        ):
            candidatos.append(f)

    for arq in candidatos:
        try:
            buf = io.BytesIO()
            dl = MediaIoBaseDownload(buf, drive.files().get_media(fileId=arq['id']))
            done = False
            while not done:
                _, done = dl.next_chunk()
            buf.seek(0)
            dados_bytes = buf.getvalue()

            info = analisar_conteudo(dados_bytes, arq['name'])
            if not info.get('eh_picpay') or info.get('valor', 0) <= 0:
                continue

            res = resolver_pasta_destino(drive, drive_idx, info, dry_run=dry_run)
            if not res:
                continue
            id_dest, caminho_dest = res
            pais_atuais = arq.get('parents', [])
            pai_atual = pais_atuais[0] if pais_atuais else None

            if arq['name'] == info['nome_sugerido'] and pai_atual == id_dest:
                continue

            print(f"\n🟢 [PICPAY DETECTADO] {arq['name']} -> {info['nome_sugerido']}")
            print(f"   📅 Mês: {info['mes_contabil']} | Soma não tarjadas: R$ {info['valor']:.2f} ({len(info.get('itens_picpay', []))} itens)")
            print(f"   📁 Pasta: {caminho_dest}")

            if not dry_run:
                body_upd = {'name': info['nome_sugerido']}
                kwargs_upd = {
                    'fileId': arq['id'],
                    'body': body_upd,
                    'fields': 'id, name, mimeType, parents, md5Checksum, modifiedTime, appProperties, webViewLink'
                }
                if pai_atual and pai_atual != id_dest:
                    kwargs_upd['addParents'] = id_dest
                    kwargs_upd['removeParents'] = pai_atual
                f_atualizado = drive.files().update(**kwargs_upd).execute()
                drive_idx.mover_arquivo(arq['id'], id_dest, info['nome_sugerido'])
                arq.update(f_atualizado)
                processados += 1
            triagem.append(info)
        except Exception as e_pic:
            print(f"   ⚠️  Erro ao processar fatura PicPay '{arq.get('name')}': {e_pic}")

    return processados, triagem


def enviar_arquivo_local_ao_drive(caminho, drive, drive_idx, dry_run=False):
    nome = os.path.basename(caminho)
    with open(caminho, 'rb') as f:
        dados = f.read()

    info = analisar_conteudo(dados, nome)
    dados_upload = info.get('dados_processados') or dados
    if info.get('dados_processados') and not dry_run:
        try:
            with open(caminho, 'wb') as f_out:
                f_out.write(dados_upload)
        except Exception:
            pass

    res = resolver_pasta_destino(drive, drive_idx, info, dry_run=dry_run)

    if not res:
        print(f"❌ Não foi possível determinar pasta de destino para '{nome}'.")
        return None

    id_dest, caminho_dest = res
    md5_novo = hashlib.md5(dados_upload).hexdigest()

    tipo_acao, arq_alvo, msg_acao = verificar_duplicata_ou_substituicao(
        drive_idx, id_dest, info, md5_novo=md5_novo, drive=drive
    )

    if tipo_acao == 'DUPLICATA_EXATA':
        print(f"   ♊ [DUPLICATA IDÊNTICA] '{nome}' já existe em {caminho_dest} como '{arq_alvo['name']}'. Upload ignorado.")
        return arq_alvo['id']

    elif tipo_acao == 'SUBSTITUIR':
        print(f"   🔄 [SUBSTITUIÇÃO] '{nome}' substitui a versão anterior '{arq_alvo['name']}' em {caminho_dest}.")
        if not dry_run:
            drive.files().update(fileId=arq_alvo['id'], body={'trashed': True}).execute()
            drive_idx.remover_arquivo(arq_alvo['id'])

    elif tipo_acao == 'MANTER_EXISTENTE':
        print(f"   ⏩ [JÁ DOCUMENTADO] Versão em {caminho_dest} ('{arq_alvo['name']}') é mais recente que o arquivo local. Upload ignorado.")
        return arq_alvo['id']

    icone = {'COMPLETO': '🟢', 'PENDENTE_RUBRICA': '🟡', 'PENDENTE_VALOR': '🟡',
             'PENDENTE_VALOR_E_RUBRICA': '🟠', 'PENDENTE_DATA': '🔴'}.get(info['status'], '⚪')

    print(f"\n{icone} Processando: {nome} -> {info['nome_sugerido']}")
    print(f"   📅 {info['data']} | R$ {info['valor']:.2f} | Status: {info['status']}")
    print(f"   📁 Destino: {caminho_dest}")
    if info['aviso']:
        print(f"   ⚠️  Aviso: {info['aviso']}")

    if dry_run:
        print("   [DRY-RUN] Simulação concluída.")
        return "<simulado>"

    nome_sug_low = info['nome_sugerido'].lower()
    if nome_sug_low.endswith('.pdf'):
        mt_upload = 'application/pdf'
    elif nome_sug_low.endswith(('.jpg', '.jpeg')):
        mt_upload = 'image/jpeg'
    else:
        mt_upload = 'image/png'

    body_create = {'name': info['nome_sugerido'], 'parents': [id_dest]}
    if info.get('eh_picpay'):
        body_create['appProperties'] = {'tarjas_reforcadas': 'sim'}

    media = MediaIoBaseUpload(io.BytesIO(dados_upload), mimetype=mt_upload)
    f_criado = drive.files().create(
        body=body_create,
        media_body=media,
        fields='id, name, mimeType, parents, md5Checksum, modifiedTime, appProperties, webViewLink'
    ).execute()
    drive_idx.adicionar_arquivo(f_criado)
    print(f"   🎉 Upload concluído com sucesso!")
    return f_criado['id']



def main():
    comum.configurar_stdout()
    ap = argparse.ArgumentParser(description="Classificador com Degradação Graciosa")
    ap.add_argument('arquivo', nargs='?', help='caminho de arquivo local')
    ap.add_argument('--pasta', help='pasta local com comprovantes')
    ap.add_argument('--enviar-drive', action='store_true', help='upload direto para o Drive')
    ap.add_argument('--organizar-raiz-drive', action='store_true', help='organiza a raiz do Drive')
    ap.add_argument('--oauth', action='store_true', help='abrir navegador para renovar OAuth do usuário')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    gc, drive, tipo = conectar(permitir_login=args.oauth)
    drive_idx = DriveIndex(drive)

    if args.organizar_raiz_drive:
        movidos, triagem = organizar_arquivos_raiz_drive(drive, drive_idx, dry_run=args.dry_run)
        print(f"\nTotal movidos/organizados: {movidos}")
        return

    arquivos = []
    if args.arquivo:
        arquivos.append(args.arquivo)
    elif args.pasta:
        for f in os.listdir(args.pasta):
            p = os.path.join(args.pasta, f)
            if os.path.isfile(p) and not f.startswith(('desktop', 'mai-', 'jun-')):
                arquivos.append(p)

    if not arquivos:
        print("Informe um arquivo local ou execute com --organizar-raiz-drive.")
        return

    for arq in arquivos:
        if args.enviar_drive:
            enviar_arquivo_local_ao_drive(arq, drive, drive_idx, dry_run=args.dry_run)
        else:
            with open(arq, 'rb') as f:
                dados = f.read()
            info = analisar_conteudo(dados, os.path.basename(arq))
            icone = {'COMPLETO': '🟢', 'PENDENTE_RUBRICA': '🟡', 'PENDENTE_VALOR': '🟡',
                     'PENDENTE_VALOR_E_RUBRICA': '🟠', 'PENDENTE_DATA': '🔴'}.get(info['status'], '⚪')
            print(f"\n{icone} {info['nome_original']}  ->  {info['nome_sugerido']}")
            print(f"   📅 {info['data']} | R$ {info['valor']:.2f} | Status: {info['status']}")
            if info['rubrica']:
                print(f"   🏷️  {info['bloco']} / {info['rubrica']} ('{info['motivo']}')")
            if info['aviso']:
                print(f"   ⚠️  Aviso: {info['aviso']}")


if __name__ == '__main__':
    main()
