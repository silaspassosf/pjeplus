"""
aud.py

Fluxo para varrer a lista "Novos Processos" e agrupar em buckets A/B/C
conforme regras do usuário, executando ações apropriadas por bucket.

Uso: importar e chamar run_aud() ou executar diretamente como script.

Observações/assunções:
- Este módulo usa funções de `Fix.utils` para criar driver e fazer login.
- Para criar gigs chamamos `criar_gigs` de `Fix.extracao` passando os parâmetros
  indicados pelo usuário ("-1", "xs marcar aud"). Se a assinatura de
  `criar_gigs` for diferente, pode ser necessário ajustar os argumentos.
- Para `ato_100` verificamos se existe `ato_100` em `atos.py`; se não, apenas logamos.
- Para `pec_ord`/`pec_sum` usamos as wrappers em `atos.py` e, quando aplicável,
  também chamamos `mov_aud` após a notificação (compatível com alteração em `pec.py`).
"""

import time
import json
import traceback
from typing import List, Dict, Any, Optional

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By

# Importar do módulo /Fix (novo)
from Fix.utils import configurar_recovery_driver, handle_exception_with_recovery
from Fix.abas import validar_conexao_driver, trocar_para_nova_aba
from Fix.extracao import abrir_detalhes_processo, criar_gigs, extrair_dados_processo
from Fix.gigs import criar_comentario
from Fix.core import preencher_multiplos_campos, aguardar_e_clicar, aguardar_renderizacao_nativa, esperar_elemento, safe_click, preencher_campo
from Fix.headless_helpers import limpar_overlays_headless
from api.variaveis import PjeApiClient, session_from_driver
from triagem import triagem_peticao

# Importa sistema unificado de progresso
from Fix.progresso_unificado import ProgressoUnificado

# Instância global do sistema de progresso para AUD
progresso_sistema = ProgressoUnificado("AUD")

def carregar_progresso_aud():
    """Carrega o estado de progresso usando sistema unificado"""
    return progresso_sistema.carregar_progresso()

def salvar_progresso_aud(progresso):
    """Salva o estado de progresso usando sistema unificado"""
    return progresso_sistema.salvar_progresso(progresso)

def processo_ja_executado_aud(numero_processo, progresso=None):
    """Verifica se o processo já foi executado no fluxo AUD usando sistema unificado"""
    if not numero_processo:
        return False
    return progresso_sistema.processo_ja_executado(numero_processo, progresso)

def marcar_processo_executado_aud(numero_processo, progresso=None, status="SUCESSO", detalhes=None):
    """Marca processo como executado no fluxo AUD usando sistema unificado"""
    if not numero_processo:
        return progresso
    return progresso_sistema.marcar_processo_executado(numero_processo, status, detalhes, progresso)


_FALHA_CITACAO = {'gigs_obs': [], 'pec_wrappers': [], 'com_domicilio': 0, 'sem_domicilio': 0, 'total': 0, 'sucesso': False}


def def_citacao(driver, processo_info: dict) -> dict:
    """Determina tipo de citação/gigs pelo polo passivo via API.

    base = 'sum' (ATSUM) ou 'ord' (demais).
    Retorna _FALHA_CITACAO se polo passivo vazio ou API falhar.
    """
    import re as _re

    tipo = (processo_info.get('tipo') or '').upper().strip()
    base = 'sum' if tipo == 'ATSUM' else 'ord'

    try:
        sessao, trt_host = session_from_driver(driver, grau=1)
        client = PjeApiClient(sessao, trt_host, grau=1)
    except Exception as e:
        print(f"[def_citacao] ERRO cliente API: {e}")
        return _FALHA_CITACAO

    m = _re.search(r'/processo/(\d+)(?:/|$)', driver.current_url)
    if not m:
        print(f"[def_citacao] ERRO: ID nao encontrado na URL")
        return _FALHA_CITACAO
    id_processo = m.group(1)

    try:
        partes_raw = client.partes(id_processo) or {}
    except Exception as e:
        print(f"[def_citacao] ERRO partes: {e}")
        return _FALHA_CITACAO

    passivos = partes_raw.get('PASSIVO') or []
    total = len(passivos)
    if total == 0:
        print("[def_citacao] POLO PASSIVO VAZIO — abortando.")
        return _FALHA_CITACAO

    com_dom = 0
    linhas_partes = []
    for parte in passivos:
        id_parte = str(
            parte.get('idPessoa') or parte.get('id') or
            parte.get('idParticipante') or parte.get('idParte') or ''
        )
        nome = parte.get('nome') or parte.get('nomeParte') or '(sem nome)'

        dom_flag = None
        if id_parte:
            dom_flag = client.domicilio_eletronico(id_parte)
        if dom_flag is True:
            com_dom += 1
            linhas_partes.append(f"  {nome}: domicilio=SIM (api.domicilio_eletronico)")
            continue
        if dom_flag is False:
            linhas_partes.append(f"  {nome}: domicilio=NAO (api.domicilio_eletronico)")
            continue

        dom_flag = parte.get('domicilioEletronico') or parte.get('possuiDomicilioEletronico')
        if dom_flag is True:
            com_dom += 1
            linhas_partes.append(f"  {nome}: domicilio=SIM (flag-basica)")
            continue
        if dom_flag is False:
            linhas_partes.append(f"  {nome}: domicilio=NAO (flag-basica)")
            continue

        linhas_partes.append(f"  {nome}: domicilio=?? (sem flag)")

    sem_dom = total - com_dom

    if sem_dom == 0:
        gigs_obs, pec_list = [f"xs {base}"], [f"pec_{base}"]
    elif com_dom == 0:
        gigs_obs, pec_list = [f"xs {base}c"], [f"pec_{base}c"]
    else:
        # Quando há partes com e sem domicílio: criar dois GIGS separados
        gigs_obs = [f"xs {base}", f"xs {base}c"]
        pec_list = [f"pec_{base}", f"pec_{base}c"]

    print(f"[def_citacao] {total} passivos | com={com_dom} sem={sem_dom} | gigs={gigs_obs} pec={pec_list}")
    for l in linhas_partes:
        print(f"[def_citacao]{l}")

    return {
        'gigs_obs': gigs_obs,
        'pec_wrappers': pec_list,
        'com_domicilio': com_dom,
        'sem_domicilio': sem_dom,
        'total': total,
        'sucesso': True,
    }


def acao_bucket_a(driver, numero_processo, processo_info):
    """Ação para bucket A: marcar audiência para 100% digital."""
    try:
        tipo = (processo_info.get('tipo') or '').upper().strip()
        tem_100 = bool(processo_info.get('digital', processo_info.get('tem_100', False)))

        numero_formatado = processo_info.get('numero')
        id_processo = str(processo_info.get('id_processo') or '')
        if not numero_formatado or not id_processo:
            print(f"[AUD][A] ❌ Falha ao extrair número/ID do processo {numero_processo}")
            return False

        rito = 'ATSum' if tipo == 'ATSUM' else 'ATOrd'

        # Se NÃO é 100% digital: marcar audiência + executar ato_unap + GIGS conforme tipo
        if not tem_100:
            print(f"[AUD][A] Processo {numero_processo} sem 100% digital. Marcando audiência, executando ato_unap e GIGS.")
            
            # 1) Marcar audiência na pauta
            marcar_aud(driver, numero_formatado, rito, driver.current_window_handle)
            limpar_overlays_headless(driver)

            # 2) Criar GIGS conforme tipo e presença de domicílio eletrônico
            citacao_a = def_citacao(driver, processo_info)
            if not citacao_a.get('sucesso', True):  # Parar se polo passivo vazio
                print(f"[AUD][A] 🛑 Polo passivo vazio — abortando execução de GIGS para {numero_processo}")
                return False
            
            for obs in citacao_a['gigs_obs']:
                try:
                    print(f"[AUD][A] Criando GIGS para {numero_processo} (prazo: 1, observacao: {obs})")
                    criar_gigs(driver, "1", "", obs)
                except Exception as e:
                    print(f"[AUD][A] ⚠️ Erro ao criar GIGS ({obs}): {e}")

            # 3) Executar ato_unap
            try:
                from atos import ato_unap
                print(f"[AUD][A] Executando ato_unap para {numero_processo}")
                return bool(ato_unap(driver, debug=True))
            except Exception as e:
                print(f"[AUD][A] ⚠️ Erro ao executar ato_unap: {e}")
                return False

        if tipo not in ['ATORD', 'ATSUM', 'ACUM', 'ACCUM']:
            print(f"[AUD][A] Processo {numero_processo} não atende critérios de rito. Pulando.")
            return True

        # 1) Desmarcar 100% (mantém aba /retificar aberta)
        aba_retificar = desmarcar_100(driver, id_processo)
        if not aba_retificar:
            print(f"[AUD][A] ❌ Não foi possível abrir/usar aba retificar")
            return False

        # 2) Marcar audiência na pauta (abre e fecha aba de audiência)
        marcar_aud(driver, numero_formatado, rito, aba_retificar)

        # 3) De volta à aba /retificar: repetir toggle + sim, fechar
        try:
            if aba_retificar in driver.window_handles:
                driver.switch_to.window(aba_retificar)
                remarcar_100_pos_aud(driver)
                driver.close()
        except Exception as e:
            print(f"[AUD][A] ⚠️ Erro ao finalizar retificar: {e}")

        # 4) Retornar à aba detalhe
        try:
            for handle in driver.window_handles:
                driver.switch_to.window(handle)
                if '/detalhe' in driver.current_url:
                    break
        except Exception:
            pass

        # 5) Pós-audiência: GIGS triagem + ato_100
        limpar_overlays_headless(driver)
        try:
            print(f"[AUD][A] Criando GIGS triagem para {numero_processo}")
            criar_gigs(driver, "", "", "xs triagem")
        except Exception as e:
            print(f"[AUD][A] ⚠️ Erro ao criar GIGS triagem: {e}")

        citacao_a2 = def_citacao(driver, processo_info)
        if not citacao_a2.get('sucesso', True):  # Parar se polo passivo vazio
            print(f"[AUD][A] 🛑 Polo passivo vazio após triagem — abortando GIGS para {numero_processo}")
            return False
        
        for obs in citacao_a2['gigs_obs']:
            try:
                print(f"[AUD][A] Criando GIGS para {numero_processo} (prazo: 1, observacao: {obs})")
                criar_gigs(driver, "1", "", obs)
            except Exception as e:
                print(f"[AUD][A] ⚠️ Erro ao criar GIGS ({obs}): {e}")

        try:
            from atos import ato_100
            print(f"[AUD][A] Executando ato_100 para {numero_processo}")
            ato_100(driver, debug=True)
        except Exception as e:
            print(f"[AUD][A] ⚠️ Erro ao executar ato_100: {e}")

        return True
    except Exception as e:
        print(f"[AUD][A] Erro ao executar ações: {e}")
        return False

def obter_processos_triagem_api(driver, numeros=None):
    """Obtém processos da Triagem Inicial lendo exclusivamente o DOM da tabela.

    Fonte de cada campo por linha (<tr class="tr-class"> em table[name="Tabela de Processos"]):
    - numero + tipo : button[aria-label^="Detalhes do Processo - "] → aria-label
    - tarefa        : span.link.processo span.sr-only (texto após "Abrir a tarefa ")
    - tem_audiencia : div[role="presentation"].sobrescrito.ng-star-inserted contendo "Audiência em:"
    - digital       : presença de pje-icone-juizo-digital ou i[aria-label="Juízo 100% Digital"]
    - bucket        : HTE→D | sem_aud→A | digital→B | else→C

    Retorna lista com: numero, id_processo, tarefa, tipo, digital, tem_audiencia, bucket
    """
    TIPOS_VALIDOS = {'ATORD', 'ATSUM', 'ACUM', 'ACCUM', 'HTE'}

    js_dom = r"""
    const TIPOS = new Set(['ATORD', 'ATSUM', 'ACUM', 'ACCUM', 'HTE']);
    const resultado = [];

    const rows = document.querySelectorAll(
        'table[name="Tabela de Processos"] tbody tr.tr-class'
    );

    for (const tr of rows) {
        // numero + tipo via botão "Detalhes do Processo - {TIPO} {NUMERO}"
        const btnDetalhes = tr.querySelector('button[aria-label^="Detalhes do Processo - "]');
        if (!btnDetalhes) continue;
        const m = (btnDetalhes.getAttribute('aria-label') || '')
            .match(/Detalhes do Processo - (\S+)\s+(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})/);
        if (!m) continue;
        const tipo = m[1].toUpperCase();
        const numero = m[2];

        if (!TIPOS.has(tipo)) continue;

        // tarefa via span.sr-only dentro de span.link.processo
        const srOnly = tr.querySelector('span.link.processo span.sr-only');
        const tarefaRaw = (srOnly ? srOnly.textContent : '').trim();
        // Remove prefixo "Abrir a tarefa " e sufixo " do processo: " / " do processo:"
        const tarefaTexto = tarefaRaw
            .replace(/^Abrir a tarefa\s+/, '')
            .replace(/\s+do processo:?\s*$/, '')
            .trim();
        if (!tarefaTexto.toLowerCase().includes('triagem inicial')) continue;

        // tem_audiencia: procurar por todas as divs com sobrescrito e encontrar a que contém "Audiência em:"
        let temAud = false;
        const divsAudiencia = tr.querySelectorAll('div[role="presentation"].sobrescrito');
        for (const div of divsAudiencia) {
            if (div.textContent.includes('Audiência em:')) {
                temAud = true;
                break;
            }
        }

        // digital: ícone 100% digital presente na linha
        const digital = !!(
            tr.querySelector('pje-icone-juizo-digital') ||
            tr.querySelector('i[aria-label="Juízo 100% Digital"]')
        );

        // bucket
        const bucket = tipo === 'HTE' ? 'D' : !temAud ? 'A' : digital ? 'B' : 'C';

        resultado.push({
            numero: numero,
            id_processo: null,
            tarefa: tarefaTexto,
            tipo: tipo,
            digital: digital,
            tem_audiencia: temAud,
            bucket: bucket
        });

        console.log('[AUD_DOM]', numero, tipo,
            '| tarefa:', tarefaTexto,
            '| aud:', temAud, '| digital:', digital, '=>', bucket);
    }

    return resultado;
    """

    try:
        resultado = driver.execute_script(js_dom)
        print(f"[AUD_DOM] {len(resultado or [])} processos obtidos via DOM (Triagem Inicial)")
        return resultado or []
    except Exception as e:
        print(f"[AUD_DOM] Erro na execução do script: {e}")
        traceback.print_exc()
        return []


def indexar_e_processar_lista_aud(driver):
    """
    Indexa e processa lista de processos AUD com controle de progresso.
    
    SEGUINDO O PADRÃO CORRETO DO PEC.PY:
    1. PRIMEIRO indexa todos os processos da lista
    2. DEPOIS filtra quais já foram executados
    3. ENTÃO agrupa em buckets A/B/C
    4. FINALMENTE processa cada bucket individualmente
    
    Returns:
        dict: Resultado do processamento com estatísticas
    """
    try:
        print("[AUD] Iniciando indexação e processamento da lista...")
        
        # Carregar progresso atual
        progresso = carregar_progresso_aud()
        
        # ===== ETAPA 1: INDEXAR TODOS OS PROCESSOS DA LISTA =====
        print("[AUD] 1. Buscando processos via API...")

        from apiaud import buscar_lista_triagem, enriquecer_processo, _is_triagem_inicial
        itens_brutos = buscar_lista_triagem(driver)
        if not itens_brutos:
            print("[AUD] ❌ API não retornou itens — verificar sessão ou endpoint")
            return {"sucesso": False, "erro": "Lista vazia"}

        triagem = [i for i in itens_brutos if _is_triagem_inicial(i)]
        if not triagem:
            print("[AUD] Campo tarefa não identificou Triagem Inicial — usando todos os itens")
            triagem = itens_brutos

        lista_processos = [p for p in (enriquecer_processo(i) for i in triagem) if p]
        if not lista_processos:
            print("[AUD] ❌ Nenhum processo enriquecido")
            return {"sucesso": False, "erro": "Lista vazia"}

        print(f"[AUD] ✅ {len(lista_processos)} processos de Triagem Inicial (de {len(itens_brutos)} brutos)")
        
        # ===== ETAPA 2: FILTRAR POR PROGRESSO (JÁ EXECUTADOS) =====
        print("[AUD] 2. Filtrando processos já executados...")
        
        processos_pendentes = []
        processos_pulados = 0
        
        for processo in lista_processos:
            numero_processo = processo.get('numero')
            
            if processo_ja_executado_aud(numero_processo, progresso):
                print(f"[AUD] ⏭️ Processo {numero_processo} já executado, pulando...")
                processos_pulados += 1
            else:
                processos_pendentes.append(processo)
                print(f"[AUD] ✅ Processo {numero_processo} será processado")
        
        print(f"[AUD] {processos_pulados} processos pulados (já executados)")
        print(f"[AUD] {len(processos_pendentes)} processos serão processados")
        
        if not processos_pendentes:
            print("[AUD] ⚠️ Todos os processos já foram executados!")
            return {"sucesso": True, "processos_executados": 0, "total_na_lista": len(lista_processos)}
        
        # ===== ETAPA 3: AGRUPAR EM BUCKETS =====
        print("[AUD] 3. Particionando buckets A/B/C/D...")

        A = [p for p in processos_pendentes if p.get('bucket') == 'A']
        B = [p for p in processos_pendentes if p.get('bucket') == 'B']
        C = [p for p in processos_pendentes if p.get('bucket') == 'C']
        D = [p for p in processos_pendentes if p.get('bucket') == 'D']

        # Calcular total de processos que passaram pelo filtro de Triagem Inicial
        total_processos_triagem = len(A) + len(B) + len(C) + len(D)

        print(f"[AUD] Buckets: A={len(A)} (sem aud) B={len(B)} (digital+aud) C={len(C)} (nao-digital+aud) D={len(D)} (HTE)")
        
        # ===== ETAPA 4: PROCESSAR BUCKETS =====
        print("[AUD] 4. Processando buckets...")
        
        resultados = {'A': [], 'B': [], 'C': []}
        def processar_bucket(bucket, bucket_nome, acao_callback):
            """Abre cada processo diretamente por URL e executa a ação correspondente."""
            resultados_bucket = []
            handle_principal = driver.current_window_handle

            for idx, processo_info in enumerate(bucket):
                numero_processo = processo_info.get('numero')
                id_processo = processo_info.get('id_processo')
                print(f"[AUD][{bucket_nome}] Processando {idx+1}/{len(bucket)}: {numero_processo}")

                if not id_processo:
                    print(f"[AUD][{bucket_nome}] ❌ id_processo ausente para {numero_processo}")
                    resultados_bucket.append({'numero': numero_processo, 'acao': f'bucket_{bucket_nome.lower()}', 'ok': False, 'msg': 'id_processo ausente'})
                    continue

                try:
                    detalhe_url = f"https://pje.trt2.jus.br/pjekz/processo/{id_processo}/detalhe/"
                    driver.get(detalhe_url)
                    esperar_elemento(driver, 'pje-cabecalho-processo,pje-timeline', by=By.CSS_SELECTOR, timeout=15)
                except Exception as e:
                    print(f"[AUD][{bucket_nome}] ❌ Falha ao navegar para detalhe de {numero_processo}: {e}")
                    resultados_bucket.append({'numero': numero_processo, 'acao': f'bucket_{bucket_nome.lower()}', 'ok': False, 'msg': f'Falha ao navegar: {e}'})
                    continue

                try:
                    print(f"[AUD][{bucket_nome}] Executando triagem de {numero_processo}")
                    processo_info['triagem'] = triagem_peticao(driver)
                except Exception as e:
                    processo_info['triagem'] = f"ERRO: falha ao executar triagem: {e}"
                    print(f"[AUD][{bucket_nome}] ⚠️ Falha ao executar triagem de {numero_processo}: {e}")

                triagem = processo_info.get('triagem')
                if isinstance(triagem, str) and triagem.startswith('ERRO: ERRO_CRITICO_401'):
                    print(f"[AUD][{bucket_nome}] 🛑 ERRO CRÍTICO 401 em {numero_processo} — sessão rejeitada, pular sem registrar progresso")
                    resultados_bucket.append({'numero': numero_processo, 'acao': f'bucket_{bucket_nome.lower()}', 'ok': False, 'msg': triagem})
                    continue

                try:
                    triagem = processo_info.get('triagem')
                    if triagem:
                        print(f"[AUD][{bucket_nome}] Registrando comentario da triagem para {numero_processo}")
                        sucesso_comentario = criar_comentario(driver, triagem)
                        if not sucesso_comentario:
                            print(f"[AUD][{bucket_nome}] ⚠️ Comentario da triagem de {numero_processo} pode não ter sido salvo")
                        limpar_overlays_headless(driver)
                except Exception as e:
                    print(f"[AUD][{bucket_nome}] ⚠️ Falha ao registrar comentario da triagem de {numero_processo}: {e}")
                    print(f"[AUD][{bucket_nome}] triagem tipo={type(triagem).__name__} tamanho={len(triagem) if isinstance(triagem, str) else 'N/A'}")
                    traceback.print_exc()

                try:
                    sucesso = acao_callback(driver, numero_processo, processo_info)
                    resultados_bucket.append({'numero': numero_processo, 'acao': f'bucket_{bucket_nome.lower()}', 'ok': sucesso, 'msg': '' if sucesso else 'Ação falhou'})
                except Exception as e:
                    print(f"[AUD][{bucket_nome}] ❌ Erro ao executar ação para {numero_processo}: {e}")
                    resultados_bucket.append({'numero': numero_processo, 'acao': f'bucket_{bucket_nome.lower()}', 'ok': False, 'msg': str(e)})

                # Fechar abas extras abertas durante a ação e retornar ao handle principal
                try:
                    for h in list(driver.window_handles):
                        if h != handle_principal:
                            try:
                                driver.switch_to.window(h)
                                driver.close()
                            except Exception:
                                pass
                    driver.switch_to.window(handle_principal)
                except Exception as eback:
                    print(f"[AUD][{bucket_nome}] ⚠️ Erro ao limpar abas: {eback}")

            return resultados_bucket
        
        def acao_bucket_b(driver, numero_processo, processo_info):
            """Ação para bucket B: criar gigs triagem + criar gigs específico + ato_100"""
            try:
                # ===== PRIMEIRA AÇÃO: GIGS TRIAGEM =====
                try:
                    print(f"[AUD][B] Criando GIGS triagem para {numero_processo}")
                    criar_gigs(driver, "", "", "xs triagem")
                except Exception as e:
                    print(f"[AUD][B] ⚠️ Erro ao criar GIGS triagem: {e}")

                # ===== SEGUNDA AÇÃO: CRIAR GIGS =====

                tipo = (processo_info.get('tipo') or '').upper()
                
                # Garantir que qualquer overlay/modal do GIGS triagem foi fechado
                limpar_overlays_headless(driver)

                # Determinar observação pelo domicílio eletrônico do polo passivo
                citacao_b = def_citacao(driver, processo_info)
                
                # Verificar se polo passivo está vazio
                if not citacao_b.get('sucesso', True):
                    print(f"[AUD][B] 🛑 Polo passivo vazio — abortando GIGS para {numero_processo}")
                    return False
                
                for obs in citacao_b['gigs_obs']:
                    print(f"[AUD][B] Criando GIGS para {numero_processo} (prazo: 1, observacao: {obs})")
                    criar_gigs(driver, "1", "", obs)
                
                # ===== TERCEIRA AÇÃO: EXECUTAR ATO_100 =====
                try:
                    from atos import ato_100
                    print(f"[AUD][B] Executando ato_100 para {numero_processo}")
                    ato_100(driver, debug=True)
                except Exception as e:
                    print(f"[AUD][B] ⚠️ Erro ao executar ato_100: {e}")
                
                print(f"[AUD][B] ✅ GIGS criado com sucesso para {numero_processo}")
                return True
            except Exception as e:
                print(f"[AUD][B] Erro ao criar GIGS: {e}")
                return False
        
        def acao_bucket_c(driver, numero_processo, processo_info):
            """Ação para bucket C: pec conforme domicílio eletrônico + mov_aud"""
            try:
                from atos import mov_aud
                from atos.wrappers_pec import pec_ord, pec_sum, pec_ordc, pec_sumc
                _PEC_MAP = {'pec_ord': pec_ord, 'pec_sum': pec_sum,
                            'pec_ordc': pec_ordc, 'pec_sumc': pec_sumc}

                citacao_c = def_citacao(driver, processo_info)
                
                # Verificar se polo passivo está vazio
                if not citacao_c.get('sucesso', True):
                    print(f"[AUD][C] 🛑 Polo passivo vazio — abortando PEC para {numero_processo}")
                    return False
                
                ok = False
                for pec_nome in citacao_c['pec_wrappers']:
                    pec_fn = _PEC_MAP.get(pec_nome)
                    if pec_fn:
                        print(f"[AUD][C] Executando {pec_nome} para {numero_processo}")
                        try:
                            ok = bool(pec_fn(driver, debug=True)) or ok
                        except Exception as e:
                            print(f"[AUD][C] ⚠️ Erro em {pec_nome}: {e}")

                if ok:
                    print(f"[AUD][C] Executando mov_aud para {numero_processo}")
                    mov_ok = mov_aud(driver, debug=True)
                    return bool(mov_ok)
                return ok
            except Exception as e:
                print(f"[AUD][C] Erro na ação: {e}")
                return False
        
        def acao_bucket_d(driver, numero_processo, processo_info):
            """Ação para bucket D: criar gigs triagem + executar ato_ratif"""
            try:
                # ===== PRIMEIRA AÇÃO: GIGS TRIAGEM =====
                try:
                    print(f"[AUD][D] Criando GIGS triagem para {numero_processo}")
                    criar_gigs(driver, "", "", "xs triagem")
                except Exception as e:
                    print(f"[AUD][D] ⚠️ Erro ao criar GIGS triagem: {e}")

                # ===== SEGUNDA AÇÃO: EXECUTAR ATO_RATIF ======
                try:
                    from xx.atos import ato_ratif
                    print(f"[AUD][D] Executando ato_ratif para {numero_processo}")
                    ok = ato_ratif(driver, debug=True)
                    if ok:
                        print(f"[AUD][D] ✅ ato_ratif executado com sucesso")
                        return True
                    else:
                        print(f"[AUD][D] ❌ ato_ratif falhou")
                        return False
                except ImportError:
                    print(f"[AUD][D] ato_ratif não disponível")
                    return False
                except Exception as e:
                    print(f"[AUD][D] Erro ao executar ato_ratif: {e}")
                    return False
            
            except Exception as e:
                print(f"[AUD][D] Erro geral na ação: {e}")
                return False
        
        # Processar cada bucket
        resultados['A'] = processar_bucket(A, 'A', acao_bucket_a)
        resultados['B'] = processar_bucket(B, 'B', acao_bucket_b)
        resultados['C'] = processar_bucket(C, 'C', acao_bucket_c)
        resultados['D'] = processar_bucket(D, 'D', acao_bucket_d)
        
        # ===== ETAPA 5: MARCAR PROCESSOS EXECUTADOS =====
        print("[AUD] 5. Marcando processos executados...")
        
        processos_sucesso = 0
        processos_erro = 0
        
        # Função auxiliar para extrair resultados
        def processar_resultados_bucket(bucket_resultados, bucket_nome):
            nonlocal processos_sucesso, processos_erro
            for res in bucket_resultados:
                numero = res.get('numero')
                ok = res.get('ok', False)
                if ok:
                    marcar_processo_executado_aud(numero, progresso, "SUCESSO", f"Bucket {bucket_nome}")
                    processos_sucesso += 1
                else:
                    marcar_processo_executado_aud(numero, progresso, "ERRO", f"Bucket {bucket_nome}: {res.get('msg', '')}")
                    processos_erro += 1
        
        processar_resultados_bucket(resultados['A'], 'A')
        processar_resultados_bucket(resultados['B'], 'B')
        processar_resultados_bucket(resultados['C'], 'C')
        processar_resultados_bucket(resultados['D'], 'D')
        
        # ===== ETAPA 6: RELATÓRIO FINAL =====
        print("[AUD] ========== RELATÓRIO FINAL ==========")
        print(f"[AUD] Total de processos na lista: {len(lista_processos)}")
        print(f"[AUD] Processos de Triagem Inicial: {total_processos_triagem}")
        print(f"[AUD] Processos executados com sucesso: {processos_sucesso}")
        print(f"[AUD] Processos com erro: {processos_erro}")
        print(f"[AUD] Taxa de sucesso: {(processos_sucesso/total_processos_triagem*100):.1f}%" if total_processos_triagem else "N/A")
        print("[AUD] ====================================")
        
        return {
            "sucesso": True,
            "processos_executados": processos_sucesso,
            "processos_erro": processos_erro,
            "total_na_lista": len(lista_processos),
            "resultados_detalhados": resultados
        }
        
    except Exception as e:
        print(f"[AUD] ❌ Erro geral na indexação: {e}")
        traceback.print_exc()
        return {"sucesso": False, "erro": str(e)}


def criar_driver_e_logar(driver: Optional[WebDriver] = None, log: bool = True) -> Optional[WebDriver]:
    """Cria um driver (se driver for None) e executa login usando Fix.utils.
    Retorna o driver pronto ou None em caso de falha."""
    if driver is not None:
        if log:
            print("[AUD] Usando driver fornecido")
        return driver

    try:
        if log:
            print("[AUD] Criando driver e executando login (Fix.utils)")
        from Fix.utils import driver_pc, login_cpf

        drv = driver_pc()
        if not drv:
            print("[AUD] Falha ao criar driver")
            return None

        ok = False
        try:
            ok = login_cpf(drv)
        except Exception as e:
            print(f"[AUD] Erro ao executar login_cpf: {e}")
            ok = False

        if not ok:
            try:
                drv.quit()
            except Exception:
                pass
            print("[AUD] Login falhou")
            return None

        return drv

    except Exception as e:
        print(f"[AUD] Exceção ao criar/logar driver: {e}")
        traceback.print_exc()
        return None


def coletar_lista_processos(driver: WebDriver) -> List[Dict[str, Any]]:
    """Coleta todos os processos visíveis na lista e extrai campos relevantes.

    Retorna lista de dicionários com chaves: numero (string sem formatação),
    tipo (ATOrd/ATSum/ACum/HTE/ou ''), tem_100 (bool), audiencia (str or ''),
    responsavel (str or ''), row_index (int).
    """
    js = r"""
    var linhas = Array.from(document.querySelectorAll('tbody tr.tr-class'));
    var resultado = [];
    linhas.forEach(function(tr, idx){
        try {
            var numero = '';
            // Extrair número do processo - baseado no HTML real do aud.js
            var linkProcesso = tr.querySelector('pje-descricao-processo a, a[role="link"]');
            if (linkProcesso) {
                numero = (linkProcesso.innerText || linkProcesso.textContent || '').trim();
            }

            // Extrair tipo (ATOrd/ATSum/ACum/HTE) - baseado no HTML real
            var tipo = '';
            // Tentar múltiplas abordagens para encontrar o tipo
            var spansTipo = tr.querySelectorAll('pje-descricao-processo span.align-end.ng-star-inserted');
            for (var i = 0; i < spansTipo.length; i++) {
                var texto = (spansTipo[i].innerText || spansTipo[i].textContent || '').trim();
                if (texto && (texto.includes('ATOrd') || texto.includes('ATSum') || texto.includes('ACum') || texto.includes('Accum') || texto.includes('HTE'))) {
                    tipo = texto;
                    console.log('Tipo encontrado:', tipo);
                    break;
                }
            }

            // Fallback: tentar pegar o primeiro span align-end que não seja vazio
            if (!tipo) {
                var primeiroSpan = tr.querySelector('pje-descricao-processo span.align-end.ng-star-inserted');
                if (primeiroSpan) {
                    tipo = (primeiroSpan.innerText || primeiroSpan.textContent || '').trim();
                    console.log('Tipo via fallback:', tipo);
                }
            }

            // 100% digital - baseado no HTML real
            var tem100 = false;
            var icone100 = tr.querySelector('.texto-icone-juizo-digital');
            if (icone100 && (icone100.innerText || icone100.textContent || '').includes('100')) {
                tem100 = true;
            }

            // Audiência - buscar div.sobrescrito com texto "Audiência em:"
            var aud = '';
            var divAud = tr.querySelector('div.sobrescrito.ng-star-inserted');
            if (divAud && (divAud.innerText || divAud.textContent || '').includes('Audiência em:')) {
                aud = (divAud.innerText || divAud.textContent || '').trim();
            } else {
                var tdPrincipal = tr.querySelector('td:nth-child(2)');
                if (tdPrincipal) {
                    aud = (tdPrincipal.innerText || tdPrincipal.textContent || '').trim();
                }
            }

            // Responsável - baseado no HTML real
            var resp = '';
            var inputResp = tr.querySelector('pje-gigs-cadastro-responsavel input, input[aria-label*="Respons"]');
            if (inputResp) {
                resp = (inputResp.value || '').trim();
            }

            // Extrair tarefa para debug
            var tarefa = '';
            var tarefaElement = tr.querySelector('a[role="button"] span, span.link, .link span');
            if (tarefaElement) {
                tarefa = (tarefaElement.innerText || tarefaElement.textContent || '').trim();
            }

            // Normalize numero removing non-digits
            var numero_clean = numero.replace(/[^0-9]/g,'');

            resultado.push({
                numero: numero_clean || numero,
                numero_raw: numero,
                tipo: tipo,
                tem_100: tem100,
                audiencia: aud,
                responsavel: resp,
                tarefa: tarefa,
                row_index: idx
            });
        } catch(e) {
            console.log('Erro na linha ' + idx + ': ' + e.message);
            resultado.push({
                numero: null,
                numero_raw: '',
                tipo: '',
                tem_100: false,
                audiencia: '',
                responsavel: '',
                tarefa: '',
                row_index: idx
            });
        }
    });
    return resultado;
    """

    try:
        dados = driver.execute_script(js)
        if not dados:
            print("[AUD] Nenhuma linha retornada pela coleta JS")
            return []
        print(f"[AUD] Coletados {len(dados)} processos da página (raw)")
        return dados
    except Exception as e:
        print(f"[AUD] Erro ao executar JS de coleta: {e}")
        traceback.print_exc()
        return []


def agrupar_em_buckets(lista: List[Dict[str, Any]]):
    """Agrupa em quatro buckets A, B, C, D conforme regra do usuário.

    Primeiro filtra apenas processos da tarefa "Triagem Inicial".
    Depois filtra apenas processos Atord, Atsum, Accum ou HTE.
    A: sem audiência
    B: tem audiência + tem 100%
    C: tem audiência + nao tem 100%
    D: HTE
    """
    # Primeiro filtrar apenas processos da Triagem Inicial
    processos_triagem = []
    for item in lista:
        tarefa = (item.get('tarefa') or '').strip()
        if 'Triagem Inicial' in tarefa:
            processos_triagem.append(item)
        else:
            print(f"[AUD] Pulando processo {item.get('numero')} - tarefa: '{tarefa}'")

    print(f"[AUD] Filtrados {len(processos_triagem)} processos da Triagem Inicial de {len(lista)} total")

    # Segundo filtro: apenas Atord, Atsum, Accum ou HTE
    processos_validos = []
    tipos_validos = ['ATORD', 'ATSUM', 'ACUM', 'HTE']
    
    for item in processos_triagem:
        tipo = (item.get('tipo') or '').upper().strip()
        if tipo in tipos_validos:
            processos_validos.append(item)
        else:
            print(f"[AUD] Pulando processo {item.get('numero')} - tipo '{tipo}' não é Atord/Atsum/Accum/HTE")

    print(f"[AUD] Filtrados {len(processos_validos)} processos válidos (Atord/Atsum/Accum/HTE) de {len(processos_triagem)} da triagem")

    A = []
    B = []
    C = []
    D = []

    for item in processos_validos:
        tipo = (item.get('tipo') or '').upper().strip()
        if tipo == 'HTE':
            D.append(item)
            continue

        # obter_processos_triagem_api grava 'temaudiencia' (bool)
        # coletarlistaprocessos legado grava 'audiencia' (str) — fallback
        tem_aud = bool(item.get('temaudiencia', False))
        if not tem_aud:
            audiencia = (item.get('audiencia') or '').strip()
            if isinstance(audiencia, str) and 'Audiência em' in audiencia:
                tem_aud = True

        if not tem_aud:
            A.append(item)
        elif item.get('tem_100', False):
            B.append(item)
        else:
            C.append(item)

    print(f"[AUD] Buckets: A={len(A)} (sem audiência) B={len(B)} (com audiência + 100%) C={len(C)} (com audiência + sem 100%) D={len(D)} (HTE)")
    return A, B, C, D


def reindexar_linha_js(driver, numero_processo):
    """
    Reindexa linha usando JavaScript para encontrar o processo pelo número.
    Similar à lógica de coletar_lista_processos, mas retorna o elemento da linha.
    
    Args:
        driver: WebDriver do Selenium
        numero_processo: Número do processo a procurar (com ou sem formatação)
    
    Returns:
        WebElement da linha ou None se não encontrado
    """
    try:
        # JavaScript para encontrar a linha que contém o processo
        js = r"""
        var numero_procurado = arguments[0];
        var linhas = Array.from(document.querySelectorAll('tbody tr.tr-class'));
        
        for (var i = 0; i < linhas.length; i++) {
            try {
                var tr = linhas[i];
                
                // Extrair número do processo da mesma forma que coletar_lista_processos
                var numero = '';
                var linkProcesso = tr.querySelector('pje-descricao-processo a, a[role="link"]');
                if (linkProcesso) {
                    numero = (linkProcesso.innerText || linkProcesso.textContent || '').trim();
                }
                
                // Normalizar número removendo não-dígitos
                var numero_clean = numero.replace(/[^0-9]/g,'');
                
                // Verificar se corresponde (comparar números limpos)
                if (numero_clean === numero_procurado || numero === numero_procurado) {
                    // Retornar índice da linha encontrada
                    return i;
                }
            } catch(e) {
                console.log('Erro ao verificar linha ' + i + ': ' + e.message);
                continue;
            }
        }
        
        // Não encontrou
        return -1;
        """
        
        # Executar JavaScript para encontrar o índice da linha
        linha_index = driver.execute_script(js, numero_processo)
        
        if linha_index >= 0:
            print(f"[AUD] ✅ Processo {numero_processo} encontrado na linha {linha_index}")
            
            # Agora obter o elemento da linha usando Selenium
            from selenium.webdriver.common.by import By
            linhas = driver.find_elements(By.CSS_SELECTOR, 'tbody tr.tr-class')
            
            if linha_index < len(linhas):
                return linhas[linha_index]
            else:
                print(f"[AUD] ❌ Índice {linha_index} fora do range (total: {len(linhas)})")
                return None
        else:
            print(f"[AUD] ❌ Processo {numero_processo} não encontrado na lista atual")
            return None
            
    except Exception as e:
        print(f"[AUD] ❌ Erro ao reindexar linha para {numero_processo}: {e}")
        return None


def _abrir_nova_aba(driver: WebDriver, url: str, aba_origem: str, url_fragmento: Optional[str] = None, timeout: int = 10) -> Optional[str]:
    """Abre URL em nova aba e retorna handle da nova aba (opcionalmente filtrando por fragmento)."""
    try:
        driver.execute_script("window.open(arguments[0], '_blank');", url)
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                abas = driver.window_handles
                for h in abas:
                    if h == aba_origem:
                        continue
                    driver.switch_to.window(h)
                    if not url_fragmento:
                        return h
                    try:
                        if url_fragmento in (driver.current_url or ""):
                            return h
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(0.2)
        return trocar_para_nova_aba(driver, aba_origem)
    except Exception as e:
        print(f"[AUD] ❌ Erro ao abrir nova aba: {e}")
        return None


def desmarcar_100(driver: WebDriver, id_processo: str) -> Optional[str]:
    """Desmarca 100% digital na aba /retificar e mantém a aba aberta."""
    aba_detalhe = driver.current_window_handle
    url_retificar = f"https://pje.trt2.jus.br/pjekz/processo/{id_processo}/retificar"

    nova_aba = _abrir_nova_aba(driver, url_retificar, aba_detalhe, url_fragmento="/retificar")
    if not nova_aba:
        return None

    try:
        step_carac = esperar_elemento(
            driver,
            "mat-step-header[aria-posinset='4']",
            by=By.CSS_SELECTOR,
            timeout=15
        )
        if not step_carac:
            raise Exception("Step 'Características' não encontrado")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", step_carac)
        safe_click(driver, step_carac)
        time.sleep(1)

        toggle = esperar_elemento(
            driver,
            "mat-slide-toggle[formcontrolname='juizoDigital']",
            by=By.CSS_SELECTOR,
            timeout=10
        )
        if not toggle:
            raise Exception("Toggle Juízo 100% digital não encontrado")

        if "mat-checked" in (toggle.get_attribute("class") or ""):
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", toggle)
            label = toggle.find_element(By.CSS_SELECTOR, "label.mat-slide-toggle-label")
            safe_click(driver, label)
            esperar_elemento(
                driver,
                "pje-modal-juizo-digital",
                by=By.CSS_SELECTOR,
                timeout=10
            )
            modal = driver.find_element(By.CSS_SELECTOR, "pje-modal-juizo-digital")
            if "Juízo 100% digital" in (modal.text or ""):
                botoes = modal.find_elements(By.CSS_SELECTOR, "button")
                if len(botoes) >= 4:
                    safe_click(driver, botoes[3])
                elif botoes:
                    safe_click(driver, botoes[0])
            esperar_elemento(
                driver,
                "mat-slide-toggle[formcontrolname='juizoDigital']:not(.mat-checked)",
                by=By.CSS_SELECTOR,
                timeout=10
            )
            time.sleep(1)
        return nova_aba
    except Exception as e:
        print(f"[AUD] ❌ Erro ao desmarcar 100%: {e}")
        return nova_aba


def remarcar_100_pos_aud(driver: WebDriver):
    """Remarcar 100% após marcar audiência (apenas toggle + Sim)."""
    try:
        toggle = esperar_elemento(
            driver,
            "mat-slide-toggle[formcontrolname='juizoDigital']",
            by=By.CSS_SELECTOR,
            timeout=10
        )
        if not toggle:
            raise Exception("Toggle Juízo 100% digital não encontrado")

        if "mat-checked" not in (toggle.get_attribute("class") or ""):
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", toggle)
            label = toggle.find_element(By.CSS_SELECTOR, "label.mat-slide-toggle-label")
            safe_click(driver, label)
            esperar_elemento(
                driver,
                "pje-modal-juizo-digital",
                by=By.CSS_SELECTOR,
                timeout=10
            )
            modal = driver.find_element(By.CSS_SELECTOR, "pje-modal-juizo-digital")
            if "Juízo 100% digital" in (modal.text or ""):
                botoes = modal.find_elements(By.CSS_SELECTOR, "button")
                if botoes:
                    safe_click(driver, botoes[0])
            esperar_elemento(
                driver,
                "mat-slide-toggle[formcontrolname='juizoDigital'].mat-checked",
                by=By.CSS_SELECTOR,
                timeout=10
            )
            time.sleep(1)
    except Exception as e:
        print(f"[AUD] ❌ Erro ao remarcar 100%: {e}")


def marcar_aud(driver: WebDriver, numero_processo: str, rito: str, aba_retorno: str):
    """Marca audiência na pauta e fecha a aba de audiência ao final."""
    aba_origem = driver.current_window_handle
    url_pauta = f"https://pje.trt2.jus.br/pjekz/pauta-audiencias?maisPje=true&numero={numero_processo}&rito={rito}&fase=Conhecimento"
    aba_aud = _abrir_nova_aba(driver, url_pauta, aba_origem, url_fragmento="/pauta-audiencias")
    if not aba_aud:
        return

    sucesso = False
    try:
        esperar_elemento(driver, "mat-card.card-pauta", by=By.CSS_SELECTOR, timeout=15)

        if rito.upper() == 'ATSUM':
            linha = esperar_elemento(
                driver,
                "//tr[.//span[contains(normalize-space(.), 'Una (rito sumaríssimo)')]]",
                by=By.XPATH,
                timeout=10
            )
        else:
            linha = esperar_elemento(
                driver,
                "//tr[.//span[normalize-space(.)='Una'] and not(.//span[contains(normalize-space(.), 'sumar')]) ]",
                by=By.XPATH,
                timeout=10
            )

        if not linha:
            raise Exception("Linha de pauta não encontrada")

        btn_plus = linha.find_element(By.XPATH, ".//button[@aria-label='Designar Audiência'] | .//i[contains(@class,'fa-plus-circle')]/ancestor::button")
        safe_click(driver, btn_plus)

        modal = esperar_elemento(driver, "mat-dialog-container", by=By.CSS_SELECTOR, timeout=10)
        if not modal:
            raise Exception("Modal de audiência não encontrado")

        input_num = modal.find_element(By.CSS_SELECTOR, "input#inputNumeroProcesso")
        valor_atual = (input_num.get_attribute('value') or '').strip()
        if not valor_atual:
            try:
                safe_click(driver, input_num)
                input_num.clear()
                input_num.send_keys(numero_processo)
                driver.execute_script(
                    "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));"
                    "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
                    input_num
                )
            except Exception:
                preencher_campo(driver, "#inputNumeroProcesso", numero_processo)
        time.sleep(0.8)
        btn_confirmar = esperar_elemento(
            driver,
            "//mat-dialog-container//button[.//span[normalize-space(.)='Confirmar']]",
            by=By.XPATH,
            timeout=10
        )
        if not btn_confirmar:
            raise Exception("Botão Confirmar não encontrado")
        safe_click(driver, btn_confirmar)
        time.sleep(1)
        modal_confirmado = esperar_elemento(
            driver,
            "//mat-dialog-container//*[self::h4 or self::h3][contains(normalize-space(.), 'Designação Confirmada')]",
            by=By.XPATH,
            timeout=10
        )
        if modal_confirmado:
            btn_fechar = esperar_elemento(
                driver,
                "//mat-dialog-container//button[.//span[normalize-space(.)='Fechar']]",
                by=By.XPATH,
                timeout=10
            )
            if btn_fechar:
                safe_click(driver, btn_fechar)
                time.sleep(0.5)
        sucesso = True
    except Exception as e:
        print(f"[AUD] ❌ Erro ao marcar audiência: {e}")
    finally:
        if sucesso:
            try:
                driver.close()
            except Exception:
                pass
            try:
                if aba_retorno in driver.window_handles:
                    driver.switch_to.window(aba_retorno)
            except Exception:
                pass



def executar_acoes_por_bucket(driver: WebDriver, A: List[Dict[str, Any]], B: List[Dict[str, Any]], C: List[Dict[str, Any]]):
    """Esta função foi substituída pela nova abordagem de indexação e processamento individual.
    Mantida apenas para compatibilidade, mas não deve ser usada."""
    print("[AUD] AVISO: executar_acoes_por_bucket está deprecated. Use indexar_e_processar_lista_aud.")
    return {'A': [], 'B': [], 'C': []}


def run_aud(driver: Optional[WebDriver] = None):
    """Fluxo principal: cria/usa driver, navega para a lista e processa com indexação e buckets.
    Retorna sumário de resultados.
    """
    # ===== CONFIGURAR RECOVERY GLOBAL =====
    from Fix.utils import driver_pc, login_cpf
    configurar_recovery_driver(driver_pc, login_cpf)
    print("[AUD] ✅ Sistema de recuperação automática configurado")
    
    drv = criar_driver_e_logar(driver)
    if not drv:
        print('[AUD] Falha ao obter driver (aborting)')
        return None

    try:
        url = 'https://pje.trt2.jus.br/pjekz/painel/global/10/lista-processos'
        print(f"[AUD] Navegando para {url}")
        drv.get(url)
        time.sleep(3)

        # Usar nova abordagem de indexação e processamento
        resultado = indexar_e_processar_lista_aud(drv)
        
        if resultado.get("sucesso"):
            print('[AUD] Execução finalizada com sucesso!')
            return resultado
        else:
            print(f'[AUD] Execução finalizada com problemas: {resultado.get("erro", "Erro desconhecido")}')
            return resultado

    except Exception as e:
        novo_driver = handle_exception_with_recovery(e, drv, "AUD_RUN")
        if novo_driver:
            drv = novo_driver
            # Tentar continuar ou retornar resultado parcial
        else:
            print(f"[AUD] Erro geral no run_aud: {e}")
            traceback.print_exc()
        return None


if __name__ == '__main__':
    # Execução direta para testes rápidos (requere login automático configurado em driver_config)
    print('[AUD] executando como script')
    resultado = run_aud(None)
    print('[AUD] Resultado do run:', resultado)
