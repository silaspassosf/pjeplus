import os
import time
import random
import re
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from paginacao_utils import ir_para_proxima_pagina

# Configurações
URL_LOGIN = 'https://www.qconcursos.com/#!/signin-email'
TIMEOUT = 15

os.makedirs('questao', exist_ok=True)
RESULTADO_TXT = os.path.join('questao', 'questoes_extraidas.txt')
RESULTADO_HTML = os.path.join('questao', 'questoes_extraidas.html')

options = webdriver.ChromeOptions()
options.add_argument('--start-maximized')
options.add_experimental_option('excludeSwitches', ['enable-logging'])
try:
    driver = webdriver.Chrome(options=options)
except Exception as e:
    print('[ERRO] Não foi possível iniciar o ChromeDriver. Verifique se o Chrome e o ChromeDriver estão instalados e compatíveis.')
    print(e)
    exit(1)

def esperar_login():
    print('\n[INFO] Faça login normalmente no QConcursos.')
    print('[INFO] Navegue até a página de questões desejada.')
    input('[ENTER] para iniciar a extração...')

def limpar_gabarito_comentario(texto):
    texto = re.sub(r'(gabarito|resposta|alternativa)\s*[:=]?\s*[A-Ea-e](\.|\)|\s|$)', '', texto, flags=re.IGNORECASE)
    linhas = texto.split('\n')
    linhas_limpa = []
    for linha in linhas:
        l = linha.strip()
        if re.fullmatch(r'[A-Ea-e][\.|\)|\s]*', l):
            continue
        if re.fullmatch(r'(letra|alternativa|resp(osta)?)\s*[:=]?\s*[A-Ea-e]', l, re.IGNORECASE):
            continue
        linhas_limpa.append(linha)
    return '\n'.join(linhas_limpa).strip()

def expandir_e_copiar_textos_associados(lista_questoes):
    print('[INFO] Expandindo e copiando textos associados das questões...')
    textos_associados = []
    for idx, questao in enumerate(lista_questoes):
        try:
            # Busca todos os spans com texto exato 'Texto associado'
            spans = questao.find_elements(By.XPATH, ".//span[normalize-space(text())='Texto associado']")
            texto_limpo = ''
            for span in spans:
                try:
                    safe_click(span)
                    # Aguarda até o texto expandido aparecer
                    WebDriverWait(questao, 6).until(
                        lambda q: any(
                            div.is_displayed() and div.get_attribute('innerHTML').strip()
                            for div in q.find_elements(By.CSS_SELECTOR, 'div.q-question-text > div.collapse.in, div.q-question-text > div.collapse[aria-expanded="true"]')
                        )
                    )
                    time.sleep(0.5)  # Pequeno delay extra para garantir renderização
                    div_textos = questao.find_elements(By.CSS_SELECTOR, 'div.q-question-text > div.collapse.in, div.q-question-text > div.collapse[aria-expanded="true"]')
                    for div in div_textos:
                        if div.is_displayed():
                            texto_html = div.get_attribute('innerHTML')
                            t = limpar_html_para_texto(texto_html)
                            if t.strip():
                                texto_limpo = t.strip()
                                break
                    if texto_limpo:
                        break
                except Exception as e:
                    print(f'[WARN] Falha ao expandir/capturar texto associado: {e}')
            textos_associados.append(texto_limpo)
        except Exception as e:
            print(f'[WARN] Falha geral ao buscar texto associado: {e}')
            textos_associados.append('')
    return textos_associados

def limpar_html_para_texto(html):
    if not html:
        return ''
    # Remove tags e converte <br> para quebra de linha
    html = re.sub(r'<br\s*/?>', '\n', html)
    html = re.sub(r'<.*?>', '', html)
    html = re.sub(r'&nbsp;', ' ', html)
    html = re.sub(r'&amp;', '&', html)
    html = re.sub(r'\n+', '\n', html)
    return html.strip()

def responder_e_extrair_questoes():
    questoes_extraidas = []
    gabaritos = []
    print('[INFO] Buscando questões na página...')
    try:
        lista_questoes = driver.find_elements(By.CSS_SELECTOR, 'div.q-questions-list > div')
    except Exception as e:
        print('[ERRO] Falha ao buscar questões:', e)
        return [], []
    if not lista_questoes:
        print('[ERRO] Nenhuma questão encontrada na página. Verifique se você está na tela correta e se as questões estão carregadas.')
        input('[ENTER] para sair...')
        return [], []
    print(f'[INFO] {len(lista_questoes)} questões encontradas.')
    textos_associados = expandir_e_copiar_textos_associados(lista_questoes)
    for idx, questao in enumerate(lista_questoes):
        numero = idx + 1
        alternativas_elements = questao.find_elements(By.CSS_SELECTOR, 'fieldset.form-group div > label.q-radio-button')
        alternativa_escolhida = None
        if alternativas_elements:
            alternativa_escolhida = random.choice(alternativas_elements)
            safe_click(alternativa_escolhida)
        btn_responder = questao.find_elements(By.CSS_SELECTOR, 'button.js-answer-btn.btn.btn-primary')
        if btn_responder:
            safe_click(btn_responder[0])
            time.sleep(random.uniform(1.5, 2.5))
        botoes_comentarios = questao.find_elements(By.CSS_SELECTOR, 'a.q-tab-item[href*="comments-tab"]')
        for btn in botoes_comentarios:
            safe_click(btn)
            time.sleep(random.uniform(0.8, 2.0))
        id_elem = questao.find_elements(By.CSS_SELECTOR, 'div.q-question-header div.q-ref div > a')
        id_questao = id_elem[0].text.strip() if id_elem else ''
        assunto_elem = questao.find_elements(By.CSS_SELECTOR, 'div.q-question-header div.q-question-breadcrumb')
        assunto = assunto_elem[0].text.strip() if assunto_elem else ''
        texto_expandido = textos_associados[idx] if idx < len(textos_associados) else ''
        enunciado_elem = questao.find_elements(By.CSS_SELECTOR, 'div.q-question-enunciation')
        enunciado = enunciado_elem[0].text.strip() if enunciado_elem else ''
        alternativas = []
        letras_alternativas = []
        if alternativas_elements:
            for alt in alternativas_elements:
                letra_elem = alt.find_elements(By.CSS_SELECTOR, 'span.q-option-item')
                letra = letra_elem[0].text.strip() if letra_elem else ''
                texto_elem = alt.find_elements(By.CSS_SELECTOR, 'div.q-item-enum')
                texto = texto_elem[0].text.strip() if texto_elem else ''
                alternativas.append(f"{letra}) {texto}")
                letras_alternativas.append(letra)
        melhor_comentario = ''
        max_curtidas = -1
        comentarios = questao.find_elements(By.CSS_SELECTOR, 'div.q-question-comment')
        for comentario in comentarios:
            texto_coment_elem = comentario.find_elements(By.CSS_SELECTOR, 'div.q-question-comment-body')
            texto_coment = texto_coment_elem[0].text.strip() if texto_coment_elem else ''
            texto_coment = limpar_gabarito_comentario(texto_coment)
            curtidas_elem = comentario.find_elements(By.CSS_SELECTOR, 'span.q-question-comment-likes-count')
            curtidas = int(curtidas_elem[0].text) if curtidas_elem and curtidas_elem[0].text.isdigit() else 0
            if curtidas > max_curtidas:
                max_curtidas = curtidas
                melhor_comentario = texto_coment
        gabarito = ''
        feedback_elem = questao.find_elements(By.CSS_SELECTOR, 'span.q-answer-feedback')
        if feedback_elem:
            fb_txt = feedback_elem[0].text.strip().lower()
            if 'parab' in fb_txt or 'acertou' in fb_txt:
                if alternativa_escolhida:
                    letra_elem = alternativa_escolhida.find_elements(By.CSS_SELECTOR, 'span.q-option-item')
                    gabarito = letra_elem[0].text.strip() if letra_elem else ''
            elif 'resposta:' in fb_txt:
                match = re.search(r'resposta:\s*([A-E])', fb_txt, re.IGNORECASE)
                if match:
                    gabarito = match.group(1).upper()
        gabaritos.append({'numero': numero, 'id': id_questao, 'gabarito': gabarito})
        questoes_extraidas.append({
            'numero': numero,
            'id': id_questao,
            'assunto': assunto,
            'texto_expandido': texto_expandido,
            'enunciado': enunciado,
            'alternativas': alternativas,
            'comentario': melhor_comentario
        })
    return questoes_extraidas, gabaritos

def esperar_elemento(seletor, by=By.CSS_SELECTOR, timeout=TIMEOUT):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, seletor))
    )

def safe_click(elemento):
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elemento)
    time.sleep(0.2)
    elemento.click()
    time.sleep(0.2)

def extrair_varias_paginas(num_paginas=20, salvar_cada=3):
    todas_questoes = []
    todos_gabaritos = []
    pagina_atual = 1
    for i in range(num_paginas):
        print(f'\n[INFO] Extraindo página {pagina_atual} de {num_paginas}...')
        questoes, gabaritos = responder_e_extrair_questoes()
        if not questoes:
            print('[INFO] Nenhuma questão extraída nesta página. Encerrando...')
            break
        todas_questoes.extend(questoes)
        todos_gabaritos.extend(gabaritos)
        if (i+1) % salvar_cada == 0 or (i+1) == num_paginas:
            idx_ini = i+2-salvar_cada if (i+1) >= salvar_cada else 1
            idx_fim = i+1
            nome_txt = f'questao/questoes_pags_{idx_ini:02d}_{idx_fim:02d}.txt'
            nome_html = f'questao/questoes_pags_{idx_ini:02d}_{idx_fim:02d}.html'
            salvar_questoes_txt(todas_questoes, todos_gabaritos, nome_txt)
            salvar_questoes_html(todas_questoes, todos_gabaritos, nome_html)
            print(f'[INFO] Salvo arquivo parcial: páginas {idx_ini}-{idx_fim}')
            todas_questoes = []
            todos_gabaritos = []
        if not ir_para_proxima_pagina(driver):
            print('[INFO] Não foi possível avançar para a próxima página. Encerrando...')
            break
        pagina_atual += 1

def salvar_questoes_txt(questoes, gabaritos, nome_arquivo=None):
    caminho = nome_arquivo if nome_arquivo else RESULTADO_TXT
    with open(caminho, 'w', encoding='utf-8') as f:
        for q in questoes:
            f.write(f"QUESTÃO {q['numero']} (ID: {q['id']})\n")
            f.write(f"ASSUNTO: {q['assunto']}\n")
            if q['texto_expandido']:
                f.write(f"TEXTO ASSOCIADO: {q['texto_expandido']}\n")
            f.write(f"ENUNCIADO: {q['enunciado']}\n")
            f.write('ALTERNATIVAS:\n')
            for alt in q['alternativas']:
                f.write(f"  {alt}\n")
            if q['comentario']:
                for par in q['comentario'].split('\n'):
                    if par.strip():
                        f.write(f"COMENTÁRIO: {par.strip()}\n")
            f.write('\n' + '-'*50 + '\n\n')
        f.write('\nGABARITO FINAL\n')
        f.write('-'*20 + '\n')
        for g in gabaritos:
            f.write(f"Questão {g['numero']} (ID: {g['id']}): {g['gabarito']}\n")
    print(f'[INFO] Questões salvas em {caminho}')

def salvar_questoes_html(questoes, gabaritos, nome_arquivo=None):
    caminho = nome_arquivo if nome_arquivo else RESULTADO_HTML
    html = ['<!DOCTYPE html>', '<html lang="pt-br">', '<head>',
            '<meta charset="utf-8">', '<title>Questões Extraídas</title>',
            '<style>body{font-family:sans-serif;background:#f8f8f8;margin:0;padding:0;} .qpage{background:#fff;max-width:700px;margin:40px auto 40px auto;padding:32px 36px 28px 36px;box-shadow:0 2px 12px #bbb;border-radius:10px;} .qtitle{color:#1a237e;font-size:1.3em;font-weight:bold;} .qassunto{color:#444;font-size:1em;margin-bottom:8px;} .qenun{margin:12px 0 8px 0;font-size:1.07em;} .qalts{margin:10px 0 10px 0;} .qalts li{margin-bottom:4px;} .qcoment{margin-top:18px;color:#b71c1c;font-size:0.98em;font-style:italic;white-space:pre-line;line-height:1.45;} .gabarito-final{margin:36px 0 10px 0; padding:18px 20px; background:#e3f2fd;border-radius:8px;border:1px solid #90caf9;} </style>',
            '</head><body>']
    for q in questoes:
        html.append('<div class="qpage">')
        html.append(f'<div class="qtitle">QUESTÃO {q["numero"]} (ID: {q["id"]})</div>')
        html.append(f'<div class="qassunto">Assunto: {q["assunto"]}</div>')
        if q['texto_expandido']:
            html.append(f'<div class="qenun"><b>Texto Associado:</b> {q["texto_expandido"]}</div>')
        html.append(f'<div class="qenun"><b>Enunciado:</b> {q["enunciado"]}</div>')
        html.append('<ul class="qalts"><b>Alternativas:</b>')
        for alt in q['alternativas']:
            html.append(f'<li>{alt}</li>')
        html.append('</ul>')
        if q['comentario']:
            comentario_html = ''.join([f'<p style="margin:0 0 7px 0;">{par.strip()}</p>' for par in q['comentario'].split('\n') if par.strip()])
            html.append(f'<div class="qcoment"><b>Comentário mais curtido:</b>{comentario_html}</div>')
        html.append('</div>')
    html.append('<div class="gabarito-final"><b>GABARITO FINAL</b><br/><ul>')
    for g in gabaritos:
        html.append(f'<li>Questão {g["numero"]} (ID: {g["id"]}): <b>{g["gabarito"]}</b></li>')
    html.append('</ul></div>')
    html.append('</body></html>')
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html))
    print(f'[INFO] Questões salvas em HTML: {caminho}')

if __name__ == '__main__':
    driver.get(URL_LOGIN)
    esperar_login()
    print('[INFO] Iniciando extração...')
    try:
        extrair_varias_paginas(num_paginas=20, salvar_cada=3)
        print('[INFO] Extração concluída. O navegador permanecerá aberto para conferência.')
        # Teste: tenta mudar de página manualmente após as 20 páginas
        print('[TESTE] Tentando clicar no botão de próxima página após extração...')
        sucesso = ir_para_proxima_pagina(driver)
        if sucesso:
            print('[TESTE] Clique para próxima página realizado com sucesso.')
        else:
            print('[TESTE] Não foi possível clicar no botão de próxima página.')
        input('[ENTER] para sair e fechar o navegador manualmente...')
    except Exception as e:
        print('[ERRO] Ocorreu um erro durante a extração:')
        traceback.print_exc()
        input('[ENTER] para sair...')
    finally:
        driver.quit()
