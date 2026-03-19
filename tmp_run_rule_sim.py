import sys
sys.path.insert(0, r'.')
try:
    from Prazo import p2b_fluxo_lazy
    from Prazo import p2b_fluxo_regras
except Exception as e:
    print('IMPORT_ERROR', e)
    raise

# create stubs
def make_stub(name):
    def fn(driver=None, *a, **k):
        print(f'STUB_CALL:{name}')
        return True
    return fn

p2b_fluxo_lazy._modules_cache = {
    'mov_arquivar': make_stub('mov_arquivar'),
    'mov_exec': make_stub('mov_exec'),
    'ato_180': make_stub('ato_180'),
    'ato_calc2': make_stub('ato_calc2'),
    'ato_pesquisas': make_stub('ato_pesquisas'),
    'ato_pesqliq': make_stub('ato_pesqliq'),
    'ato_prev': make_stub('ato_prev'),
    'ato_meios': make_stub('ato_meios'),
    'ato_sobrestamento': make_stub('ato_sobrestamento'),
    'retifidpj_wrapper': make_stub('retifidpj_wrapper'),
    'pec_excluiargos': make_stub('pec_excluiargos'),
    'criar_gigs': make_stub('criar_gigs'),
}

from Prazo.p2b_core import normalizar_texto

tests = [
    'A pronúncia da prescrição foi registrada',
    'O documento está sob pena de bloqueio',
    'Concedo 05 dias para apresentação',
    'Concorda com homologação do acordo',
    'Exequente, ora embargado, apresentou defesa',
    'Decido procedentes os embargos',
    'Consta saldo devedor na conta',
    'Ante a notícia de descumprimento do acordo',
    'Comprovar recolhimento do valor',
    'Defiro a penhora no rosto dos autos',
    'RECLAMANTE para apresentar cálculos de liquidação',
    'Deverá realizar tentativas de conciliação',
    'Defiro a instauração do procedimento',
    'Tendo em vista que houve atraso no pagamento da parcela pendente',
    'Pagamento da próxima parcela deverá ser feito',
    'INDEFIRO o pedido de desconsideração',
    'Arquivem-se os autos por inércia',
    'Registre-se o movimento processual adequado',
]

rules = p2b_fluxo_regras._definir_regras_processamento()

for text in tests:
    text_norm = normalizar_texto(text)
    print('\n=== TEST: %s' % text)
    print('normalized:', text_norm)
    # for rules that call inicar_exec, mock phase detection to simulate liquidação
    try:
        import Prazo.p2b_fluxo_helpers as helpers
        helpers.obter_fase_processual = lambda d: 'liquidacao'
    except Exception:
        pass
    # show matching rules
    for i, rule in enumerate(rules):
        try:
            keywords = rule[0]
            tipo_acao = rule[1] if len(rule) > 1 else None
        except Exception:
            continue
        for regex in keywords:
            try:
                if regex.search(text_norm):
                    print('MATCH RULE', i, 'pattern=', getattr(regex, 'pattern', str(regex)), 'tipo_acao=', tipo_acao)
            except Exception:
                pass

    res = p2b_fluxo_regras._processar_regras_gerais(None, text_norm, doc_idx=0)
    print('RETURNED:', res)
