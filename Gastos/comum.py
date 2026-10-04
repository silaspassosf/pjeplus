"""Infra compartilhada da Prestação de Contas (GASTOS/).

- Autenticação com fallback seguro (OAuth -> Service Account).
- DriveIndex: cache em memória de toda a árvore do Drive em 2 requisições.
- Calendário de meses (Maio/2025 = pasta 01 até Setembro/2026 = pasta 17).
- Estrutura canônica de rubricas (planilha x pastas do Drive).
- garantir_meses(): cria abas e pastas faltantes até um mês-alvo em poucos segundos.
"""
import io
import os
import re
import sys
import unicodedata
from collections import defaultdict

import gspread
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQ_CLIENT_SECRET = os.path.join(BASE_DIR, 'client_secret.json')
ARQ_TOKEN = os.path.join(BASE_DIR, 'token.json')
ARQ_SERVICE_ACCOUNT = os.path.join(BASE_DIR, 'credenciais.json')

ID_PLANILHA = '1UnvAdmOGZi48Ap7BwXEq9aCfRZxJCldbl9r__c0OjY0'
ID_PASTA_RAIZ_DRIVE = '1AkTJwtFYQSH8QFpIDFTsd8w3DbDUL4GD'
ESCOPOS = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

MIME_PASTA = 'application/vnd.google-apps.folder'

MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
         'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
MESES_ABREV = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
INICIO = (2025, 5)          # Maio/2025 -> pasta "01 - Maio 2025"
MES_ALVO_PADRAO = (2026, 9)  # gerar até Setembro/2026

BLOCO_A = 'Bloco A - Individuais'
BLOCO_B = 'Bloco B - Gerais'

RUBRICAS_A = ['Escola', 'Psicoterapia', 'Psicopedagoga', 'Farmácia e Higiene',
              'Plano de Saúde e Odontológico', 'Médicos e Exames',
              'Alimentação rua e Cantina Escolar', 'Vestuário', 'Transporte', 'Lazer',
              'Gastos extras escolares'] + [f'Outros (Individual) {i:02d}' for i in range(1, 6)] + ['', '']
RUBRICAS_B = ['Aluguel', 'Água', 'Luz', 'Gás', 'Internet', 'Streamings',
              'Mercado/Açougue/Padaria', 'Faxina/Limpeza'] + [f'Outros (Geral) {i:02d}' for i in range(1, 6)] + ['', '']
LINHA_INI_A, LINHA_INI_B = 5, 27
VALOR_PADRAO = {'Aluguel': 3500}
PASTA_DRIVE = {'Faxina/Limpeza': 'Faxina-Limpeza'}

# Rubricas onde normalmente existe apenas 1 conta/recibo mensal (substituição automática de versão)
RUBRICAS_CONTA_UNICA = {
    'Aluguel', 'Luz', 'Água', 'Gás', 'Internet',
    'Escola', 'Plano de Saúde e Odontológico', 'Psicopedagoga', 'Psicoterapia'
}

RE_CONSOLIDADO = re.compile(
    r'^(?:[a-z]{3}-\d{2}\s+|(?:Doc\s+[A-Z]+\d*\s*-\s*)?Comprovantes\s+-\s+|Doc\s+[A-Z]+\s*-\s*Prestação\s+de\s+Contas\s+-\s*|Prestação\s+de\s+Contas\s+-\s*|Compilação\s+-\s*).+\.pdf$',
    re.IGNORECASE
)


def numero_para_letras(n):
    """Converte índice numérico em letras sequenciais: 1 -> A, 2 -> B, ..., 26 -> Z, 27 -> AA, etc."""
    resultado = ""
    while n > 0:
        n -= 1
        resultado = chr(ord('A') + (n % 26)) + resultado
        n //= 26
    return resultado


def obter_letra_mes(mes_nome):
    """Retorna a letra sequencial do mês (ex: Maio 2025 -> A, Junho 2025 -> B, ..., Maio 2026 -> M)."""
    partes = mes_nome.strip().split()
    if len(partes) >= 2 and partes[0] in MESES:
        mes_num = MESES.index(partes[0]) + 1
        ano_num = int(partes[1])
        idx = (ano_num - INICIO[0]) * 12 + (mes_num - INICIO[1]) + 1
        if idx >= 1:
            return numero_para_letras(idx)
    return 'A'


def eh_rubrica_conta_unica(rubrica):
    if not rubrica:
        return False
    norm_alvo = normalizar(rubrica)
    return any(normalizar(r) == norm_alvo for r in RUBRICAS_CONTA_UNICA)


def valores_muito_proximos(v1, v2, lim_pct=0.02, lim_abs=1.0):
    try:
        v1, v2 = float(v1), float(v2)
    except (ValueError, TypeError):
        return False
    if v1 <= 0 or v2 <= 0:
        return False
    diff_abs = abs(v1 - v2)
    if diff_abs <= lim_abs:
        return True
    return (diff_abs / max(v1, v2)) <= lim_pct


def configurar_stdout():
    try:
        sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
    except Exception:
        pass


def normalizar(txt):
    txt = unicodedata.normalize('NFKD', str(txt)).encode('ascii', 'ignore').decode()
    txt = re.sub(r'[/\\\-_]+', ' ', txt.lower())
    return re.sub(r'\s+', ' ', txt).strip()


def iterar_meses(ate=MES_ALVO_PADRAO, inicio=INICIO):
    ano, mes, idx = inicio[0], inicio[1], 1
    while (ano, mes) <= tuple(ate):
        yield idx, f'{MESES[mes - 1]} {ano}', f'{MESES_ABREV[mes - 1]}-{str(ano)[-2:]}', ano, mes
        idx += 1
        mes += 1
        if mes > 12:
            mes, ano = 1, ano + 1


def nome_pasta_mes(idx, nome_mes):
    return f'{idx:02d} - {nome_mes}'


def gerar_prefixo_mes(nome_mes):
    partes = nome_mes.strip().split(' ')
    if len(partes) >= 2 and partes[0] in MESES:
        return f'{MESES_ABREV[MESES.index(partes[0])]}-{partes[1][-2:]}'
    return 'doc'


def nomes_pastas_bloco(rubricas):
    return [PASTA_DRIVE.get(r, r) for r in rubricas if r]


# ------------------------------------------------------------- autenticação
def _creds_oauth(permitir_login=True):
    creds = None
    if os.path.exists(ARQ_TOKEN):
        try:
            creds = Credentials.from_authorized_user_file(ARQ_TOKEN, ESCOPOS)
        except Exception:
            creds = None
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(ARQ_TOKEN, 'w') as f:
                f.write(creds.to_json())
            return creds
        except Exception:
            pass  # token revogado ou inválido
    if not permitir_login:
        return None
    print('Abrindo navegador para autorização Google (OAuth)...')
    flow = InstalledAppFlow.from_client_secrets_file(ARQ_CLIENT_SECRET, ESCOPOS)
    creds = flow.run_local_server(port=0)
    with open(ARQ_TOKEN, 'w') as f:
        f.write(creds.to_json())
    return creds


def conectar(permitir_login=False):
    creds = _creds_oauth(permitir_login=permitir_login)
    tipo = 'oauth'
    if creds is None:
        creds = service_account.Credentials.from_service_account_file(ARQ_SERVICE_ACCOUNT, scopes=ESCOPOS)
        tipo = 'service_account'
    return gspread.authorize(creds), build('drive', 'v3', credentials=creds), tipo


# ----------------------------------------------------------- drive indexador
class DriveIndex:
    """Índice em memória de todo o Drive em 1-2 requisições paginadas."""
    def __init__(self, drive):
        self.drive = drive
        self.by_id = {}
        self.by_parent = defaultdict(list)
        self.recarregar()

    def recarregar(self):
        self.by_id.clear()
        self.by_parent.clear()
        try:
            raiz = self.drive.files().get(fileId=ID_PASTA_RAIZ_DRIVE, fields="id, name, mimeType").execute()
            self.by_id[raiz['id']] = raiz
        except Exception:
            pass

        # Varre estritamente a árvore do GASTOS em lotes (BFS)
        pais_para_buscar = [ID_PASTA_RAIZ_DRIVE]
        while pais_para_buscar:
            lote = pais_para_buscar[:20]
            pais_para_buscar = pais_para_buscar[20:]
            q_pais = " or ".join(f"'{p}' in parents" for p in lote)
            query = f"trashed=false and ({q_pais})"
            tok = None
            while True:
                r = self.drive.files().list(
                    q=query,
                    pageSize=1000,
                    pageToken=tok,
                    fields="nextPageToken, files(id, name, mimeType, parents, md5Checksum, modifiedTime, appProperties, webViewLink, size)"
                ).execute()
                for f in r.get('files', []):
                    self.by_id[f['id']] = f
                    for p in f.get('parents', []):
                        self.by_parent[p].append(f)
                    if f['mimeType'] == MIME_PASTA:
                        pais_para_buscar.append(f['id'])
                tok = r.get('nextPageToken')
                if not tok:
                    break

    def listar_filhos(self, id_pai, apenas_pastas=None):
        filhos = self.by_parent.get(id_pai, [])
        if apenas_pastas is True:
            return [f for f in filhos if f['mimeType'] == MIME_PASTA]
        elif apenas_pastas is False:
            return [f for f in filhos if f['mimeType'] != MIME_PASTA]
        return list(filhos)

    def obter_ou_criar_pasta(self, nome, id_pai, dry_run=False):
        for f in self.listar_filhos(id_pai, apenas_pastas=True):
            if f['name'] == nome:
                return f['id'], False
        if dry_run:
            return f'<nova:{nome}>', True
        meta = {'name': nome, 'mimeType': MIME_PASTA, 'parents': [id_pai]}
        f = self.drive.files().create(body=meta, fields='id, name, mimeType, parents').execute()
        f['parents'] = [id_pai]
        self.by_id[f['id']] = f
        self.by_parent[id_pai].append(f)
        return f['id'], True

    def pasta_do_mes(self, nome_mes):
        for f in self.listar_filhos(ID_PASTA_RAIZ_DRIVE, apenas_pastas=True):
            if f['name'].endswith(nome_mes):
                return f['id']
        return None

    def remover_arquivo(self, id_arquivo):
        f = self.by_id.pop(id_arquivo, None)
        if f:
            for p in f.get('parents', []):
                if p in self.by_parent and f in self.by_parent[p]:
                    try:
                        self.by_parent[p].remove(f)
                    except ValueError:
                        pass

    def mover_arquivo(self, id_arquivo, novo_pai, novo_nome=None):
        f = self.by_id.get(id_arquivo)
        if f:
            for p in list(f.get('parents', [])):
                if p in self.by_parent and f in self.by_parent[p]:
                    try:
                        self.by_parent[p].remove(f)
                    except ValueError:
                        pass
            f['parents'] = [novo_pai]
            if novo_nome:
                f['name'] = novo_nome
            self.by_parent[novo_pai].append(f)

    def adicionar_arquivo(self, f):
        self.by_id[f['id']] = f
        for p in f.get('parents', []):
            self.by_parent[p].append(f)

    def buscar_por_md5(self, md5, id_pasta=None):
        if not md5:
            return None
        candidatos = self.listar_filhos(id_pasta, apenas_pastas=False) if id_pasta else self.by_id.values()
        for f in candidatos:
            if f.get('mimeType') != MIME_PASTA and f.get('md5Checksum') == md5:
                return f
        return None



# ------------------------------------------------------------------- sheets
def _formula_individual(linha, bloco):
    return f'=IF(C{linha}="";"";C{linha})' if bloco == 'A' else f'=IF(C{linha}="";"";C{linha}/3)'


def _linhas_bloco(rubricas, linha_ini, bloco):
    vals = []
    for i, rub in enumerate(rubricas):
        ln = linha_ini + i
        vals.append([rub, VALOR_PADRAO.get(rub, ''), _formula_individual(ln, bloco), '', 'Pendente', ''])
    return vals


def resetar_aba(aba, nome_mes):
    fim_a = LINHA_INI_A + len(RUBRICAS_A) - 1
    fim_b = LINHA_INI_B + len(RUBRICAS_B) - 1
    aba.batch_update([
        {'range': 'A1', 'values': [[f'Prestação de Contas — {nome_mes}']]},
        {'range': f'B{LINHA_INI_A}:G{fim_a}', 'values': _linhas_bloco(RUBRICAS_A, LINHA_INI_A, 'A')},
        {'range': f'B{LINHA_INI_B}:G{fim_b}', 'values': _linhas_bloco(RUBRICAS_B, LINHA_INI_B, 'B')},
    ], value_input_option='USER_ENTERED')


def corrigir_rotulos_outros(aba, dry_run=False):
    col_b = aba.col_values(2)
    updates, cont = [], {'Outros (Geral)': 0, 'Outros (Individual)': 0}
    for i, v in enumerate(col_b, 1):
        v = v.strip()
        for base in cont:
            if v == base or re.fullmatch(re.escape(base) + r' \d{2}', v):
                cont[base] += 1
                novo = f'{base} {cont[base]:02d}' if cont[base] <= 5 else ''
                if novo != v:
                    updates.append({'range': f'B{i}', 'values': [[novo]]})
    if updates and not dry_run:
        aba.batch_update(updates, value_input_option='USER_ENTERED')
    return len(updates)


# --------------------------------------------------------- garantir meses
def garantir_meses(sheets_client, drive_idx, ate=MES_ALVO_PADRAO, dry_run=False):
    tag = '[DRY-RUN] ' if dry_run else ''
    planilha = sheets_client.open_by_key(ID_PLANILHA)
    abas = planilha.worksheets()
    titulos = {a.title.strip(): a for a in abas}

    pastas_raiz = {f['name']: f['id'] for f in drive_idx.listar_filhos(ID_PASTA_RAIZ_DRIVE, apenas_pastas=True)}

    for idx, nome_mes, _prefixo, _ano, _mes in iterar_meses(ate):
        # 1. Planilha
        if nome_mes not in titulos:
            modelo = planilha.worksheets()[-1]
            print(f'{tag}🆕 Criando aba "{nome_mes}" na planilha (modelo: {modelo.title})...')
            if not dry_run:
                nova = planilha.duplicate_sheet(modelo.id, insert_sheet_index=len(planilha.worksheets()),
                                                new_sheet_name=nome_mes)
                resetar_aba(nova, nome_mes)
                titulos[nome_mes] = nova
        else:
            n = corrigir_rotulos_outros(titulos[nome_mes], dry_run=dry_run)
            if n:
                print(f'{tag}🏷️  Aba "{nome_mes}": {n} rótulo(s) "Outros" numerados')

        # 2. Drive
        nome_pasta = nome_pasta_mes(idx, nome_mes)
        id_mes = pastas_raiz.get(nome_pasta) or next(
            (v for k, v in pastas_raiz.items() if k.endswith(nome_mes)), None)
        criadas = 0
        if not id_mes:
            id_mes, nova = drive_idx.obter_ou_criar_pasta(nome_pasta, ID_PASTA_RAIZ_DRIVE, dry_run=dry_run)
            pastas_raiz[nome_pasta] = id_mes
            criadas += nova

        for bloco, rubricas in ((BLOCO_A, RUBRICAS_A), (BLOCO_B, RUBRICAS_B)):
            if id_mes.startswith('<nova:'):
                criadas += 1 + len(nomes_pastas_bloco(rubricas))
                continue
            id_bloco, nova = drive_idx.obter_ou_criar_pasta(bloco, id_mes, dry_run=dry_run)
            criadas += nova
            if id_bloco.startswith('<nova:'):
                criadas += len(nomes_pastas_bloco(rubricas))
                continue
            existentes = {f['name'] for f in drive_idx.listar_filhos(id_bloco, apenas_pastas=True)}
            for nome_sub in nomes_pastas_bloco(rubricas):
                if nome_sub not in existentes:
                    drive_idx.obter_ou_criar_pasta(nome_sub, id_bloco, dry_run=dry_run)
                    criadas += 1
        if criadas:
            print(f'{tag}📁 Drive "{nome_pasta}": {criadas} pasta(s) criada(s)')
    print(f'{tag}✅ Meses garantidos até {MESES[ate[1] - 1]} {ate[0]}.')
