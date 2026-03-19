"""
Teste SIMPLES: extrai HTML real → aplica regras do pet2.py → mostra log
"""
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

# Importa DIRETAMENTE do pet2.py
sys.path.insert(0, str(Path(__file__).parent))
from pet2 import definir_regras, verifica_peticao_contra_hipotese, PeticaoLinha


def extrair_peticoes_html(html_content: str):
    """Extrai petições do HTML real."""
    soup = BeautifulSoup(html_content, 'html.parser')
    linhas = soup.find_all('tr', class_='cdk-drag')
    
    peticoes = []
    for linha in linhas:
        cells = linha.find_all('td')
        if len(cells) < 7:
            continue
        
        # Extrai dados
        numero_processo = cells[1].get_text(strip=True)
        data_juntada = cells[3].get_text(strip=True)
        tipo_peticao = cells[4].get_text(strip=True)
        descricao = cells[5].get_text(strip=True)
        tarefa_fase = cells[6].get_text(strip=True)
        
        # Separa tarefa e fase
        partes = tarefa_fase.split('\n')
        tarefa = partes[0].strip() if len(partes) > 0 else ""
        fase = partes[1].strip() if len(partes) > 1 else ""
        
        # Verifica se é perito
        eh_perito = bool(linha.find('mat-icon', string=lambda t: t and 'gavel' in t))
        
        # Extrai polo
        polo = "ativo"  # padrão
        polo_icons = linha.find_all('mat-icon')
        for icon in polo_icons:
            if 'arrow_downward' in (icon.get_text(strip=True) or ""):
                polo = "passivo"
                break
        
        # Cria objeto
        peticao = PeticaoLinha(
            numero_processo=numero_processo,
            data_juntada="",
            tipo_peticao=tipo_peticao,
            descricao=descricao,
            tarefa=tarefa,
            fase=fase,
            eh_perito=eh_perito,
            data_audiencia=None,
            polo=polo
        )
        peticoes.append(peticao)
    
    return peticoes


def testar_peticao(peticao: PeticaoLinha, regras_dict: dict):
    """Testa petição contra TODAS as regras do pet2.py."""
    
    # Ordem de processamento (do pet2.py)
    ordem_blocos = ['pericias', 'recurso', 'diretos', 'gigs', 'analise', 'apagar']
    
    for bloco_nome in ordem_blocos:
        regras = regras_dict.get(bloco_nome, [])
        
        for nome_regra, padroes, acao in regras:
            # Verifica se a petição bate com os padrões
            if verifica_peticao_contra_hipotese(peticao, padroes):
                # Extrai nome da ação
                acao_str = "None"
                if acao is not None:
                    if callable(acao):
                        acao_str = getattr(acao, '__name__', str(acao))
                    elif isinstance(acao, tuple):
                        # Tupla de ações
                        acao_str = " + ".join([getattr(a, '__name__', str(a)) for a in acao if a is not None])
                    else:
                        acao_str = str(acao)
                
                return bloco_nome, nome_regra, acao_str
    
    return None, None, None


def main():
    # Carrega HTML
    doc_path = Path(__file__).parent.parent / 'doc.txt'
    html_content = doc_path.read_text(encoding='utf-8')
    
    # Extrai petições
    peticoes = extrair_peticoes_html(html_content)
    
    # Carrega regras do pet2.py
    regras = definir_regras()
    
    print("=" * 100)
    print("LOG: NÚMERO - REGRA - AÇÃO")
    print("=" * 100)
    
    # Testa cada petição
    for peticao in peticoes:
        bloco, regra, acao = testar_peticao(peticao, regras)
        
        if regra:
            print(f"{peticao.numero_processo} | {regra} ({bloco}) | {acao}")
        else:
            print(f"{peticao.numero_processo} | SEM REGRA | -")
    
    print("=" * 100)
    print(f"Total: {len(peticoes)} petições processadas")
    print("=" * 100)


if __name__ == "__main__":
    main()
