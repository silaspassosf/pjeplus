import io
import re
import os
import gspread
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from PyPDF2 import PdfMerger
from PIL import Image

# --- CONFIGURAÇÕES ---
ID_PLANILHA = '1UnvAdmOGZi48Ap7BwXEq9aCfRZxJCldbl9r__c0OjY0'
ID_PASTA_RAIZ_DRIVE = '1AkTJwtFYQSH8QFpIDFTsd8w3DbDUL4GD'

# --- AUTENTICAÇÃO ---
escopos = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_authorized_user_file('token.json', escopos)
sheets_client = gspread.authorize(creds)
drive_service = build('drive', 'v3', credentials=creds)

def extrair_valor_do_nome(nome_arquivo):
    match = re.search(r'(\d+)\.(\d{2})', nome_arquivo)
    return float(match.group(0)) if match else 0.0

def refazer_outros_isolado():
    print("🚀 Iniciando Reparo Cirúrgico: Outros (Individual) 01 - Maio 2026")
    
    # 1. Encontrar o mês de Maio
    query_mes = f"mimeType='application/vnd.google-apps.folder' and name contains 'Maio 2026' and trashed=false and '{ID_PASTA_RAIZ_DRIVE}' in parents"
    id_mes = drive_service.files().list(q=query_mes, fields="files(id)").execute().get('files', [])[0]['id']
    
    # 2. Encontrar o Bloco A
    query_bloco = f"mimeType='application/vnd.google-apps.folder' and name contains 'Bloco A' and trashed=false and '{id_mes}' in parents"
    id_bloco_a = drive_service.files().list(q=query_bloco, fields="files(id)").execute().get('files', [])[0]['id']
    
    # 3. Encontrar a pasta "Outros (Individual) 01"
    nome_pasta_alvo = "Outros (Individual) 01"
    query_pasta = f"mimeType='application/vnd.google-apps.folder' and name='{nome_pasta_alvo}' and trashed=false and '{id_bloco_a}' in parents"
    res_pasta = drive_service.files().list(q=query_pasta, fields="files(id, name)").execute().get('files', [])
    
    if not res_pasta:
        print(f"❌ Pasta '{nome_pasta_alvo}' não encontrada no Drive dentro do Bloco A de Maio!")
        return
        
    id_pasta_alvo = res_pasta[0]['id']
    print(f"✅ Pasta '{nome_pasta_alvo}' encontrada no Drive!")

    # 4. Processar os arquivos
    nome_consolidado = "mai-26 Outros (Individual) 01.pdf"
    query_arquivos = f"mimeType!='application/vnd.google-apps.folder' and trashed=false and '{id_pasta_alvo}' in parents"
    arquivos = drive_service.files().list(q=query_arquivos, fields="files(id, name, mimeType)").execute().get('files', [])
    
    # Apaga o PDF consolidado antigo (se ele estiver lá dentro)
    for arq in arquivos:
        if arq['name'] == nome_consolidado:
            print(f"   🗑️ Apagando PDF antigo corrompido: {arq['name']}")
            drive_service.files().delete(fileId=arq['id']).execute()
            
    # Filtra apenas as fontes
    arquivos_fonte = [f for f in arquivos if f['name'] != nome_consolidado and (f['mimeType'] == 'application/pdf' or f['mimeType'].startswith('image/'))]
    
    if not arquivos_fonte:
        print("🤷‍♂️ Nenhum recibo ou imagem encontrado dentro da pasta para consolidar.")
        return
        
    print(f"📄 Encontrados {len(arquivos_fonte)} arquivo(s) válidos. Iniciando compressão...")
    
    soma_total = 0.0
    merger = PdfMerger()
    
    for arq in arquivos_fonte:
        valor = extrair_valor_do_nome(arq['name'])
        soma_total += valor
        
        request = drive_service.files().get_media(fileId=arq['id'])
        ficheiro_bytes = io.BytesIO()
        downloader = MediaIoBaseDownload(ficheiro_bytes, request)
        done = False
        while not done: _, done = downloader.next_chunk()
        ficheiro_bytes.seek(0)
        
        if arq['mimeType'] == 'application/pdf':
            merger.append(ficheiro_bytes)
        elif arq['mimeType'].startswith('image/'):
            imagem = Image.open(ficheiro_bytes).convert('RGB')
            imagem.thumbnail((1200, 1600), Image.Resampling.LANCZOS)
            pdf_bytes = io.BytesIO()
            imagem.save(pdf_bytes, format='PDF', resolution=72, optimize=True, quality=50)
            pdf_bytes.seek(0)
            merger.append(pdf_bytes)
            
    pdf_final_bytes = io.BytesIO()
    merger.write(pdf_final_bytes)
    pdf_final_bytes.seek(0)
    
    print("☁️ Fazendo upload do novo PDF...")
    media = MediaIoBaseUpload(pdf_final_bytes, mimetype='application/pdf', resumable=True)
    metadata = {'name': nome_consolidado, 'parents': [id_pasta_alvo], 'appProperties': {'hash_estado': 'REPARO_MANUAL'}}
    ficheiro = drive_service.files().create(body=metadata, media_body=media, fields='id, webViewLink').execute()
    drive_service.permissions().create(fileId=ficheiro['id'], body={'type': 'anyone', 'role': 'reader'}).execute()
    
    link_pdf = ficheiro.get('webViewLink', '')
    
    # 5. Atualizar a Planilha
    print("📝 Atualizando a linha na planilha do Google Sheets...")
    planilha = sheets_client.open_by_key(ID_PLANILHA)
    aba = planilha.worksheet('Maio 2026')
    
    dados = aba.get_all_values()
    linha_alvo = None
    
    for i, linha in enumerate(dados):
        col_1 = str(linha[1]).strip() if len(linha) > 1 else ""
        # Procura a linha exata do Outros 01 (garantindo que estamos no Bloco A, mas como o nome é único, basta achar o nome)
        if col_1 == nome_pasta_alvo:
            linha_alvo = i + 1
            break
            
    if linha_alvo:
        str_total = f"{soma_total:.2f}".replace('.', ',')
        # Como é Bloco A (Individual), o gasto total e individualizado são iguais
        aba.update(range_name=f'C{linha_alvo}:D{linha_alvo}', values=[[str_total, str_total]], value_input_option='USER_ENTERED')
        aba.update(range_name=f'G{linha_alvo}', values=[[f'=HYPERLINK("{link_pdf}"; "Link")']], value_input_option='USER_ENTERED')
        print(f"🎉 SUCESSO! Planilha atualizada na linha {linha_alvo} com o valor R$ {str_total} e o novo link.")
    else:
        print(f"⚠️ PDF gerado no Drive, mas a linha '{nome_pasta_alvo}' não foi encontrada na aba 'Maio 2026'.")

if __name__ == '__main__':
    refazer_outros_isolado()