# ============================================================
# f.py -- Harness de teste isolado: Triagem completa
# Uso: py f.py
# Processo alvo: 8501188
# ============================================================

ID_PROCESSO = '8505663'

from Triagem.driver import criar_driver_e_logar
from Triagem.runner import _processar_processo


def main():
    driver = criar_driver_e_logar()
    if not driver:
        print('[TESTE][ERRO] Falha ao criar driver ou logar')
        return

    processo_info = {
        'numero': ID_PROCESSO,
        'id_processo': ID_PROCESSO,
        'tipo': '',
        'digital': False,
        'tem_audiencia': False,
        'bucket': 'B',
    }

    print(f'[TESTE] Executando fluxo completo para processo {ID_PROCESSO}...')
    progresso = {}
    ok = _processar_processo(driver, processo_info, progresso)

    triagem_txt = processo_info.get('triagem', '')
    if triagem_txt:
        print('\n=== RESULTADO TRIAGEM ===')
        print(triagem_txt)
        print('=========================\n')

    print(f'[TESTE] Resultado final: {"OK" if ok else "FALHOU"}')
    print('[TESTE] Concluido. Encerrando driver...')
    driver.quit()


if __name__ == '__main__':
    main()

