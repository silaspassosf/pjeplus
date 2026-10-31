"""
Testes unitários para o módulo de Lembretes (post-its) no PJePlus.
Valida paridade arquitetural com aagigs (gigs-plugin.js: lancarLembrete):
- Normalização de strings e matching idempotente no painel de post-its
- Criação com título, visibilidade (LOCAL/PRIVADO/GLOBAL) e destinatário
- Conclusão/remoção de lembrete existente (ação [concluir])
- Substituição de template de clipboard
- Re-exports canônicos em Fix.facade_publica e Fix.gigs
"""

from unittest.mock import MagicMock, patch
import pytest

from Fix.extracao import (
    _normalizar_texto,
    _verificar_lembrete_presente,
    criar_lembrete_posit,
    remover_lembrete_posit,
)
from Fix.facade_publica import (
    criar_lembrete_posit as facade_criar,
    remover_lembrete_posit as facade_remover,
)
from Fix.gigs import (
    criar_lembrete_posit as gigs_criar,
    remover_lembrete_posit as gigs_remover,
)


class TestNormalizacaoTexto:
    def test_normalizar_texto_basico(self):
        assert _normalizar_texto("Bloqueio Pendente") == "bloqueio pendente"
        assert _normalizar_texto("  Prescrição   Bienal  ") == "prescricao bienal"
        assert _normalizar_texto("Atenção: NÃO EXPEDIR") == "atencao: nao expedir"
        assert _normalizar_texto("") == ""
        assert _normalizar_texto(None) == ""


class TestVerificarLembretePresente:
    def test_container_ausente_retorna_false(self):
        driver = MagicMock()
        with patch("Fix.extracao.espera.elemento", return_value=None):
            assert _verificar_lembrete_presente(driver, "bloqueio", teto=0.1) is False

    def test_encontra_lembrete_por_titulo(self):
        driver = MagicMock()
        container_mock = MagicMock()
        painel_mock = MagicMock()
        el_tit = MagicMock()
        el_tit.text = "Bloqueio pendente"

        def fake_elemento(target, seletor, teto=0.2):
            if "pje-visualizador-post-its" in seletor:
                return container_mock
            if "post-it-div-titulo" in seletor:
                return el_tit
            return None

        with patch("Fix.extracao.espera.elemento", side_effect=fake_elemento), \
             patch("Fix.extracao.espera.elementos", return_value=[painel_mock]), \
             patch("Fix.extracao.espera.assentar"):
            assert _verificar_lembrete_presente(driver, "bloqueio", teto=0.2) is True

    def test_encontra_lembrete_por_titulo_e_conteudo(self):
        driver = MagicMock()
        container_mock = MagicMock()
        painel_mock = MagicMock()
        el_tit = MagicMock()
        el_tit.text = "mdd positivo"
        el_cont = MagicMock()
        el_cont.text = "Mandado positivo (Fulano de Tal) - via correio"

        def fake_elemento(target, seletor, teto=0.2):
            if "pje-visualizador-post-its" in seletor:
                return container_mock
            if "post-it-div-titulo" in seletor:
                return el_tit
            if "Conteúdo do Lembrete" in seletor:
                return el_cont
            return None

        with patch("Fix.extracao.espera.elemento", side_effect=fake_elemento), \
             patch("Fix.extracao.espera.elementos", return_value=[painel_mock]), \
             patch("Fix.extracao.espera.assentar"):
            assert _verificar_lembrete_presente(driver, "mdd positivo", conteudo="correio", teto=0.2) is True
            assert _verificar_lembrete_presente(driver, "mdd positivo", conteudo="oficial justiça", teto=0.2) is False


class TestCriarLembretePosit:
    def test_retorna_false_se_driver_desconectado(self):
        driver = MagicMock()
        with patch("Fix.extracao.validar_conexao_driver", return_value=False):
            assert criar_lembrete_posit(driver, "bloqueio", "obs") is False

    def test_idempotencia_quando_ja_presente(self):
        driver = MagicMock()
        with patch("Fix.extracao.validar_conexao_driver", return_value=True), \
             patch("Fix.extracao._verificar_lembrete_presente", return_value=True):
            # Se já está presente, retorna True sem abrir modal
            assert criar_lembrete_posit(driver, "bloqueio", "obs", verificar_existente=True) is True

    def test_criacao_completa_com_visibilidade_e_conteudo(self):
        driver = MagicMock()
        btn_postit = MagicMock()
        campos_preenchidos = []

        def fake_preencher(drv, sel, val, **kwargs):
            campos_preenchidos.append((sel, val))
            return True

        with patch("Fix.extracao.validar_conexao_driver", return_value=True), \
             patch("Fix.extracao._verificar_lembrete_presente", return_value=False), \
             patch("Fix.extracao.espera.elemento", side_effect=lambda drv, sel, **kw: btn_postit if "pje-icone-post-it" in sel or "visibilidadePostit" in sel else None), \
             patch("Fix.extracao.safe_click_no_scroll"), \
             patch("Fix.extracao.aguardar_e_clicar", return_value=True), \
             patch("Fix.extracao.espera.ate_aparecer", return_value=True), \
             patch("Fix.extracao.preencher_campo", side_effect=fake_preencher), \
             patch("Fix.extracao.selecionar_opcao", return_value=True) as mock_sel_opcao, \
             patch("Fix.extracao.espera.ate_js", return_value=True), \
             patch("Fix.extracao.espera.ate_sumir", return_value=True), \
             patch("Fix.extracao.espera.assentar"):

            sucesso = criar_lembrete_posit(
                driver,
                titulo="Bloqueio SISBAJUD",
                conteudo="Processar após 15 dias",
                visibilidade="LOCAL",
                salvar=True,
            )
            assert sucesso is True
            assert ("#tituloPostit", "Bloqueio SISBAJUD") in campos_preenchidos
            assert ("#conteudoPostit", "Processar após 15 dias") in campos_preenchidos
            mock_sel_opcao.assert_called_once()

    def test_criacao_com_template_clipboard(self):
        driver = MagicMock()
        campos_preenchidos = []

        def fake_preencher(drv, sel, val, **kwargs):
            campos_preenchidos.append((sel, val))
            return True

        with patch("Fix.extracao.validar_conexao_driver", return_value=True), \
             patch("Fix.extracao._verificar_lembrete_presente", return_value=False), \
             patch("Fix.extracao.pyperclip.paste", return_value="1000123-45.2026.5.02.0001"), \
             patch("Fix.extracao.espera.elemento", return_value=MagicMock()), \
             patch("Fix.extracao.safe_click_no_scroll"), \
             patch("Fix.extracao.aguardar_e_clicar", return_value=True), \
             patch("Fix.extracao.espera.ate_aparecer", return_value=True), \
             patch("Fix.extracao.preencher_campo", side_effect=fake_preencher), \
             patch("Fix.extracao.espera.ate_js", return_value=True), \
             patch("Fix.extracao.espera.ate_sumir", return_value=True), \
             patch("Fix.extracao.espera.assentar"):

            sucesso = criar_lembrete_posit(
                driver,
                titulo="Processo Vinculado",
                conteudo="Verificar processo clipboard urgente",
                salvar=True,
            )
            assert sucesso is True
            assert ("#conteudoPostit", "Verificar processo 1000123-45.2026.5.02.0001 urgente") in campos_preenchidos

    def test_delegacao_para_remover_quando_acao_concluir(self):
        driver = MagicMock()
        with patch("Fix.extracao.remover_lembrete_posit", return_value=True) as mock_remover:
            resultado = criar_lembrete_posit(driver, "bloqueio", "obs", acao="concluir")
            assert resultado is True
            mock_remover.assert_called_once_with(driver, titulo="bloqueio", conteudo="obs", debug=False)


class TestRemoverLembretePosit:
    def test_remover_lembrete_com_sucesso(self):
        driver = MagicMock()
        container_mock = MagicMock()
        painel_mock = MagicMock()
        el_tit = MagicMock()
        el_tit.text = "Bloqueio pendente"
        btn_remover = MagicMock()

        def fake_elemento(target, seletor, teto=0.3):
            if "pje-visualizador-post-its" in seletor:
                return container_mock
            if "post-it-div-titulo" in seletor:
                return el_tit
            if "Remover" in seletor:
                return btn_remover
            return None

        with patch("Fix.extracao.validar_conexao_driver", return_value=True), \
             patch("Fix.extracao.espera.elemento", side_effect=fake_elemento), \
             patch("Fix.extracao.espera.elementos", return_value=[painel_mock]), \
             patch("Fix.extracao.safe_click_no_scroll"), \
             patch("Fix.extracao.aguardar_e_clicar", return_value=True), \
             patch("Fix.extracao.espera.ate_sumir", return_value=True), \
             patch("Fix.extracao.espera.assentar"):

            resultado = remover_lembrete_posit(driver, "bloqueio")
            assert resultado is True


class TestReExports:
    def test_funcoes_exportadas_em_facade_e_gigs(self):
        assert callable(facade_criar)
        assert callable(facade_remover)
        assert callable(gigs_criar)
        assert callable(gigs_remover)
        assert facade_criar is criar_lembrete_posit
        assert facade_remover is remover_lembrete_posit
        assert gigs_criar is criar_lembrete_posit
        assert gigs_remover is remover_lembrete_posit
