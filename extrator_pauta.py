#!/usr/bin/env python3
"""
Extrator de Pauta do PJe - Aud1 API
Extrai: horário, partes (CNPJ/CPF), tipo
Funciona de qualquer terminal com sessão PJe logada
"""

import requests
import json
import re
from datetime import datetime

# ────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO
# ────────────────────────────────────────────────────────────────────────────
HOST = 'pje.trt2.jus.br'
BASE_URL = f'https://{HOST}/audapi/rest'

# IDs das 15 audiências (capturadas do interceptor)
IDS_AUDIENCIAS = [
    12174224, 12273392, 12350305, 12203321, 12351168, 12276741, 12504763, 
    12278192, 12268971, 12208416, 12205664, 12206010, 12509755, 12406275, 12431351
]

# ────────────────────────────────────────────────────────────────────────────
# UTILITÁRIOS
# ────────────────────────────────────────────────────────────────────────────
def normalizar_cnpj(s):
    if not s:
        return s
    nums = re.sub(r'\D', '', s)
    if len(nums) == 14:
        return re.sub(r'(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})', r'\1.\2.\3/\4-\5', nums)
    return s

def normalizar_cpf(s):
    if not s:
        return s
    nums = re.sub(r'\D', '', s)
    if len(nums) == 11:
        return re.sub(r'(\d{3})(\d{3})(\d{3})(\d{2})', r'\1.\2.\3-\4', nums)
    return s

def normalizar_doc(s):
    if not s:
        return s
    nums = re.sub(r'\D', '', s)
    if len(nums) == 14:
        return normalizar_cnpj(s)
    elif len(nums) == 11:
        return normalizar_cpf(s)
    return s

# ────────────────────────────────────────────────────────────────────────────
# MAIN: Extrair Pauta
# ────────────────────────────────────────────────────────────────────────────
def main():
    # Criar sessão com cookies do navegador
    sess = requests.Session()
    
    # IMPORTANTE: Copiar cookies do navegador
    # Firefox: DevTools → Storage → Cookies → pje.trt2.jus.br
    # Chrome: DevTools → Application → Cookies → pje.trt2.jus.br
    # Cole aqui o conteúdo de um cookie importante (ex: "sso_access_token=...")
    
    print('🔄 Conectando ao PJe...')
    
    # Tentar ler cookies salvos (se existirem)
    try:
        with open('pje_cookies.json', 'r') as f:
            cookies = json.load(f)
            sess.cookies.update(cookies)
            print('✓ Cookies carregados de pje_cookies.json')
    except:
        print('⚠️  Arquivo pje_cookies.json não encontrado')
        print('   Cole os cookies do navegador em pje_cookies.json')
        return
    
    # ────────────────────────────────────────────────────────────────────
    # Carregar audiências
    # ────────────────────────────────────────────────────────────────────
    print(f'\n📊 Carregando {len(IDS_AUDIENCIAS)} audiências...')
    
    audiencias = []
    for id_aud in IDS_AUDIENCIAS:
        try:
            resp = sess.get(f'{BASE_URL}/audiencia/{id_aud}', timeout=5)
            
            if resp.status_code == 200:
                aud = resp.json()
                
                # Extrair dados
                horario = aud.get('hora') or aud.get('horaAudiencia') or ''
                tipo = aud.get('tipo') or aud.get('tipoAudiencia') or ''
                
                # Partes (excluir julgamento)
                partes = []
                for p in aud.get('partes', []):
                    if p.get('tipo', '').upper() not in ['JULGAMENTO']:
                        partes.append({
                            'nome': p.get('nome') or '',
                            'documento': normalizar_doc(p.get('documento') or '')
                        })
                
                audiencias.append({
                    'id': id_aud,
                    'horario': horario,
                    'tipo': tipo,
                    'partes': partes,
                    'data': aud.get('data') or aud.get('dataAudiencia') or ''
                })
                
                print(f'  ✓ ID {id_aud}: {horario} - {tipo}')
            else:
                print(f'  ✗ ID {id_aud}: HTTP {resp.status_code}')
                
        except Exception as e:
            print(f'  ✗ ID {id_aud}: {str(e)}')
    
    # ────────────────────────────────────────────────────────────────────
    # Exibir resultados
    # ────────────────────────────────────────────────────────────────────
    print(f'\n✅ {len(audiencias)} audiências carregadas!\n')
    
    # Formatado
    for aud in audiencias:
        print(f"━ {aud['horario']} | {aud['tipo']}")
        for parte in aud['partes']:
            print(f"   • {parte['nome']} ({parte['documento']})")
    
    # JSON para clipboard
    resultado_json = json.dumps(audiencias, indent=2, ensure_ascii=False)
    
    try:
        import pyperclip
        pyperclip.copy(resultado_json)
        print(f'\n✅ JSON copiado para clipboard ({len(resultado_json)} bytes)')
    except:
        print('\n📋 JSON:')
        print(resultado_json)
        print('\n💾 Salve em pauta_resultado.json se necessário')
    
    # Salvar arquivo
    with open('pauta_resultado.json', 'w', encoding='utf-8') as f:
        json.dump(audiencias, f, indent=2, ensure_ascii=False)
    print('📁 Salvo em: pauta_resultado.json')

if __name__ == '__main__':
    main()
