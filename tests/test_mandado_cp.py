"""Testes unitários para o fluxo de Carta Precatória (contagem e baixarCP).

Cobre:
- Extração de texto e matching de documentos (CDist, Despacho, Mandado, Certidão OJ, Certidão geral)
- contar_mandados_e_certidoes_oficial (API e DOM fallback)
- baixarCP (API-first com seletores do probe #doc_<uid>, DOM fallback, PDF único)
- _cp_marcar_checkbox (idempotência e suporte a múltiplos seletores)
"""

from unittest.mock import MagicMock, patch
import pytest

from Fix.core import (
    _extrair_texto_item_api,
    _cp_eh_cdist,
    _cp_eh_despacho,
    _cp_eh_mandado,
    _cp_eh_certidao_oj,
    _cp_eh_certidao_geral,
    _cp_texto_documento,
    _cp_marcar_checkbox,
    contar_mandados_e_certidoes_oficial,
    baixarCP,
)


# Dados reais extraídos do probe PJe Probe — 1001742-81.2026
PROBE_TIMELINE_API = [
    {
        "id": 1070001,
        "idUnicoDocumento": "107a23d",
        "titulo": "Certidão",
        "descricao": "Certidão de Oficial de Justiça",
        "tipo": "Certidão",
    },
    {
        "id": 2090002,
        "idUnicoDocumento": "2d9dbaa",
        "titulo": "Mandado",
        "descricao": "Mandado",
        "tipo": "Mandado",
    },
    {
        "id": 4770003,
        "idUnicoDocumento": "4774fce",
        "titulo": "Certidão",
        "descricao": "Certidão de Oficial de Justiça",
        "tipo": "Certidão",
    },
    {
        "id": 3580004,
        "idUnicoDocumento": "de58e53",
        "titulo": "Certidão",
        "descricao": "Ciência ao Juízo deprecante",
        "tipo": "Certidão",
    },
    {
        "id": 3100005,
        "idUnicoDocumento": "0310153",
        "titulo": "Mandado",
        "descricao": "Mandado",
        "tipo": "Mandado",
    },
    {
        "id": 2340006,
        "idUnicoDocumento": "e2f3bcc",
        "titulo": "Despacho",
        "descricao": "Despacho",
        "tipo": "Despacho",
    },
    {
        "id": 4700007,
        "idUnicoDocumento": "47c03da",
        "titulo": "Certidão",
        "descricao": "Certidão de Distribuição",
        "tipo": "Certidão",
    },
]


class TestPredicadosCP:
    def test_extrair_texto_item_api_inclui_descricao(self):
        doc = {
            "titulo": "Certidão",
            "descricao": "Certidão de Distribuição",
            "tipo": "Certidão",
            "nomeDocumento": "dist.pdf",
        }
        texto = _extrair_texto_item_api(doc)
        assert "distribuicao" in texto
        assert _cp_eh_cdist(texto)

    def test_predicados_documentos_probe(self):
        # 1. Certidão de Oficial de Justiça
        t_cert_oj = _extrair_texto_item_api(PROBE_TIMELINE_API[0])
        assert _cp_eh_certidao_oj(t_cert_oj)
        assert not _cp_eh_mandado(t_cert_oj)

        # 2. Mandado
        t_mand = _extrair_texto_item_api(PROBE_TIMELINE_API[1])
        assert _cp_eh_mandado(t_mand)
        assert not _cp_eh_certidao_oj(t_mand)

        # 4. Certidão Ciência deprecante (certidão geral, não OJ)
        t_ciencia = _extrair_texto_item_api(PROBE_TIMELINE_API[3])
        assert _cp_eh_certidao_geral(t_ciencia)
        assert not _cp_eh_certidao_oj(t_ciencia)

        # 6. Despacho
        t_desp = _extrair_texto_item_api(PROBE_TIMELINE_API[5])
        assert _cp_eh_despacho(t_desp)

        # 7. CDist
        t_cdist = _extrair_texto_item_api(PROBE_TIMELINE_API[6])
        assert _cp_eh_cdist(t_cdist)


class TestContarMandadosECertidoes:
    def test_contar_via_api_dados_probe(self):
        mock_driver = MagicMock()
        mock_driver.current_url = "https://pje.trt2.jus.br/pjekz/processo/8924893/detalhe"

        with patch("Fix.core._obter_timeline_via_api", return_value=PROBE_TIMELINE_API):
            qtd_mandados, qtd_certidoes = contar_mandados_e_certidoes_oficial(mock_driver, log=False)

        # Do probe: 2 Mandados (2d9dbaa, 0310153) e 2 Certidões OJ (107a23d, 4774fce)
        assert qtd_mandados == 2
        assert qtd_certidoes == 2

    def test_contar_fallback_dom(self):
        mock_driver = MagicMock()

        elem_cdist = MagicMock()
        elem_cdist.text = "Certidão de Distribuição"
        elem_cdist.get_attribute.return_value = "Selecionar Certidão. Certidão de Distribuição"

        elem_mand1 = MagicMock()
        elem_mand1.text = "Mandado 0310153"
        elem_mand1.get_attribute.return_value = "Selecionar Mandado. ID: 0310153"

        elem_cert1 = MagicMock()
        elem_cert1.text = "Certidão de Oficial de Justiça"
        elem_cert1.get_attribute.return_value = "Selecionar Certidão de Oficial de Justiça"

        with patch("Fix.core._obter_timeline_via_api", return_value=None):
            with patch("Fix.core._buscar_filho", return_value=None):
                with patch("Fix.core.espera.elementos", return_value=[elem_cdist, elem_mand1, elem_cert1]):
                    qtd_mandados, qtd_certidoes = contar_mandados_e_certidoes_oficial(mock_driver, log=False)

        assert qtd_mandados == 1
        assert qtd_certidoes == 1


class TestCpTextoDocumento:
    def test_leitura_aria_label_mat_checkbox(self):
        elem = MagicMock()
        elem.tag_name = "mat-checkbox"
        elem.get_attribute.side_effect = lambda attr: (
            "Selecionar Certidão. Certidão de Distribuição. ID: 47c03da" if attr == "aria-label" else ""
        )
        elem.text = ""

        with patch("Fix.core._buscar_filho", return_value=None):
            texto = _cp_texto_documento(elem)

        assert "certidao de distribuicao" in texto
        assert _cp_eh_cdist(texto)


class TestCpMarcarCheckbox:
    def test_ja_marcado_retorna_true_sem_clicar(self):
        mock_driver = MagicMock()
        mock_elem = MagicMock()
        mock_elem.get_attribute.return_value = "mat-checkbox mat-checkbox-checked"

        # Mock de input com checked=True
        mock_input = MagicMock()
        mock_input.get_attribute.return_value = "true"
        mock_input.is_selected.return_value = True

        with patch("Fix.core._buscar_filho", return_value=mock_input):
            with patch("Fix.core.safe_click_no_scroll") as mock_click:
                res = _cp_marcar_checkbox(mock_driver, mock_elem)

        assert res is True
        mock_click.assert_not_called()

    def test_marcar_por_seletor_uid(self):
        mock_driver = MagicMock()
        mock_elem = MagicMock()
        mock_elem.get_attribute.return_value = "mat-checkbox"

        with patch("Fix.core.espera.elemento", return_value=mock_elem):
            with patch("Fix.core._buscar_filho", return_value=None):
                with patch("Fix.core.safe_click_no_scroll", return_value=True):
                    res = _cp_marcar_checkbox(mock_driver, "#doc_47c03da")

        assert res is True


class TestBaixarCP:
    def test_baixar_cp_via_api_probe(self):
        mock_driver = MagicMock()
        mock_driver.current_url = "https://pje.trt2.jus.br/pjekz/processo/8924893/detalhe"

        marcados_uids = []

        def mock_marcar(driver, elem, timeout=10):
            if isinstance(elem, str):
                marcados_uids.append(elem)
            return True

        with patch("Fix.core._obter_timeline_via_api", return_value=PROBE_TIMELINE_API):
            with patch("Fix.browser_suporte.click_headless_safe", return_value=True):
                with patch("Fix.core.aguardar_renderizacao_nativa", return_value=True):
                    with patch("atos.movimentos_navegacao.clicar_botao_por_texto", return_value=True):
                        with patch("Fix.core._cp_marcar_checkbox", side_effect=mock_marcar):
                            sucesso = baixarCP(mock_driver, log=False, numero_processo="1001742-81.2026.5.02.0000")

        assert sucesso is True
        # Todos os 7 documentos da CP (âncora CDist até o topo) devem ser marcados
        assert "#doc_47c03da" in marcados_uids  # CDist (âncora)
        assert "#doc_e2f3bcc" in marcados_uids  # Despacho
        assert "#doc_0310153" in marcados_uids  # Mandado
        assert "#doc_de58e53" in marcados_uids  # Certidão Ciência
        assert "#doc_4774fce" in marcados_uids  # Certidão OJ
        assert "#doc_2d9dbaa" in marcados_uids  # Mandado
        assert "#doc_107a23d" in marcados_uids  # Certidão OJ
        assert len(marcados_uids) == 7
