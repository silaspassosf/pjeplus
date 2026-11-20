import logging
logger = logging.getLogger(__name__)

# Evitar modificações em arquivos não explicitamente mencionados.
# nao é neceasário varrer o codigo todo para cada edição pedida

import json
import os
import re
import sys
import time
import unicodedata
from Fix.utils import remover_acentos, normalizar_texto
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional


from core.rule_registry import RuleRegistry

from Fix.utils import verificar_e_tratar_acesso_negado_global, handle_exception_with_recovery
from Fix.core import preencher_campo, aguardar_renderizacao_nativa
from Fix.extracao import salvar_destinatarios_cache
from Fix.abas import validar_conexao_driver
from Fix import espera
from Fix.extracao import criar_gigs, criar_lembrete_posit
from Prazo.p2b_core import checar_prox
from .apoio_fluxos import (
    ato_judicial,
    ato_meios,
    ato_pesquisas,
    ato_crda,
    ato_crte,
    ato_bloq,
    ato_idpj,
    ato_termoE,
    ato_termoS,
    ato_edital,
    pec_idpj,
    mov_arquivar,
    ato_meiosub,
)


def _normalizar_texto_match(valor: str) -> str:
    if not valor:
        return ''
    txt = normalizar_texto(str(valor))
    txt = re.sub(r'[^a-z0-9\s]', ' ', txt)
    txt = re.sub(r'\s+', ' ', txt).strip()
    return txt


def _carregar_reus_dadosatuais(debug: bool = False) -> List[Dict[str, str]]:
    """Carrega reclamadas/reclamados de dadosatuais.json para cruzamento de destinatários."""
    try:
        caminho = os.path.join(os.getcwd(), 'dadosatuais.json')
        if not os.path.exists(caminho):
            if debug:
                logger.info('[ARGOS][IDPJ][DEST] dadosatuais.json não encontrado')
            return []

        with open(caminho, 'r', encoding='utf-8') as f:
            dados = json.load(f)

        reus = dados.get('reu', []) or []
        resultado = []
        for item in reus:
            nome = (item or {}).get('nome', '')
            cpfcnpj = (item or {}).get('cpfcnpj', '')
            if nome:
                resultado.append({'nome': nome, 'cpfcnpj': cpfcnpj})

        if debug:
            logger.info(f'[ARGOS][IDPJ][DEST] Reús carregados de dadosatuais.json: {len(resultado)}')
        return resultado

    except Exception as e:
        if debug:
            logger.info(f'[ARGOS][IDPJ][DEST] Falha ao carregar dadosatuais.json: {e}')
        return []


def _identificar_destinatarios_idpj(texto_documento: str, debug: bool = False) -> List[Dict[str, str]]:
    """Identifica destinatários da decisão IDPJ cruzando nomes no texto com dadosatuais.json."""
    if not texto_documento:
        return []

    texto_norm = _normalizar_texto_match(texto_documento)
    reus = _carregar_reus_dadosatuais(debug=debug)
    if not reus:
        return []

    # Isso evita detectar nomes que aparecem no cabeçalho do documento.
    contexto_focal = ''

    try:
        m2 = re.search(r'providencie a secretaria.*?(?:\n\s*\n|$)', texto_norm, flags=re.IGNORECASE | re.DOTALL)
        if m2:
            contexto_focal = m2.group(0)
    except Exception:
        contexto_focal = ''

    if not contexto_focal:
        padroes_focais = [
            r'incluir os socios .*? no polo passivo',
            r'inclua se .*? no polo passivo',
            r'incluir os socios .*? em obediencia a ordem',
        ]

        for padrao in padroes_focais:
            try:
                m = re.search(padrao, texto_norm, flags=re.IGNORECASE)
                if m:
                    contexto_focal = m.group(0)
                    break
            except Exception:
                continue

    if debug:
        if contexto_focal:
            logger.info('[ARGOS][IDPJ][DEST] Contexto focal de sócios identificado na decisão')
        else:
            logger.info('[ARGOS][IDPJ][DEST] Contexto focal não encontrado, usando texto completo')

    texto_base_busca = contexto_focal if contexto_focal else texto_norm

    destinatarios = []
    nomes_match = []

    for reu in reus:
        nome = reu.get('nome', '')
        cpfcnpj = reu.get('cpfcnpj', '')
        nome_norm = _normalizar_texto_match(nome)

        if not nome_norm or len(nome_norm) < 5:
            continue

        if nome_norm in texto_base_busca:
            destinatarios.append({
                'nome': nome,
                'cpfcnpj': cpfcnpj,
                'tipo': 'reu',
            })
            nomes_match.append(nome)

    if not destinatarios and contexto_focal:
        for reu in reus:
            nome = reu.get('nome', '')
            cpfcnpj = reu.get('cpfcnpj', '')
            nome_norm = _normalizar_texto_match(nome)

            if not nome_norm or len(nome_norm) < 5:
                continue

            if nome_norm in texto_norm:
                destinatarios.append({
                    'nome': nome,
                    'cpfcnpj': cpfcnpj,
                    'tipo': 'reu',
                })
                nomes_match.append(nome)

        if debug and destinatarios:
            logger.info('[ARGOS][IDPJ][DEST] Fallback no texto completo aplicado')

    if debug:
        logger.info(f'[ARGOS][IDPJ][DEST] Destinatários IDPJ reconhecidos: {len(destinatarios)}')
        if nomes_match:
            logger.info(f"[ARGOS][IDPJ][DEST] Nomes: {', '.join(nomes_match[:6])}")

    return destinatarios

def estrategia_defiro_instauracao(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=False):
    """Regra IDPJ por decisão; SISBAJUD afeta apenas lembrete."""
    txt_lower = texto_documento.lower() if texto_documento else ''
    tipo_norm = normalizar_texto(str(tipo_documento or ''))
    if 'decisao' not in tipo_norm:
        return False
    normalized = normalizar_texto(texto_documento) if texto_documento else ''

    palavras_idpj = [
        'defiro a instauração',
        'defiro a instauracao',
        'deferir a instauração',
        'deferir a instauracao',
        'determino que seja incluído',
        'determino que seja incluida',
        'incidente de desconsideração',
        'incidente de desconsideracao',
        'desconsideração da personalidade jurídica',
        'desconsideracao da personalidade juridica',
        'desconsideração inversa',
        'desconsideracao inversa',
        '855-a',
        'idpj',
        'inclua-se no polo passivo',
        'sócio retirante',
        'socio retirante'
    ]

    idpj_detectado = False
    palavra_encontrada = None
    for palavra in palavras_idpj:
        if palavra in txt_lower or palavra in normalized:
            idpj_detectado = True
            palavra_encontrada = palavra
            break

    if idpj_detectado:
        def _persistir_destinatarios_idpj() -> None:
            """Persiste destinatários apenas quando a regra IDPJ for efetivamente aplicada."""
            try:
                destinatarios_idpj = _identificar_destinatarios_idpj(texto_documento, debug=debug)
                if destinatarios_idpj:
                    salvar_destinatarios_cache('ATUAL', destinatarios_idpj, origem='argos_idpj_decisao')
                    if debug:
                        logger.info(f'[ARGOS][IDPJ][DEST] Cache atualizado com {len(destinatarios_idpj)} destinatário(s)')
                elif debug:
                    logger.info('[ARGOS][IDPJ][DEST] Nenhum destinatário IDPJ reconhecido no texto')
            except Exception as dest_err:
                if debug:
                    logger.info(f'[ARGOS][IDPJ][DEST] Falha ao salvar destinatários IDPJ: {dest_err}')

        if debug:
            logger.info('[ARGOS][REGRAS] Regra IDPJ reconhecida por decisão')

        _persistir_destinatarios_idpj()

        try:
            from atos.anexos_sigilo import aguardar_visibilidade_concluida
            aguardar_visibilidade_concluida(driver, timeout=20.0, estabilidade=0.4, log=True)
        except Exception as e_vis:
            logger.warning(f'[ARGOS][IDPJ] barreira pre-GIGS visibilidade: {type(e_vis).__name__}: {e_vis}')

        # Sequência obrigatória no fluxo IDPJ:
        #   1) GIGS de bloqueio (se SISBAJUD positivo ou valores bloqueados na decisão):
        tem_bloqueio_decisao = any(termo in texto_documento.lower() for termo in [
            'valores bloqueados', 'bloqueio positivo', 'bloqueio de valores positivo', 'saldo bloqueado'
        ])
        if resultado_sisbajud == 'positivo' or tem_bloqueio_decisao:
            logger.info('[ARGOS][REGRAS] Bloqueio identificado (SISBAJUD=%s, decisao_bloq=%s): criando GIGS de bloqueio', resultado_sisbajud, tem_bloqueio_decisao)
            obs_bloqueio = 'BLOQUEIO - processar após IDPJ'
            gigs_bloq_ok = False
            for tentativa in range(1, 4):
                try:
                    logger.info(f'[ARGOS][REGRAS] Criando GIGS de bloqueio "{obs_bloqueio}" (tentativa {tentativa}/3)')
                    gigs_bloq_ok = bool(criar_gigs(driver, '', '', obs_bloqueio))
                except Exception as e:
                    logger.warning(f'[ARGOS][REGRAS][WARN] GIGS de bloqueio tentativa {tentativa}/3 falhou: {type(e).__name__}: {e}')
                if gigs_bloq_ok:
                    logger.info('[ARGOS][REGRAS] GIGS de bloqueio confirmado com sucesso')
                    break
                logger.warning(f'[ARGOS][REGRAS][WARN] GIGS de bloqueio nao confirmado (tentativa {tentativa}/3) — reassentando')
                espera.assentar(driver, 1.2, motivo='[GIGS_BLOQ] retry apos falha')

            if not gigs_bloq_ok:
                logger.error('[ARGOS][REGRAS][ERRO] GIGS de bloqueio nao criado apos 3 tentativas — prosseguindo com GIGS e pec_idpj')
            espera.assentar(driver, 1.0, motivo='[IDPJ] barreira pos-gigs-bloqueio')
        elif debug:
            logger.info('[ARGOS][REGRAS] SISBAJUD não positivo: sem GIGS de bloqueio, seguindo com GIGS xs carta e pec_idpj')

        try:
            espera.ate_sumir(driver, 'textarea[formcontrolname="observacao"]', teto=4)
            espera.ate_sumir(driver, '.cdk-overlay-backdrop-showing', teto=4)
        except Exception as e:
            logger.warning(f'[ARGOS][IDPJ] barreira pos-gigs-bloqueio: {type(e).__name__}: {e}')

        gigs_ok = False
        for tentativa in range(1, 4):
            try:
                logger.info(f'[ARGOS][IDPJ] Passo 2/3: criando GIGS xs carta (tentativa {tentativa}/3)')
                gigs_ok = bool(criar_gigs(driver, 7, '', 'xs carta'))
            except Exception as e:
                logger.warning(f'[ARGOS][REGRAS][WARN] GIGS xs carta tentativa {tentativa}/3 falhou: {type(e).__name__}: {e}')
            if gigs_ok:
                logger.info('[ARGOS][IDPJ] GIGS xs carta confirmado (formulário fechado)')
                break
            espera.assentar(driver, 1.5, motivo='[IDPJ] retry GIGS xs carta')
        if not gigs_ok:
            logger.error('[ARGOS][IDPJ][ERRO] GIGS xs carta nao confirmado apos 3 tentativas — prosseguindo com pec_idpj')

        try:
            espera.ate_sumir(driver, 'textarea[formcontrolname="observacao"]', teto=6)
            aguardar_renderizacao_nativa(driver, '.cdk-overlay-backdrop-showing', modo='sumir', timeout=5)
        except Exception as e:
            logger.warning(f'[ARGOS][IDPJ] barreira pos-GIGS: {type(e).__name__}: {e}')

        try:
            logger.info('[ARGOS][IDPJ] Passo 3/3: executando pec_idpj (GIGS xs carta já criado no passo 2)')
            res_idpj = pec_idpj(driver, debug=debug, gigs_extra=False)
            if isinstance(res_idpj, tuple) and not res_idpj[0]:
                return False
            if res_idpj is False:
                return False
        except Exception as e:
            logger.error(f'[ARGOS][REGRAS][ERRO] Falha ao executar pec_idpj: {e}')
            return False
        return True
    return False

def _executar_ato_seguro(driver: Any, fn_ato: Callable, nome_ato: str, debug: bool = False) -> bool:
    """Executa ato judicial com medição de tempo e tratamento seguro de exceções."""
    t0 = time.time()
    try:
        try:
            from atos.anexos_sigilo import aguardar_visibilidade_concluida
            aguardar_visibilidade_concluida(driver, timeout=15.0, estabilidade=0.3, log=debug)
        except Exception:
            pass
        res = fn_ato(driver, debug=debug)
        duracao = time.time() - t0
        sucesso = False
        if isinstance(res, tuple):
            sucesso = bool(res[0])
        elif isinstance(res, bool):
            sucesso = res
        elif res is not None:
            sucesso = bool(res)
        else:
            sucesso = True

        if not sucesso:
            logger.error('[ARGOS][REGRAS] %s retornou falha (%.2fs)', nome_ato, duracao)
            return False

        if debug:
            logger.debug('[ARGOS][REGRAS] %s finalizado com sucesso em %.2fs', nome_ato, duracao)
        return True
    except Exception as e:
        logger.error('[ARGOS][REGRAS] %s falhou com exceção: %s', nome_ato, e)
        return False


def decidir_ato_despacho_argos(resultado_sisbajud: str, tem_anexos_sigilosos: bool) -> str:
    """Regra de negócio pura: decide o nome do ato judicial para despacho com ARGOS."""
    if resultado_sisbajud == 'positivo':
        return 'ato_bloq'
    elif resultado_sisbajud == 'negativo':
        return 'ato_termoS' if tem_anexos_sigilosos else 'ato_meios'
    return 'ato_meios'


def estrategia_despacho_argos(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=False):
    """Prioridade: documento com palavra 'ARGOS'"""
    tipo_norm = normalizar_texto(str(tipo_documento or ''))
    if 'despacho' not in tipo_norm:
        return False

    if not (texto_documento and 'argos' in texto_documento.lower()):
        return False

    if debug:
        logger.debug('[ARGOS][REGRAS] Despacho com ARGOS detectado - aplicando regras')

    tem_sigilosos = any(v == 'sim' for v in (sigilo_anexos or {}).values())
    nome_ato = decidir_ato_despacho_argos(resultado_sisbajud, tem_sigilosos)

    atos_map = {
        'ato_bloq': ato_bloq,
        'ato_termoS': ato_termoS,
        'ato_meios': ato_meios,
    }
    fn_ato = atos_map.get(nome_ato, ato_meios)

    if debug:
        logger.debug('[ARGOS][REGRAS] Ação definida: %s', nome_ato)

    return _executar_ato_seguro(driver, fn_ato, nome_ato, debug=debug)


def estrategia_infojud(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=False):
    """Despacho com 'Realize-se a pesquisa INFOJUD'"""
    tipo_norm = normalizar_texto(str(tipo_documento or ''))
    if 'despacho' not in tipo_norm:
        return False

    if not texto_documento:
        return False

    txt_lower = texto_documento.lower()
    normalized = unicodedata.normalize('NFD', texto_documento).encode('ascii', 'ignore').decode('ascii').lower()

    regras_infojud = [
        'realize-se a pesquisa infojud',
        'realize se a pesquisa infojud',
        'realize-se a pesquisa do infojud',
        'realize se a pesquisa do infojud',
        'realização de pesquisa infojud',
        'realizacao de pesquisa infojud',
        'pesquisa infojud',
        'decred, dimob e e-financeira',
        'através do sistema argos',
        'atraves do sistema argos'
    ]

    if not any(r in txt_lower or r in normalized for r in regras_infojud):
        return False

    if debug:
        logger.debug('[ARGOS][REGRAS] Regra despacho+infojud reconhecida')

    tem_sigilosos = any(v == 'sim' for v in (sigilo_anexos or {}).values())
    fn_ato, nome_ato = (ato_termoS, 'ato_termoS') if tem_sigilosos else (ato_meios, 'ato_meios')
    return _executar_ato_seguro(driver, fn_ato, nome_ato, debug=debug)


def estrategia_decisao_manifestar(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=False):
    """Decisão com 'devendo se manifestar'"""
    tipo_norm = normalizar_texto(str(tipo_documento or ''))
    if 'decisao' not in tipo_norm:
        return False

    trechos_checar_prox = ['devendo se manifestar', 'nada a deferir', 'comunique-se por edital', 'mantenho o despacho']
    for trecho in trechos_checar_prox:
        if texto_documento and trecho in texto_documento.lower():
            if debug:
                logger.info(f'[ARGOS][REGRAS] Texto "{trecho}" detectado, chamando checar_prox...')
            try:
                checar_prox(driver, None, None, None, texto_documento)
            except Exception as e:
                if debug:
                    logger.info(f'[ARGOS][REGRAS][ERRO] checar_prox falhou: {e}')
            return True
    return False


def estrategia_tendo_em_vista_que(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=False):
    """Decisão com 'tendo em vista que' — analisa número de reclamadas e escolhe ação."""
    tipo_norm = normalizar_texto(str(tipo_documento or ''))
    if 'decisao' in tipo_norm and texto_documento:
        txt_lower = texto_documento.lower()
        normalized = unicodedata.normalize('NFD', texto_documento).encode('ascii', 'ignore').decode('ascii').lower()

        tem_tendo_em_vista = ('tendo em vista que' in txt_lower or
                             'tendo em vista que' in normalized)

        if not tem_tendo_em_vista:
            return False
        if debug:
            logger.info('[ARGOS][REGRAS] Regra decisao+tendo_em_vista reconhecida')
        try:
            from .apoio_fluxos import _extrair_id_processo_da_url, _criar_api_client_local
            id_proc = _extrair_id_processo_da_url(driver)
            num_reclamadas = 0
            if id_proc:
                client = _criar_api_client_local(driver)
                if client:
                    partes_raw = client.partes(id_proc) or {}
                    passivos = partes_raw.get('PASSIVO') or []
                    num_reclamadas = len(passivos)
                    if debug:
                        logger.info('[ARGOS][REGRAS] API partes: %d reclamada(s)', num_reclamadas)
        except Exception as e:
            if debug:
                logger.error(f'[ARGOS][REGRAS][ERRO] Falha ao consultar partes via API: {e}')
            num_reclamadas = 0
        if num_reclamadas == 1:
            if resultado_sisbajud != 'positivo' and all(v == 'nao' for v in (sigilo_anexos or {}).values()):
                if debug:
                    logger.info('[ARGOS][REGRAS] Chamando ato_meios (1 reclamada, SISBAJUD negativo/indefinido, sem sigilo)')
                return _executar_ato_seguro(driver, ato_meios, 'ato_meios', debug=debug)
            elif resultado_sisbajud != 'positivo' and any(v == 'sim' for v in (sigilo_anexos or {}).values()):
                if debug:
                    logger.info('[ARGOS][REGRAS] Chamando ato_termoE (1 reclamada, SISBAJUD negativo, com sigilo)')
                return _executar_ato_seguro(driver, ato_termoE, 'ato_termoE', debug=debug)
            else:
                if debug:
                    logger.info('[ARGOS][REGRAS] Chamando ato_bloq (1 reclamada, SISBAJUD positivo/indefinido)')
                return _executar_ato_seguro(driver, ato_bloq, 'ato_bloq', debug=debug)
        else:
            if resultado_sisbajud != 'positivo':
                if debug:
                    logger.info('[ARGOS][REGRAS] Chamando ato_meiosub (multiplas reclamadas, SISBAJUD negativo/indefinido)')
                return _executar_ato_seguro(driver, ato_meiosub, 'ato_meiosub', debug=debug)
            else:
                if debug:
                    logger.info('[ARGOS][REGRAS] Chamando ato_bloq (multiplas reclamadas, SISBAJUD positivo/indefinido)')
                return _executar_ato_seguro(driver, ato_bloq, 'ato_bloq', debug=debug)
        return False
    return False


registry_argos = RuleRegistry("argos", ["tendo_vista", "idpj", "manifestar", "despacho_argos", "infojud"])

registry_argos.register(r'defiro a instaura[cç][aã]o|desconsidera[cç][aã]o|idpj|inclua.se no polo passivo|s[óo]cio retirante',
                        'idpj', None)
registry_argos.register(r'tendo em vista que', 'tendo_vista', None)
registry_argos.register(r'devendo se manifestar|nada a deferir', 'manifestar', None)
registry_argos.register(r'argos', 'despacho_argos', None)
registry_argos.register(r'realize.se a pesquisa infojud|pesquisa infojud|atrav[ée]s do sistema argos',
                        'infojud', None)

ESTRATEGIAS_ARGOS = [
    ("decisao+tendo_em_vista", estrategia_tendo_em_vista_que),
    ("IDPJ (instauração/855-A/desconsideração)", estrategia_defiro_instauracao),
    ("despacho+argos", estrategia_despacho_argos),
    ("despacho+infojud", estrategia_infojud),
    ("decisao+manifestar", estrategia_decisao_manifestar),
]

ESTRATEGIAS_ARGOS_DECISAO = [
    ("decisao+tendo_em_vista", estrategia_tendo_em_vista_que),
    ("IDPJ (instauração/855-A/desconsideração)", estrategia_defiro_instauracao),
    ("decisao+manifestar", estrategia_decisao_manifestar),
]

ESTRATEGIAS_ARGOS_DESPACHO = [
    ("despacho+argos", estrategia_despacho_argos),
    ("despacho+infojud", estrategia_infojud),
]


def aplicar_regras_argos(
    driver: Any,
    resultado_sisbajud: Dict[str, str],
    sigilo_anexos: Dict[str, str],
    tipo_documento: str,
    texto_documento: str,
    debug: bool = False
) -> bool:
    """Aplica regras de negócio via Strategy Pattern."""
    if not texto_documento:
        return False

    tipo_norm = normalizar_texto(str(tipo_documento or ''))
    if 'decisao' in tipo_norm:
        estrategias_em_uso = ESTRATEGIAS_ARGOS_DECISAO
    elif 'despacho' in tipo_norm:
        estrategias_em_uso = ESTRATEGIAS_ARGOS_DESPACHO
    else:
        estrategias_em_uso = ESTRATEGIAS_ARGOS

    if debug:
        try:
            raw_snippet = texto_documento[:1200].replace('\n', ' ')
        except Exception:
            raw_snippet = str(texto_documento)[:1200]
        normalized_snippet = remover_acentos(texto_documento)[:1200] if texto_documento else ''

    if texto_documento:
        registry_bucket, _ = registry_argos.match(texto_documento)
        if debug:
            if registry_bucket:
                logger.info(f'[ARGOS][REGRAS][REGISTRY] Text match: bucket={registry_bucket}')
            else:
                logger.info(f'[ARGOS][REGRAS][REGISTRY] No text pattern matched')

    # ===== TENTAR CADA ESTRATÉGIA EM ORDEM =====
    inicio_aplicacao = time.time()
    regra_aplicada = False
    for nome_estrategia, funcao_estrategia in estrategias_em_uso:
        try:
            if debug:
                inicio_estrategia = time.time()
            if funcao_estrategia(driver, resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug):
                regra_aplicada = True
                if debug:
                    fim_estrategia = time.time()
                    logger.info(f'[ARGOS][REGRAS] Estrategia "{nome_estrategia}" aplicada em {fim_estrategia - inicio_estrategia:.2f}s')
                    logger.info(f'[ARGOS][REGRAS] Tempo total ate aplicar regra: {fim_estrategia - inicio_aplicacao:.2f}s')
                break
            if debug:
                fim_estrategia = time.time()
                logger.info(f'[ARGOS][REGRAS] Estrategia "{nome_estrategia}" sem aplicacao ({fim_estrategia - inicio_estrategia:.2f}s)')
        except Exception as e:
            if debug:
                logger.error(f'[ARGOS][REGRAS][ERRO] Estrategia "{nome_estrategia}" falhou: {str(e)[:60]}')
            continue

    if not regra_aplicada and debug:
        fim_aplicacao = time.time()
        logger.info(f'[ARGOS][REGRAS] Nenhuma regra aplicou ({fim_aplicacao - inicio_aplicacao:.2f}s)')
    return regra_aplicada

