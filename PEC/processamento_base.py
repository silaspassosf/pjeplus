import logging
logger = logging.getLogger(__name__)

"""Módulo PEC - Processamento de Execução e Cumprimento (PJe)."""

from typing import Any

from .regras import determinar_acoes_por_observacao
from .regras import executar_acao_pec, chamar_funcao_com_assinatura_correta
from .executor import executar_acao as executar_acao_base


# ===== IMPORTS PESADOS REMOVIDOS (LAZY LOADING) =====
# Movidos para cache sob demanda para carregamento 8-10x mais rápido

# Cache de módulos para lazy loading
_pec_modules_cache = {}


def _lazy_import_pec():
    """Carrega módulos pesados sob demanda (lazy loading)."""
    global _pec_modules_cache
    
    if not _pec_modules_cache:
        from Fix.core import aguardar_e_clicar, esperar_elemento
        from Fix.extracao import extrair_dados_processo, abrir_detalhes_processo, trocar_para_nova_aba, reindexar_linha
        from atos import pec_excluiargos
        
        _pec_modules_cache.update({
            'aguardar_e_clicar': aguardar_e_clicar,
            'esperar_elemento': esperar_elemento,
            'extrair_dados_processo': extrair_dados_processo,
            'abrir_detalhes_processo': abrir_detalhes_processo,
            'trocar_para_nova_aba': trocar_para_nova_aba,
            'reindexar_linha': reindexar_linha,
            'pec_excluiargos': pec_excluiargos,
        })
    
    return _pec_modules_cache


from typing import Optional, List
from selenium.webdriver.remote.webdriver import WebDriver

def executar_acao(driver: WebDriver, acao: str, numero_processo: str, observacao: str, destinatarios_override: Optional[List] = None, driver_sisb: Optional[WebDriver] = None) -> None:
    """
    Executa a ação determinada no processo aberto.
    Suporta apenas funções diretas (como P2B) e listas de funções para execução sequencial.
    Detecta a assinatura de cada função para chamar com os argumentos corretos.
    
    Args:
        driver_sisb: Driver SISBAJUD opcional para reutilização (evita criar múltiplos drivers)
    """
    return executar_acao_base(
        driver,
        acao,
        numero_processo,
        observacao,
        destinatarios_override,
        driver_sisb
    )


def processar_processo_pec_individual(driver):
    """
    Callback específico para processar um processo individual no PEC
    Usado pelo sistema centralizado de retry do PJE.PY
    
    Esta função foca APENAS na lógica específica do PEC,
    sem se preocupar com retry, progresso ou navegação para /detalhe
    """
    try:
        # 1. Extrair dados do processo atual
        numero_processo = extrair_numero_processo_pec(driver)
        if not numero_processo:
            print("[PEC_INDIVIDUAL] ❌ Não foi possível extrair número do processo")
            return False


        # =====================================================================
        # TESTE – API GIGS + BUCKETS PEC (reutiliza regras existentes)
        # =====================================================================


        def _acaonome_para_bucket_pec(acaonome: str) -> str:
            """
            Mesma lógica de classificação usada por indexarecriarbucketsunico.
            Centralizada aqui para não duplicar.
            """
            SISBAJUD = {"minutabloqueio", "minutabloqueio60", "processarordemsisbajud", "processarordemsisbajudwrapper"}
            CARTA    = {"carta", "analisardocumentosposcarta"}
            SOB      = {"movsob", "defchip", "movaud"}
            SOBREST  = {"defsob"}

            name = (acaonome or "").lower()

            if name in SISBAJUD:
                return "sisbajud"
            if name in CARTA:
                return "carta"
            if name in SOB:
                return "sob"
            if name in SOBREST:
                return "sobrestamento"
            if name.startswith("pec"):
                return "comunicacoes"
            return "outros"


        def _resolver_acaonome(acaofunc) -> str:
            """
            Extrai o nome canônico da ação — mesmo algoritmo do indexarecriarbucketsunico.
            Trata função direta, lista de funções e wrappers pecord/pecsum/pecsigilo.
            """
            import inspect
            try:
                from atos.comunicacao import pecord, pecsum, pecsigilo
                _WRAPPERS = {id(pecord): "pecord", id(pecsum): "pecsum", id(pecsigilo): "pecsigilo"}
            except Exception:
                _WRAPPERS = {}

            # Se for callable simples
            if callable(acaofunc):
                return _WRAPPERS.get(id(acaofunc), getattr(acaofunc, "__name__", "unknown"))

            # Se for lista/tupla de ações, tentar resolver primeiro elemento relevante
            if isinstance(acaofunc, (list, tuple)):
                for func in acaofunc:
                    if func is None or not callable(func):
                        continue
                    nome = _WRAPPERS.get(id(func), getattr(func, "__name__", ""))
                    if not nome:
                        continue
                    # Detectar SISBAJUD via nome ou código-fonte
                    try:
                        if "bloqueio" in nome or "sisb" in nome.lower():
                            return "minutabloqueio"
                        src = inspect.getsource(func)
                        src_l = src.lower()
                        if "processarbloqueios" in src_l or "sisb" in src_l or "bloqueio" in src_l:
                            return "minutabloqueio"
                    except Exception:
                        pass
                    return nome
                return "unknown"

            return str(acaofunc) if acaofunc else "unknown"


        def testar_api_gigs_e_buckets_pec(
            driver,
            lista_processos: list,
            filtrar_concluidos: bool = True,
        ) -> dict:
            """
            Diagnóstico manual: chama a API GIGS para cada processo da lista,
            aplica `determinar_acoes_por_observacao` (regras reais do PEC) e agrupa
            os resultados nos mesmos buckets usados pelo fluxo de produção.

            Uso:
                from PEC.processamento_base import testar_api_gigs_e_buckets_pec
                buckets = testar_api_gigs_e_buckets_pec(driver, ["0000000-00.0000.5.02.0000"])

            Args:
                driver            WebDriver já autenticado no PJe.
                lista_processos   Lista de números CNJ a testar.
                filtrar_concluidos  Se True, ignora atividades com status CONCLUÍDO/CANCELADO.

            Returns:
                Dict[bucket_name, List[Dict]] — processos agrupados por bucket.
            """
            # Import dinâmico para evitar custo em carregamento normal do módulo
            from Fix.variaveis import session_from_driver, PjeApiClient, obter_gigs_com_fase
            # usar a função já importada no topo do módulo
            # determinar_acoes_por_observacao

            sess, trt = session_from_driver(driver, grau=1)
            client = PjeApiClient(sess, trt)

            buckets: dict = {
                "sisbajud": [],
                "carta": [],
                "sob": [],
                "sobrestamento": [],
                "comunicacoes": [],
                "outros": [],
                "sem_acao": [],       # observacao reconhecida mas sem regra mapeada
                "sem_observacao": [], # atividade sem campo observacao
            }

            STATUS_IGNORADOS = ("CONCLU", "CANCELA")

            print(f"PEC_TESTE_API: {len(lista_processos)} processo(s) para testar")

            for numero in lista_processos:
                try:
                    dados = obter_gigs_com_fase(client, numero)
                    if not dados:
                        print(f"PEC_TESTE_API: {numero} → sem dados GIGS")
                        continue

                    atividades = dados.get("atividadesgigs") or []
                    if not atividades:
                        print(f"PEC_TESTE_API: {numero} → lista atividadesgigs vazia")
                        continue

                    for ativ in atividades:
                        status   = (ativ.get("statusAtividade") or "").upper()
                        obs_raw  = (ativ.get("observacao") or "").strip()
                        dataprazo = ativ.get("dataPrazo") or ""

                        if filtrar_concluidos and any(s in status for s in STATUS_IGNORADOS):
                            continue

                        info = {
                            "numero": numero,
                            "observacao": obs_raw,
                            "status": status,
                            "dataPrazo": dataprazo,
                        }

                        if not obs_raw:
                            buckets["sem_observacao"].append(info)
                            print(f"PEC_TESTE_API: {numero} → sem observacao (status={status})")
                            continue

                        acoes = determinar_acoes_por_observacao(obs_raw)

                        if not acoes:
                            buckets["sem_acao"].append(info)
                            print(f"PEC_TESTE_API: {numero} → obs={obs_raw!r} → SEM REGRA")
                            continue

                        # determinar_acoes_por_observacao retorna lista/tupla ou callable(s)
                        first = acoes[0] if isinstance(acoes, (list, tuple)) and acoes else acoes
                        acaonome = _resolver_acaonome(first)
                        bucket   = _acaonome_para_bucket_pec(acaonome)
                        buckets[bucket].append(info)
                        print(
                            f"PEC_TESTE_API: {numero} → bucket={bucket} "
                            f"acao={acaonome} status={status} "
                            f"dataPrazo={dataprazo} obs={obs_raw[:80]}"
                        )

                except Exception as e:
                    print(f"PEC_TESTE_API: ERRO em {numero}: {e}")
                    continue

            print("\nPEC_TESTE_API: ── RESUMO ──")
            total = sum(len(v) for v in buckets.values())
            for nome, itens in buckets.items():
                if not itens:
                    continue
                print(f"  {nome.upper():15s} {len(itens):>3} atividades")
                for proc in itens[:3]:
                    obs_curta = proc["observacao"][:60]
                    print(f"    · {proc['numero']} {obs_curta}")
            print(f"  {'TOTAL':15s} {total:>3}")

            return buckets
        
        # 2. Indexar processo atual para obter observação
        processo_atual = indexar_processo_atual_gigs(driver)
        if not processo_atual:
            print("[PEC_INDIVIDUAL] ❌ Falha ao extrair dados do processo atual")
            return False
        
        _, observacao = processo_atual
        print(f"[PEC_INDIVIDUAL] Processo: {numero_processo} | Observação: {observacao}")
        
        # 3. Determinar ações baseadas na observação (AQUI, UMA VEZ)
        acoes = determinar_acoes_por_observacao(observacao)
        acao = acoes[0] if acoes else None  # Para compatibilidade com código antigo
        print(f"[PEC_INDIVIDUAL] Ações determinadas: {[a.__name__ if callable(a) else str(a) for a in acoes]}")
        
        # 4. Pular processos sem ação definida
        if acao is None:
            print(f"[PEC_INDIVIDUAL] ⏭️ Pulando processo (ação não definida)")
            return True  # Considera sucesso para não retry
        
        # 6. Preparar override de destinatário (se a observação contiver um nome após o comando)
        destinatarios_override = None
        try:
            import re
            # Padrão: 'pec dec Nome Sobrenome', 'pec edital Nome', 'pec idpj Nome'
            m = re.match(r'^(?:pec\s*(?:dec|edital|idpj)\b)\s+(.+)$', observacao.strip(), re.I)
            if m:
                nome_cand = m.group(1).strip()
                # Tomar até a primeira vírgula ou hífen ou parenteses
                nome_cand = re.split(r'[,-\(\\)]', nome_cand)[0].strip()
                # Remover títulos comuns
                nome_cand = re.sub(r'^(sr\.?|sra\.?|dr\.?|dra\.?|srta\.?|srta)\s+', '', nome_cand, flags=re.I).strip()
                # Validar tamanho mínimo
                if len(nome_cand) >= 3 and re.search('[A-Za-zÀ-ÖØ-öø-ÿ]', nome_cand):
                    destinatarios_override = {'nome': nome_cand}
                    print(f"[PEC_INDIVIDUAL][DEST_OVERRIDE] Nome extraído para override: '{nome_cand}'")
        except Exception as e_parse:
            print(f"[PEC_INDIVIDUAL][DEST_OVERRIDE][WARN] Falha ao tentar extrair nome da observação: {e_parse}")

        # 7. Executar ação específica (sem os parâmetros antigos que não usamos mais)
        # ✨ NOVO: Tentar obter driver_sisb do contexto global (se existir)
        driver_sisb = getattr(driver, '_driver_sisb_compartilhado', None)
        
        sucesso_acao = executar_acao_pec(
            driver,
            acao,
            numero_processo=numero_processo,
            observacao=observacao,
            debug=True,
            driver_sisb=driver_sisb
        )
        
        if sucesso_acao:
            print(f"[PEC_INDIVIDUAL] ✅ Ação executada com sucesso")
            return True
        else:
            print(f"[PEC_INDIVIDUAL] ❌ Falha na execução da ação '{acao}'")
            return False
        
    except Exception as e:
        print(f"[PEC_INDIVIDUAL] ❌ Erro no processamento: {e}")
        return False
