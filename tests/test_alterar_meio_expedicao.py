"""Testes unitários para alterar_meio_expedicao.

Os fixtures reproduzem o DOM real do PJe capturado por probe no TRT2
(processo 8894351, aba /comunicacoesprocessuais/minutas):

    <tr class="cdk-drag">
      ...
      <mat-select id="destinatario_<hash>MeioExpedicao">
        <span class="mat-select-min-line">Domicílio Eletrônico</span>
      </mat-select>
    </tr>

    <div class="cdk-overlay-pane">
      <mat-option name="Correios">Correios</mat-option>
    </div>

O foco é o atropelo entre linhas: o 1º destinatário muda e o 2º abre o
dropdown mas o clique em Correios não registra (backdrop residual / linha
obsoleta depois do re-render do Angular).
"""

import unittest
from unittest.mock import MagicMock, patch

from atos.comunicacao_finalizacao import (
    alterar_meio_expedicao,
    _alterar_meio_da_linha_para_correios,
)

XP_LINHA = '(//tbody[contains(@class,"cdk-drop-list")]//tr[contains(@class,"cdk-drag")])[{idx}]'


class FakeLinha:
    """<tr> do destinatário, com o span do meio de expedição e a coluna Prazo.

    Espelha o DOM do probe: cada linha tem um hash próprio e todos os ids da
    linha derivam dele (`destinatario_<hash>MeioExpedicao`,
    `...TipoPrazoD`, `...PrazoDiasUteis`).
    """

    def __init__(self, idx, meio='Domicílio Eletrônico', id_hash=None,
                 tipo_prazo='dias_uteis', prazo=None):
        self.idx = idx
        self.meio = meio
        self.id_hash = id_hash or f"hash{idx}"
        self.tipo_prazo = tipo_prazo   # dias_uteis | sem_prazo | data_certa | dias_corridos
        self.prazo = prazo             # None quando "sem prazo"
        self._js = MagicMock(return_value=meio)

    @property
    def prefixo(self):
        return f"destinatario_{self.id_hash}"

    def ao_virar_correios(self):
        """O PJe reavalia o expediente e zera o prazo (bug relatado)."""
        self.tipo_prazo = 'sem_prazo'
        self.prazo = None

    def __repr__(self):
        return f'<Linha {self.idx} meio={self.meio!r} prazo={self.prazo!r} {self.tipo_prazo}>'


class FakeOpcao:
    def __init__(self, texto='Correios', visivel=True):
        self.text = texto
        self._visivel = visivel
        self.nome = 'Correios' if 'correio' in texto.lower() else texto

    def is_displayed(self):
        return self._visivel

    def get_attribute(self, nome):
        if nome == 'name':
            return self.nome
        return None

    def __repr__(self):
        return f'<Opcao {self.text!r} visivel={self._visivel}>'


class TabelaFake:
    """Estado da tabela de destinatários + overlay do mat-select.

    A cliques na opção "Correios" gravam o novo meio na linha `linha_aberta` —
    é o que o Angular faz de verdade.
    """

    def __init__(self, linhas):
        self.linhas = {l.idx: l for l in linhas}
        self.painel_aberto = False
        self.linha_aberta = None
        self.opcoes = [FakeOpcao('Domicílio Eletrônico'), FakeOpcao('Correios')]
        self.dropdown = MagicMock()
        self.cliques_opcao = []
        # Quando True, o clique na opção é aceito mas não grava nada
        # (simula o clique engolido pelo backdrop).
        self.engolir_clique = False

    # --- consultas -----------------------------------------------------
    def linha(self, idx):
        return self.linhas.get(idx)

    def _span(self, texto):
        m = MagicMock()
        m.text = texto
        m.is_displayed.return_value = True
        return m

    def _opcoes_para(self, sel):
        """Reproduz o filtro `correio` embutido no XPath da opção."""
        if 'correio' in sel.lower():
            return [o for o in self.opcoes if 'correio' in o.text.lower()]
        return list(self.opcoes)

    def elemento(self, driver, sel, teto=2, visivel=True):
        if 'mat-option' in sel:
            if not self.painel_aberto:
                return None
            for o in self._opcoes_para(sel):
                if o.is_displayed():
                    return o
            return None
        # span/linha de uma linha específica (XPath por índice) — checar ANTES
        # do mat-select, porque o XPath do span também contém "mat-select".
        for idx in self.linhas:
            if sel.startswith(XP_LINHA.format(idx=idx)):
                if 'mat-select-min-line' in sel or 'span' in sel:
                    return self._span(self.linhas[idx].meio)
                if 'mat-select' in sel or 'mat-form-field-infix' in sel:
                    return self.dropdown
                return self.linhas[idx]
        if 'mat-select' in sel or 'mat-form-field-infix' in sel:
            return self.dropdown
        if 'mat-select-min-line' in sel:
            l = self.linha(self.linha_aberta) if self.linha_aberta else None
            return self._span(l.meio if l else '')
        return None

    def elementos(self, driver, sel, teto=2):
        if 'tbody.cdk-drop-list tr.cdk-drag' in sel:
            return list(self.linhas.values())
        if 'mat-option' in sel:
            if not self.painel_aberto:
                return []
            return self._opcoes_para(sel)
        return []

    def ate_js(self, driver, expressao, teto=2.0):
        # A confirmação final checa o texto da própria linha.
        if "'correio'" in expressao.replace('"', "'"):
            l = self.linha(self.linha_aberta) if self.linha_aberta else None
            return bool(l and 'correio' in l.meio.lower())
        # Confirmação do prazo: tipo "dias úteis" + valor gravado.
        if 'TipoPrazo' in expressao or 'PrazoDiasUteis' in expressao:
            if 'uteis' not in expressao:
                return True
            # Por prefixo (caminho normal) ou por índice de linha (fallback).
            for l in self.linhas.values():
                if l.prefixo in expressao:
                    return l.tipo_prazo == 'dias_uteis' and l.prazo is not None
            for i, l in self.linhas.items():
                if f'[{i}]' in expressao:
                    return l.tipo_prazo == 'dias_uteis' and l.prazo is not None
            return False
        return True

    # --- coluna Prazo ---------------------------------------------------
    def executar_js(self, driver, script, *args):
        """Emula os scripts de prazo (rádio "dias úteis" + input de dias).

        Assinatura real: `_executar_js(driver, script, *args)` — o `driver` é
        consumido como primeiro argumento (não é o script).
        """
        # Caminho por linha (fallback): o seletor chega dentro do próprio script.
        if not args and 'cdk-drag' in script:
            for i in self.linhas:
                if f'[{i}]' in script:
                    linha = self.linhas[i]
                    linha.tipo_prazo = 'dias_uteis'
                    linha.prazo = '5' if 'DiasUteis' in script else linha.prazo
                    return True
            return False
        alvo = args[0] if args else ''
        linha = None
        if isinstance(alvo, str):
            for l in self.linhas.values():
                if alvo.startswith(l.prefixo):
                    linha = l
                    break
        if linha is None and isinstance(alvo, str) and 'cdk-drag' in alvo:
            # Fallback por XPath (índice da linha).
            for i in self.linhas:
                if f'[{i}]' in alvo:
                    linha = self.linhas[i]
                    break
        if linha is None:
            return False
        if alvo.endswith('TipoPrazoD-input'):
            linha.tipo_prazo = 'dias_uteis'
            return True
        if alvo.endswith('PrazoDiasUteis'):
            # Só aceita o valor quando o tipo é "dias úteis" (o input só existe aí).
            if linha.tipo_prazo != 'dias_uteis':
                return False
            linha.prazo = str(args[1]) if len(args) > 1 else '5'
            return True
        return True

    def ate_aparecer(self, driver, sel, teto=2.0):
        if 'mat-option' in sel:
            return self.painel_aberto
        return True

    def ate_sumir(self, driver, sel, teto=2.0):
        if 'mat-option' in sel:
            return not self.painel_aberto
        return True


def _ids_prazo_fake(tabela, idx):
    """Equivalente a `_ids_prazo_da_linha` usando os hashes do fake."""
    linha = tabela.linha(idx)
    if not linha:
        return None, None, None
    p = linha.prefixo
    return p, p + 'TipoPrazoD-input', p + 'PrazoDiasUteis'


def _fake_dropdown_meio(tabela):
    def _fake(driver, idx):
        tabela.linha_aberta = idx
        return tabela.dropdown
    return _fake


def _fake_safe_click(tabela):
    """Intercepta safe_click_no_scroll (dropdown e opção usam essa função)."""
    def _fake(driver, elemento, log=False):
        return _aplicar_clique(tabela, elemento)
    return _fake


def _aplicar_clique(tabela, elemento):
    """Efeito real de um clique: abre o painel ou grava o meio na linha."""
    if elemento is tabela.dropdown:
        tabela.painel_aberto = True
        return True
    if isinstance(elemento, FakeOpcao):
        tabela.cliques_opcao.append(elemento.text)
        if tabela.engolir_clique:
            return True  # aceito, porém sem efeito (clique engolido)
        if tabela.linha_aberta:
            linha = tabela.linhas[tabela.linha_aberta]
            linha.meio = elemento.text
            tabela.painel_aberto = False
            # Regressão do PJe: virar Correios zera o prazo da linha.
            if 'correio' in elemento.text.lower():
                linha.ao_virar_correios()
        return True
    return True


def _fake_clicar_elemento_real(tabela):
    """`_clicar_elemento_real` é o caminho primário do clique (Playwright)."""
    def _fake(driver, elemento):
        return _aplicar_clique(tabela, elemento)
    return _fake


def _patch_ambiente(tabela, vincular_mock=None):
    patches = [
        patch('atos.comunicacao_finalizacao.aguardar_renderizacao_nativa', return_value=True),
        patch('atos.comunicacao_finalizacao.safe_click_no_scroll', side_effect=_fake_safe_click(tabela)),
        patch('atos.comunicacao_finalizacao._clicar_elemento_real', side_effect=_fake_clicar_elemento_real(tabela)),
        patch('atos.comunicacao_finalizacao._dropdown_meio_linha', side_effect=_fake_dropdown_meio(tabela)),
        patch('atos.comunicacao_finalizacao.scroll_to_element_safe', return_value=True),
        patch('atos.comunicacao_finalizacao.espera.elemento', side_effect=tabela.elemento),
        patch('atos.comunicacao_finalizacao.espera.elementos', side_effect=tabela.elementos),
        patch('atos.comunicacao_finalizacao.espera.ate_js', side_effect=tabela.ate_js),
        patch('atos.comunicacao_finalizacao.espera.ate_aparecer', side_effect=tabela.ate_aparecer),
        patch('atos.comunicacao_finalizacao.espera.ate_sumir', side_effect=tabela.ate_sumir),
        patch('atos.comunicacao_finalizacao.espera.assentar', return_value=None),
        patch('atos.comunicacao_finalizacao._executar_js', side_effect=tabela.executar_js),
        patch('atos.comunicacao_finalizacao._ids_prazo_da_linha',
              side_effect=lambda driver, idx: _ids_prazo_fake(tabela, idx)),
    ]
    if vincular_mock is not None:
        patches.append(
            patch('atos.comunicacao_finalizacao.vincular_primeiro_endereco_valido', vincular_mock)
        )
    return patches


def _rodar(tabela, wrapper_name=None, vincular_mock=None, debug=True):
    logs = []
    patches = _patch_ambiente(tabela, vincular_mock)
    for p in patches:
        p.start()
    try:
        driver = MagicMock()
        driver.page = MagicMock()
        resultado = alterar_meio_expedicao(
            driver, debug=debug, log=logs.append, wrapper_name=wrapper_name
        )
    finally:
        for p in patches:
            p.stop()
    return resultado, logs


class TestAlterarMeioExpedicao(unittest.TestCase):

    def test_altera_uma_linha_domicilio_para_correios(self):
        """Linha em Domicílio Eletrônico muda para Correios e é confirmada."""
        tabela = TabelaFake([FakeLinha(1, 'Domicílio Eletrônico')])

        sucesso, logs = _rodar(tabela)

        self.assertTrue(sucesso)
        self.assertEqual(tabela.linha(1).meio, 'Correios')
        self.assertIn('Correios', tabela.cliques_opcao)
        self.assertTrue(any('Alterados: 1' in m for m in logs))

    def test_altera_duas_linhas_em_sequencia(self):
        """REGRESSÃO: duas linhas (a segunda era a que travava)."""
        tabela = TabelaFake([
            FakeLinha(1, 'Domicílio Eletrônico'),
            FakeLinha(2, 'Domicílio Eletrônico'),
        ])

        sucesso, logs = _rodar(tabela)

        self.assertTrue(sucesso)
        self.assertEqual(tabela.linha(1).meio, 'Correios')
        self.assertEqual(tabela.linha(2).meio, 'Correios')
        self.assertTrue(any('Alterados: 2' in m for m in logs))

    def test_altera_tres_linhas_como_no_probe(self):
        """Cenário do probe: 3 destinatários iguais -> 3 trocas."""
        tabela = TabelaFake([FakeLinha(i, 'Domicílio Eletrônico') for i in (1, 2, 3)])

        sucesso, logs = _rodar(tabela)

        self.assertTrue(sucesso)
        for i in (1, 2, 3):
            self.assertEqual(tabela.linha(i).meio, 'Correios', f'linha {i} não virou Correios')
        self.assertTrue(any('Alterados: 3' in m for m in logs))

    def test_pula_linha_ja_em_correios(self):
        """Linha já em Correios não é tocada."""
        tabela = TabelaFake([FakeLinha(1, 'Correios')])

        sucesso, logs = _rodar(tabela)

        self.assertTrue(sucesso)
        self.assertEqual(tabela.cliques_opcao, [])
        self.assertTrue(any('Alterados: 0' in m for m in logs))
        self.assertTrue(any('Não precisavam: 1' in m for m in logs))

    def test_mistura_ja_correios_e_pendente(self):
        """Só a linha pendente é alterada; a que já está em Correios é pulada."""
        tabela = TabelaFake([
            FakeLinha(1, 'Correios'),
            FakeLinha(2, 'Domicílio Eletrônico'),
        ])

        sucesso, logs = _rodar(tabela)

        self.assertTrue(sucesso)
        self.assertEqual(tabela.linha(1).meio, 'Correios')
        self.assertEqual(tabela.linha(2).meio, 'Correios')
        self.assertTrue(any('Alterados: 1' in m for m in logs))
        self.assertTrue(any('Não precisavam: 1' in m for m in logs))

    def test_retenta_quando_clique_em_correios_nao_registra(self):
        """Se o clique for engolido pelo backdrop, retenta em vez de travar."""
        tabela = TabelaFake([FakeLinha(1, 'Domicílio Eletrônico')])

        estado = {'n': 0}

        def clicar(driver, elemento):
            if isinstance(elemento, FakeOpcao):
                estado['n'] += 1
                if estado['n'] == 1:
                    tabela.cliques_opcao.append(elemento.text)
                    return True  # 1ª tentativa engolida
            return _aplicar_clique(tabela, elemento)

        logs = []
        patches = _patch_ambiente(tabela)
        for p in patches:
            p.start()
        try:
            with patch('atos.comunicacao_finalizacao._clicar_elemento_real', side_effect=clicar), \
                 patch('atos.comunicacao_finalizacao.safe_click_no_scroll',
                       side_effect=lambda d, e, log=False: _aplicar_clique(tabela, e)):
                driver = MagicMock()
                driver.page = MagicMock()
                sucesso = alterar_meio_expedicao(driver, debug=True, log=logs.append)
        finally:
            for p in patches:
                p.stop()

        self.assertTrue(sucesso)
        self.assertEqual(tabela.linha(1).meio, 'Correios', 'deveria ter retentado e aplicado')
        self.assertGreaterEqual(len(tabela.cliques_opcao), 2, 'deveria ter tentado mais de uma vez')

    def test_nao_conta_como_alterado_quando_opcao_correios_invisivel(self):
        """Opção residual (invisível) no DOM não pode contar como troca."""
        tabela = TabelaFake([FakeLinha(1, 'Domicílio Eletrônico')])
        tabela.opcoes = [FakeOpcao('Correios', visivel=False)]

        sucesso, logs = _rodar(tabela)

        self.assertTrue(sucesso)
        self.assertEqual(tabela.linha(1).meio, 'Domicílio Eletrônico')
        self.assertTrue(any('Alterados: 0' in m for m in logs))

    def test_chama_vincular_endereco_para_pec_exeq(self):
        """Em pec_exeq, após mudar para Correios, vincula o primeiro endereço."""
        tabela = TabelaFake([FakeLinha(1, 'Domicílio Eletrônico')])
        vincular = MagicMock()

        sucesso, logs = _rodar(tabela, wrapper_name='pec_exeq', vincular_mock=vincular)

        self.assertTrue(sucesso)
        self.assertEqual(tabela.linha(1).meio, 'Correios')
        vincular.assert_called_once()
        self.assertEqual(vincular.call_args.kwargs.get('idx'), 1)

    def test_nao_chama_vincular_endereco_fora_de_pec_exeq(self):
        """Nos wrappers AR, não seleciona primeiro endereço."""
        for wrapper in ('pec_arord', 'pec_arordv', 'pec_arsum', 'pec_arsumv', 'pec_outro', None):
            with self.subTest(wrapper=wrapper):
                tabela = TabelaFake([FakeLinha(1, 'Domicílio Eletrônico')])
                vincular = MagicMock()

                sucesso, logs = _rodar(tabela, wrapper_name=wrapper, vincular_mock=vincular)

                self.assertTrue(sucesso)
                self.assertEqual(tabela.linha(1).meio, 'Correios')
                vincular.assert_not_called()

    def test_restabelece_prazo_5_dias_apos_virar_correios(self):
        """REGRESSÃO: ao virar Correios o prazo cai para "sem prazo" — volta para 5 dias úteis."""
        tabela = TabelaFake([FakeLinha(1, 'Domicílio Eletrônico', prazo='5')])

        sucesso, logs = _rodar(tabela)

        self.assertTrue(sucesso)
        self.assertEqual(tabela.linha(1).meio, 'Correios')
        self.assertEqual(tabela.linha(1).tipo_prazo, 'dias_uteis', 'tipo de prazo deveria ser dias úteis')
        self.assertEqual(tabela.linha(1).prazo, '5', 'prazo deveria voltar para 5 dias')

    def test_restabelece_prazo_em_cada_linha_antes_da_proxima(self):
        """Com 3 destinatários, TODAS precisam terminar com meio Correios e prazo 5."""
        tabela = TabelaFake([
            FakeLinha(1, 'Domicílio Eletrônico', prazo='5'),
            FakeLinha(2, 'Domicílio Eletrônico', prazo='5'),
            FakeLinha(3, 'Domicílio Eletrônico', prazo='5'),
        ])

        sucesso, logs = _rodar(tabela)

        self.assertTrue(sucesso)
        for i in (1, 2, 3):
            linha = tabela.linha(i)
            self.assertEqual(linha.meio, 'Correios', f'linha {i}: meio')
            self.assertEqual(linha.tipo_prazo, 'dias_uteis', f'linha {i}: tipo de prazo')
            self.assertEqual(linha.prazo, '5', f'linha {i}: prazo')

    def test_prazo_respeita_valor_do_wrapper(self):
        """Wrappers de 5 dias usam 5; o valor vem do wrapper, não é fixo no código."""
        tabela = TabelaFake([FakeLinha(1, 'Domicílio Eletrônico', prazo='8')])
        logs = []
        patches = _patch_ambiente(tabela)
        for p in patches:
            p.start()
        try:
            driver = MagicMock()
            driver.page = MagicMock()
            alterar_meio_expedicao(driver, debug=True, log=logs.append, prazo_dias=8)
        finally:
            for p in patches:
                p.stop()

        self.assertEqual(tabela.linha(1).tipo_prazo, 'dias_uteis')
        self.assertEqual(tabela.linha(1).prazo, '8')

    def test_nao_restabelece_prazo_quando_desligado(self):
        """`restabelecer_prazo=False` preserva o comportamento antigo (sem mexer no prazo)."""
        tabela = TabelaFake([FakeLinha(1, 'Domicílio Eletrônico', prazo='5')])
        logs = []
        patches = _patch_ambiente(tabela)
        for p in patches:
            p.start()
        try:
            driver = MagicMock()
            driver.page = MagicMock()
            alterar_meio_expedicao(driver, debug=True, log=logs.append,
                                   restabelecer_prazo=False)
        finally:
            for p in patches:
                p.stop()

        self.assertEqual(tabela.linha(1).meio, 'Correios')
        self.assertEqual(tabela.linha(1).tipo_prazo, 'sem_prazo')
        self.assertIsNone(tabela.linha(1).prazo)

    def test_fallback_por_linha_quando_ids_de_prazo_nao_sao_derivaveis(self):
        """Se a linha re-renderizou e os ids não derivam, o fallback por <tr> resolve."""
        tabela = TabelaFake([FakeLinha(1, 'Domicílio Eletrônico', prazo='5')])
        logs = []
        patches = _patch_ambiente(tabela)
        for p in patches:
            p.start()
        try:
            with patch('atos.comunicacao_finalizacao._ids_prazo_da_linha',
                       side_effect=lambda driver, idx: (None, None, None)):
                driver = MagicMock()
                driver.page = MagicMock()
                alterar_meio_expedicao(driver, debug=True, log=logs.append)
        finally:
            for p in patches:
                p.stop()

        self.assertEqual(tabela.linha(1).meio, 'Correios')
        self.assertEqual(tabela.linha(1).tipo_prazo, 'dias_uteis')
        self.assertEqual(tabela.linha(1).prazo, '5')

    def test_helper_direto_retorna_true_quando_ja_e_correios(self):
        """Atalho: linha já em Correios não abre dropdown."""
        tabela = TabelaFake([FakeLinha(1, 'Correios')])

        patches = _patch_ambiente(tabela)
        for p in patches:
            p.start()
        try:
            resultado = _alterar_meio_da_linha_para_correios(MagicMock(), 1)
        finally:
            for p in patches:
                p.stop()

        self.assertTrue(resultado)
        self.assertFalse(tabela.painel_aberto)


if __name__ == '__main__':
    unittest.main()
