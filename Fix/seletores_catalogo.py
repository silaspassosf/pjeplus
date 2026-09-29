"""
Fix/seletores_catalogo.py - Fonte Canônica de Seletores e Ações Semânticas do PJePlus.

Implementa o catálogo centralizado de seletores por ação semântica, contexto e ambiente,
com suporte a:
- Vencedor registrado e invalidável em tempo de execução
- Encerramento imediato após sucesso (sem testar alternativas desnecessárias)
- Cadeia centralizada única de fallbacks
- Telemetria de sucessos, falhas e vencedores
- Erro contextualizado se toda a cadeia falhar
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from Fix import espera
from Fix.diagnostico_runtime import log_erro_estruturado

logger = logging.getLogger("Fix.seletores")


@dataclass
class SeletorRegistro:
    """Registro semântico de seletores para uma ação no DOM."""
    acao: str
    seletor_principal: str
    fallbacks: List[str] = field(default_factory=list)
    contexto: str = "geral"
    ambiente: str = "default"
    condicao_sucesso: str = "presente"  # 'presente', 'visivel', 'clicavel', 'habilitado'
    timeout: float = 3.0
    seletor_vencedor: Optional[str] = None
    data_ultima_confirmacao: Optional[str] = None
    quantidade_sucessos: int = 0
    quantidade_falhas: int = 0
    ultima_falha: Optional[str] = None
    versao_interface: str = "KZ"


class CatalogoSeletores:
    """Repositório de ações semânticas e orquestrador de vencedores/fallbacks."""

    def __init__(self):
        self._registros: Dict[Tuple[str, str, str], SeletorRegistro] = {}
        self._inicializar_padroes()

    def _chave(self, acao: str, contexto: str, ambiente: str) -> Tuple[str, str, str]:
        return (acao.lower().strip(), contexto.lower().strip(), ambiente.lower().strip())

    def registrar(self, registro: SeletorRegistro) -> None:
        """Registra ou atualiza uma ação semântica no catálogo."""
        chave = self._chave(registro.acao, registro.contexto, registro.ambiente)
        self._registros[chave] = registro

    def obter(self, acao: str, contexto: str = "geral", ambiente: str = "default") -> Optional[SeletorRegistro]:
        """Obtém registro por ação + contexto + ambiente, com fallback para contexto 'geral'."""
        chave = self._chave(acao, contexto, ambiente)
        if chave in self._registros:
            return self._registros[chave]
        chave_geral = self._chave(acao, "geral", ambiente)
        return self._registros.get(chave_geral)

    def invalidar_vencedor(self, acao: str, contexto: str = "geral", ambiente: str = "default") -> None:
        """Invalida o vencedor quando o DOM muda ou o seletor falha."""
        reg = self.obter(acao, contexto, ambiente)
        if reg:
            reg.seletor_vencedor = None

    def executar_busca(
        self,
        driver: Any,
        acao: str,
        contexto: str = "geral",
        ambiente: str = "default",
        timeout: Optional[float] = None,
        processo: str = "",
    ) -> Optional[Any]:
        """
        Executa a busca semântica seguindo o algoritmo obrigatório:
        1. Consulta o vencedor registrado.
        2. Testa primeiro somente o vencedor.
        3. Se sucesso, encerra imediatamente.
        4. Se falhar, invalida o vencedor para esta execução.
        5. Executa cadeia única de fallbacks.
        6. Encerra no primeiro sucesso e registra novo vencedor.
        7. Não testa seletores restantes após o sucesso.
        8. Se todos falharem, emite erro estruturado padronizado.
        """
        reg = self.obter(acao, contexto, ambiente)
        if not reg:
            log_erro_estruturado(
                codigo="SELETOR-ACAO-NAO-REGISTRADA",
                fluxo=contexto,
                modulo="Fix.seletores_catalogo",
                funcao="executar_busca",
                processo=processo,
                etapa=contexto,
                acao=acao,
                seletor="",
                excecao="KeyError",
                causa=f"Ação semântica '{acao}' não catalogada para contexto '{contexto}'",
                retry=False,
            )
            return None

        teto = timeout if timeout is not None else reg.timeout

        def _testar(sel: str, t_teto: float) -> Optional[Any]:
            try:
                if reg.condicao_sucesso == "clicavel":
                    from Fix.core import wait_for_clickable
                    return wait_for_clickable(driver, sel, timeout=int(max(1, t_teto)))
                elif reg.condicao_sucesso == "habilitado":
                    if espera.ate_habilitar(driver, sel, teto=t_teto):
                        return espera.elemento(driver, sel, teto=1)
                    return None
                elif reg.condicao_sucesso == "visivel":
                    return espera.elemento(driver, sel, teto=t_teto, visivel=True)
                else:  # 'presente'
                    return espera.elemento(driver, sel, teto=t_teto, visivel=False)
            except Exception:
                return None

        # 1 & 2. Testar primeiro somente o vencedor registrado se houver
        if reg.seletor_vencedor:
            el_vencedor = _testar(reg.seletor_vencedor, min(teto, 2.0))
            if el_vencedor:
                reg.quantidade_sucessos += 1
                reg.data_ultima_confirmacao = datetime.now().isoformat()
                return el_vencedor
            # 4. Falha do vencedor -> invalidar para esta execução
            reg.quantidade_falhas += 1
            reg.ultima_falha = f"{reg.seletor_vencedor} às {datetime.now().isoformat()}"
            vencedor_antigo = reg.seletor_vencedor
            reg.seletor_vencedor = None
        else:
            vencedor_antigo = None

        # 5. Executar cadeia única de fallbacks (sem testar o que acabou de falhar)
        cadeia = [reg.seletor_principal] + [s for s in reg.fallbacks if s != reg.seletor_principal]
        if vencedor_antigo in cadeia:
            cadeia.remove(vencedor_antigo)

        for sel in cadeia:
            el = _testar(sel, teto)
            if el:
                # 6 & 7. Encerra no primeiro sucesso e registra novo vencedor
                reg.seletor_vencedor = sel
                reg.quantidade_sucessos += 1
                reg.data_ultima_confirmacao = datetime.now().isoformat()
                return el

        # 8. Se todos falharem, log estruturado canônico
        log_erro_estruturado(
            codigo=f"{acao.upper()}-ELEMENTO-NAO-ENCONTRADO",
            fluxo=contexto,
            modulo="Fix.seletores_catalogo",
            funcao="executar_busca",
            processo=processo,
            etapa=contexto,
            acao=acao,
            seletor=reg.seletor_principal,
            excecao="TimeoutError",
            causa=f"Todos os seletores da cadeia falharam ({len(cadeia) + (1 if vencedor_antigo else 0)} tentativas)",
            retry=False,
            consequencia="Ação semântica interrompida por falta de elemento no DOM",
        )
        return None

    def _inicializar_padroes(self) -> None:
        """Registra os seletores canônicos mapeados em Mandado, P2B e PEC."""
        # 1. Mandado: menu de tarefas
        self.registrar(SeletorRegistro(
            acao="abrir_menu_tarefa",
            seletor_principal="#botao-menu",
            fallbacks=['button[aria-label="Abrir menu de tarefas"]', 'button#botao-menu'],
            contexto="mandado",
            condicao_sucesso="presente",
            timeout=2.0,
        ))

        # 2. Mandado: botão Expedientes
        self.registrar(SeletorRegistro(
            acao="abrir_expedientes",
            seletor_principal='button[aria-label="Expedientes"]',
            fallbacks=['button#btnExpedientes', 'a[aria-label="Expedientes"]'],
            contexto="mandado",
            condicao_sucesso="presente",
            timeout=3.0,
        ))

        # 3. Mandado: botão Fechar Expedientes
        self.registrar(SeletorRegistro(
            acao="fechar_expedientes",
            seletor_principal='button[aria-label="Fechar Expedientes"]',
            fallbacks=['button#btnFecharExpedientes'],
            contexto="mandado",
            condicao_sucesso="clicavel",
            timeout=5.0,
        ))

        # 4. Geral: confirmação em diálogo (botão 'Sim')
        self.registrar(SeletorRegistro(
            acao="confirmar_dialogo_sim",
            seletor_principal="//mat-dialog-container//button[.//span[normalize-space(.)='Sim'] or normalize-space(.)='Sim']",
            fallbacks=[
                "//div[contains(@class,'cdk-overlay-pane')]//button[.//span[normalize-space(.)='Sim'] or normalize-space(.)='Sim']",
                "//button[.//span[normalize-space(.)='Sim'] or normalize-space(.)='Sim']",
            ],
            contexto="geral",
            condicao_sucesso="presente",
            timeout=2.0,
        ))

        # 5. Geral: Timeline
        self.registrar(SeletorRegistro(
            acao="abrir_timeline",
            seletor_principal="li.tl-item-container",
            fallbacks=["div.tl-item-container", ".timeline-item"],
            contexto="geral",
            condicao_sucesso="presente",
            timeout=3.0,
        ))

        # 6. Atos / Minutas: Filtro de Modelo
        self.registrar(SeletorRegistro(
            acao="filtro_modelo",
            seletor_principal="input#inputFiltro",
            fallbacks=['input[placeholder*="Filtrar"]', 'input[aria-label*="Filtrar"]'],
            contexto="atos",
            condicao_sucesso="presente",
            timeout=5.0,
        ))

        # 7. Atos / Minutas: Nodo Filtrado
        self.registrar(SeletorRegistro(
            acao="nodo_modelo_filtrado",
            seletor_principal=".nodo-filtrado",
            fallbacks=['mat-tree-node.nodo-filtrado', 'mat-tree-node'],
            contexto="atos",
            condicao_sucesso="presente",
            timeout=15.0,
        ))

        # 8. Atos / Minutas: Diálogo de Visualização de Modelo
        self.registrar(SeletorRegistro(
            acao="dialogo_visualizar_modelo",
            seletor_principal="pje-dialogo-visualizar-modelo",
            fallbacks=['mat-dialog-container:has(pje-dialogo-visualizar-modelo)'],
            contexto="atos",
            condicao_sucesso="presente",
            timeout=15.0,
        ))

        # 9. Atos / Minutas: Botão Inserir Modelo
        self.registrar(SeletorRegistro(
            acao="botao_inserir_modelo",
            seletor_principal='button[aria-label="Inserir modelo de documento"]',
            fallbacks=[
                'pje-dialogo-visualizar-modelo > div > div.div-preview-botoes > div.div-botao-inserir > button',
                'pje-dialogo-visualizar-modelo button',
            ],
            contexto="atos",
            condicao_sucesso="clicavel",
            timeout=10.0,
        ))

        # 10. Atos / Minutas: Editor de Texto
        self.registrar(SeletorRegistro(
            acao="editor_minuta",
            seletor_principal='div[class*="area-conteudo"][contenteditable="true"]',
            fallbacks=[
                '.ck-editor__editable[contenteditable="true"]',
                'div.ck-content[contenteditable="true"]',
                '[contenteditable="true"]',
            ],
            contexto="atos",
            condicao_sucesso="presente",
            timeout=5.0,
        ))

        # 11. PEC: Prazo de Expediente / Destinatário
        self.registrar(SeletorRegistro(
            acao="campo_prazo_destinatario",
            seletor_principal='input[aria-label="Prazo"]',
            fallbacks=[
                'input[formcontrolname="prazo"]',
                'input#inputPrazo',
                'input[name*="prazo"]',
            ],
            contexto="pec",
            condicao_sucesso="presente",
            timeout=3.0,
        ))

        self.registrar(SeletorRegistro(
            acao="campo_prazo_dias_uteis",
            seletor_principal='input[aria-label="Prazo em dias úteis"]',
            fallbacks=[
                'input[placeholder*="dias úteis"]',
                'mat-form-field input[type="number"]',
                'input[formcontrolname="prazo"]',
            ],
            contexto="pec",
            condicao_sucesso="presente",
            timeout=3.0,
        ))

        self.registrar(SeletorRegistro(
            acao="campo_prazo_data_certa",
            seletor_principal='input[aria-label="Prazo em data certa"]',
            fallbacks=[
                'input[placeholder*="data"]',
                'input[type="date"]',
            ],
            contexto="pec",
            condicao_sucesso="presente",
            timeout=3.0,
        ))

        self.registrar(SeletorRegistro(
            acao="campo_prazo_dias_corridos",
            seletor_principal='input[aria-label="Prazo em dias úteis"]',
            fallbacks=[
                'input[placeholder*="dias"]',
                'mat-form-field input[type="number"]',
                'input[formcontrolname="prazo"]',
            ],
            contexto="pec",
            condicao_sucesso="presente",
            timeout=3.0,
        ))

        # 12. PEC / Juntada: Salvar Documento
        self.registrar(SeletorRegistro(
            acao="salvar_documento_anexo",
            seletor_principal='button[aria-label="Salvar"]',
            fallbacks=['button.mat-primary[aria-label="Salvar"]'],
            contexto="pec_anexos",
            condicao_sucesso="clicavel",
            timeout=5.0,
        ))

        # 13. PEC / Juntada: Assinar Documento
        self.registrar(SeletorRegistro(
            acao="assinar_documento_anexo",
            seletor_principal='button[aria-label="Assinar documento e juntar ao processo"]',
            fallbacks=['button[aria-label*="Assinar"]'],
            contexto="pec_anexos",
            condicao_sucesso="habilitado",
            timeout=3.0,
        ))


# Instância global canônica
_catalogo_global = CatalogoSeletores()


def obter_catalogo() -> CatalogoSeletores:
    """Retorna a instância global do catálogo de seletores."""
    return _catalogo_global


def buscar_elemento_por_acao(
    driver: Any,
    acao: str,
    contexto: str = "geral",
    ambiente: str = "default",
    timeout: Optional[float] = None,
    processo: str = "",
) -> Optional[Any]:
    """Busca elemento no DOM via ação semântica no catálogo central."""
    return _catalogo_global.executar_busca(
        driver=driver,
        acao=acao,
        contexto=contexto,
        ambiente=ambiente,
        timeout=timeout,
        processo=processo,
    )


def clicar_por_acao(
    driver: Any,
    acao: str,
    contexto: str = "geral",
    ambiente: str = "default",
    timeout: Optional[float] = None,
    processo: str = "",
) -> bool:
    """Localiza e clica no elemento associado à ação semântica."""
    el = buscar_elemento_por_acao(
        driver=driver,
        acao=acao,
        contexto=contexto,
        ambiente=ambiente,
        timeout=timeout,
        processo=processo,
    )
    if not el:
        return False
    try:
        from Fix.core import safe_click_no_scroll
        safe_click_no_scroll(driver, el)
        return True
    except Exception as e:
        logger.error("Falha ao clicar na ação '%s': %s", acao, e)
        return False
