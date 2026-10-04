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
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from PIL import Image

import comum
from comum import (BLOCO_A, BLOCO_B, ID_PASTA_RAIZ_DRIVE, MESES, DriveIndex,
                   conectar, normalizar)

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
        'keywords': ['cooeduba', 'cooperativa educacional de ubatuba', 'pjbank pagamentos', 'mensalidade escola ollie'],
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
        'keywords': ['fernanda xavier de paiva borges', 'psicopedagoga', 'psicopedagogia'],
        'valores_tipicos': [300.00],
    },
    {
        'rubrica': 'Psicoterapia',
        'bloco': BLOCO_A,
        'sufixo': '',
        'keywords': ['psicoterapia', 'psicologa', 'terapia ollie'],
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
                    pix = pag.get_pixmap(dpi=300)
                    img = Image.open(io.BytesIO(pix.tobytes('png')))
                    partes.append(pytesseract.image_to_string(img, lang='por+eng', config='--psm 6'))
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
    texto_str = str(texto)

    # 1. Caso iFood / Pedido com "Data do pedido"
    m = re.search(r'Data\s+do\s+pedid[oa]\s*[:\s]*[\r\n\s]*(\d{2})[/.-](\d{2})[/.-](20\d{2})', texto_str, re.IGNORECASE)
    if m:
        dia, mes, ano = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mes <= 12 and 1 <= dia <= 31:
            return datetime(ano, mes, dia)

    # 2. Caso Conta do Mês / Mês de Referência (Luz Elektro / Neoenergia, Sabesp, etc.)
    meses_map_pt = {
        'janeiro': 1, 'fevereiro': 2, 'março': 3, 'marco': 3, 'abril': 4, 'maio': 5,
        'junho': 6, 'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
    }
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
    m = re.search(r'(?<![\d.,])(\d+)[.,](\d{2})(?![\d])', alvo_nome)
    if m:
        return float(f"{m.group(1)}.{m.group(2)}")
    return 0.0


def classificar_despesa(texto, valor=0.0, nome_arquivo=""):
    texto_norm = normalizar(texto) + " " + normalizar(nome_arquivo)

    for regra in REGRAS_DESPESA:
        for kw in regra['keywords']:
            if normalizar(kw) in texto_norm:
                return regra['rubrica'], regra['bloco'], regra.get('sufixo', ''), kw

        if valor in regra.get('valores_tipicos', []):
            return regra['rubrica'], regra['bloco'], regra.get('sufixo', ''), f"valor {valor:.2f}"

    return None, None, "", "não identificada"


def analisar_conteudo(dados_bytes, nome_original):
    """Analisa comprovante e aplica a matriz de decisão com degradação graciosa."""
    nome_base, ext = os.path.splitext(nome_original)
    if not ext:
        ext = '.pdf' if dados_bytes[:4] == b'%PDF' else '.png'

    nome_low = nome_original.lower()

    # 1. 99Receipt: já contém data e valor no nome do arquivo
    if '99receipt' in nome_low or '99 receipt' in nome_low:
        data = extrair_data(nome_original)
        valor = extrair_valor("", nome_original)
        rubrica, bloco, sufixo_regra, motivo = 'Transporte', BLOCO_A, 'OLLIE TRANSPORTE', '99receipt nome'
        texto = ""
    else:
        texto = extrair_texto_de_bytes(dados_bytes, nome_original)
        data = extrair_data(texto) or extrair_data(nome_original)
        valor = extrair_valor(texto, nome_original)
        rubrica, bloco, sufixo_regra, motivo = classificar_despesa(texto, valor, nome_original)

    data_ok = bool(data)
    valor_ok = bool(valor > 0) or (valor == 0.0 and ('0,00' in str(texto) or 'r$ 0,00' in str(texto).lower() or 'r$0,00' in str(texto).lower()))
    rubrica_ok = bool(rubrica is not None)

    # Identificação de Mês
    if data_ok:
        nome_mes = f"{MESES[data.month - 1]} {data.year}"
        diff_meses = (data.year - 2025) * 12 + (data.month - 5) + 1
        if diff_meses >= 1:
            pasta_mes = f"{diff_meses:02d} - {nome_mes}"
        else:
            pasta_mes = f"[FORA_DO_PERIODO] {nome_mes}"
    else:
        nome_mes, pasta_mes = None, None

    nome_limpo = higienizar_fragmento(nome_base)

    # --- MATRIZ DE DEGRAÇÃO GRACIOSA ---
    if data_ok and valor_ok and rubrica_ok:
        status = 'COMPLETO'
        det = f" {sufixo_regra}" if sufixo_regra else ""
        is_ifood = (
            'ifood' in motivo or 'ifood' in nome_low or
            (texto and any(w in texto.lower() for w in ['ifood', 'cardapio', 'previsao de entrega', 'pago pelo app', 'data do pedido']))
        )
        if 'tenda' in motivo or 'tenda' in nome_low:
            det = " tenda"
        elif is_ifood and rubrica == 'Mercado/Açougue/Padaria':
            det = " ifood"
        elif rubrica == 'Internet':
            det = " vivo fibra"
        elif rubrica == 'Aluguel':
            det = ""
        elif rubrica == 'Transporte':
            det = " OLLIE TRANSPORTE"
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
    }


def resolver_pasta_destino(drive, drive_idx, info, dry_run=False):
    """Encontra ou cria a pasta exata no Drive de acordo com o destino_tipo."""
    dt = info['destino_tipo']

    # 1. Rubrica normal: {pasta_mes}/{bloco}/{rubrica}/
    if dt == 'rubrica':
        id_mes = drive_idx.pasta_do_mes(info['mes_contabil'])
        if not id_mes:
            nome_quar = "[REVISAR_FORA_DO_PERIODO]"
            id_quar, _ = drive_idx.obter_ou_criar_pasta(nome_quar, ID_PASTA_RAIZ_DRIVE, dry_run=dry_run)
            return id_quar, f"{nome_quar}/"
        blocos = [f for f in drive_idx.listar_filhos(id_mes, apenas_pastas=True) if f['name'] == info['bloco']]
        if not blocos:
            return None
        alvo = normalizar(info['pasta_drive_rubrica'])
        for r in drive_idx.listar_filhos(blocos[0]['id'], apenas_pastas=True):
            if normalizar(r['name']) == alvo:
                return r['id'], f"{info['pasta_mes_drive']} / {info['bloco']} / {info['pasta_drive_rubrica']}/"
        return None

    # 2. Pasta de revisão dentro do mês: {pasta_mes}/[REVISAR_RUBRICA]/
    elif dt == 'revisar_mes':
        id_mes = drive_idx.pasta_do_mes(info['mes_contabil'])
        if not id_mes:
            nome_quar = "[REVISAR_FORA_DO_PERIODO]"
            id_quar, _ = drive_idx.obter_ou_criar_pasta(nome_quar, ID_PASTA_RAIZ_DRIVE, dry_run=dry_run)
            return id_quar, f"{nome_quar}/"
        nome_pasta_rev = "[REVISAR_RUBRICA]"
        id_rev, _ = drive_idx.obter_ou_criar_pasta(nome_pasta_rev, id_mes, dry_run=dry_run)
        return id_rev, f"{info['pasta_mes_drive']} / {nome_pasta_rev}/"

    # 3. Quarentena na raiz do Drive: [REVISAR_SEM_DATA]/
    elif dt == 'quarentena_raiz':
        nome_quar = "[REVISAR_SEM_DATA]"
        id_quar, _ = drive_idx.obter_ou_criar_pasta(nome_quar, ID_PASTA_RAIZ_DRIVE, dry_run=dry_run)
        return id_quar, f"{nome_quar}/"

    return None


RE_CONSOLIDADO = comum.RE_CONSOLIDADO


def verificar_duplicata_ou_substituicao(drive_idx, id_destino, info, md5_novo=None, timestamp_novo=None):
    """Verifica se o novo arquivo:
    1. É duplicata idêntica (mesmo MD5) de algum arquivo existente.
    2. Substitui uma versão anterior existente (mesmo mês, mesma rubrica e valor muito próximo/conta única).
    Retorna: (tipo_resultado, arquivo_alvo, mensagem)
    onde tipo_resultado pode ser:
      - 'DUPLICATA_EXATA'
      - 'SUBSTITUIR'
      - 'MANTER_EXISTENTE'
      - 'NOVO'
    """
    if not id_destino:
        return 'NOVO', None, None

    candidatos = [
        f for f in drive_idx.listar_filhos(id_destino, apenas_pastas=False)
        if not RE_CONSOLIDADO.match(f['name'])
    ]

    # 1. Checagem de Duplicata Idêntica (MD5)
    if md5_novo:
        for f in candidatos:
            if f.get('md5Checksum') == md5_novo:
                return 'DUPLICATA_EXATA', f, f"Arquivo idêntico (mesmo MD5={md5_novo[:8]}) já existe como '{f['name']}'."

    # 2. Checagem de Substituição de Versão ("valor muito próximo, mês e tipo semelhantes")
    # Regra: preferir o último subido, substituir
    rubrica = info.get('rubrica')
    valor_novo = info.get('valor', 0.0)
    data_novo = info.get('data_dt')
    time_novo = timestamp_novo or datetime.now().isoformat()

    # Caso A: Rubrica de Conta Única (Luz, Água, Aluguel, Internet, Escola, etc.)
    if rubrica and comum.eh_rubrica_conta_unica(rubrica):
        if candidatos:
            existente = sorted(candidatos, key=lambda x: x.get('modifiedTime', ''), reverse=True)[0]
            time_existente = existente.get('modifiedTime', '')
            if time_novo >= time_existente:
                return 'SUBSTITUIR', existente, f"Rubrica de conta única '{rubrica}': versão mais recente substitui '{existente['name']}'."
            else:
                return 'MANTER_EXISTENTE', existente, f"Versão existente '{existente['name']}' já é mais recente."

    # Caso B: Rubricas multi-itens (Mercado, Faxina, Farmácia, Transporte, Cantina, etc.)
    if valor_novo > 0:
        for f in candidatos:
            val_existente = extrair_valor(f['name'])
            if val_existente > 0 and comum.valores_muito_proximos(valor_novo, val_existente):
                data_existente = extrair_data(f['name'])
                match_data = False
                if data_novo and data_existente:
                    match_data = (data_novo.date() == data_existente.date())
                elif not data_existente and abs(valor_novo - val_existente) < 0.01:
                    match_data = True

                if match_data:
                    time_existente = f.get('modifiedTime', '')
                    if time_novo >= time_existente:
                        return 'SUBSTITUIR', f, f"Despesa correspondente (R$ {valor_novo:.2f}): versão mais recente substitui '{f['name']}'."
                    else:
                        return 'MANTER_EXISTENTE', f, f"Versão existente '{f['name']}' é mais recente."

    return 'NOVO', None, None


def organizar_arquivos_raiz_drive(drive, drive_idx, dry_run=False):
    """Varre a raiz do Drive, aplica degradação graciosa e organiza comprovantes pendentes."""
    filhos_raiz = drive_idx.listar_filhos(ID_PASTA_RAIZ_DRIVE, apenas_pastas=False)

    comprovantes_soltos = [
        f for f in filhos_raiz
        if f.get('mimeType') in ('application/pdf', 'image/png', 'image/jpeg')
        or f['name'].lower().endswith(('.pdf', '.png', '.jpg', '.jpeg'))
    ]

    if not comprovantes_soltos:
        return 0, []

    print(f"\n🔍 Organizando {len(comprovantes_soltos)} comprovante(s) pendente(s) na raiz do Drive...")
    movidos, relatorio_triagem = 0, []

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

        if not res:
            print(f"   ⚠️  [{arq['name']}]: Não foi possível determinar pasta de destino.")
            continue

        id_dest, caminho_dest = res
        md5_novo = arq.get('md5Checksum') or hashlib.md5(dados_bytes).hexdigest()
        time_novo = arq.get('modifiedTime', '')

        tipo_acao, arq_alvo, msg_acao = verificar_duplicata_ou_substituicao(
            drive_idx, id_dest, info, md5_novo=md5_novo, timestamp_novo=time_novo
        )

        if tipo_acao == 'DUPLICATA_EXATA':
            print(f"   ♊ [DUPLICATA IDÊNTICA] {arq['name']} -> já existe como '{arq_alvo['name']}' em {caminho_dest}")
            print(f"      🗑️  Descartando arquivo duplicado da raiz...")
            if not dry_run:
                drive.files().update(fileId=arq['id'], body={'trashed': True}).execute()
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
                drive.files().update(fileId=arq_alvo['id'], body={'trashed': True}).execute()
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
                drive.files().update(fileId=arq['id'], body={'trashed': True}).execute()
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
            drive.files().update(
                fileId=arq['id'],
                addParents=id_dest,
                removeParents=ID_PASTA_RAIZ_DRIVE,
                body={'name': info['nome_sugerido']}
            ).execute()
            drive_idx.mover_arquivo(arq['id'], id_dest, info['nome_sugerido'])
            movidos += 1

        relatorio_triagem.append(info)

    return movidos, relatorio_triagem


def enviar_arquivo_local_ao_drive(caminho, drive, drive_idx, dry_run=False):
    nome = os.path.basename(caminho)
    with open(caminho, 'rb') as f:
        dados = f.read()

    info = analisar_conteudo(dados, nome)
    res = resolver_pasta_destino(drive, drive_idx, info, dry_run=dry_run)

    if not res:
        print(f"❌ Não foi possível determinar pasta de destino para '{nome}'.")
        return None

    id_dest, caminho_dest = res
    md5_novo = hashlib.md5(dados).hexdigest()

    tipo_acao, arq_alvo, msg_acao = verificar_duplicata_ou_substituicao(
        drive_idx, id_dest, info, md5_novo=md5_novo
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

    media = MediaIoBaseUpload(io.BytesIO(dados), mimetype='application/pdf' if nome.lower().endswith('.pdf') else 'image/png')
    f_criado = drive.files().create(
        body={'name': info['nome_sugerido'], 'parents': [id_dest]},
        media_body=media,
        fields='id, name, mimeType, parents, md5Checksum, modifiedTime, webViewLink'
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
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    gc, drive, tipo = conectar(permitir_login=False)
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
