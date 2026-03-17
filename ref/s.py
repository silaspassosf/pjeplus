"""
Teste completo da segunda minuta agendada usando funções do módulo SISB
Fluxo: Login → Navegar para ordem existente → Copiar dados → Criar segunda minuta
"""

from SISB.core import iniciar_sisbajud
from SISB.helpers import _criar_minuta_agendada_por_copia

def testar_segunda_minuta_completa():
    """
    Testa o fluxo completo da segunda minuta agendada:
    1. Login SISBAJUD
    2. Navegar para ordem judicial existente
    3. Usar _criar_minuta_agendada_por_copia para criar segunda minuta
    """
    driver = None

    try:
        print('=' * 80)
        print('TESTE COMPLETO: SEGUNDA MINUTA AGENDADA')
        print('=' * 80)

        # 1. Iniciar SISBAJUD (driver + login automático)
        print('\n[TESTE] 1. Iniciando SISBAJUD (driver + login)...')
        driver = iniciar_sisbajud(
            driver_pje=None,
            extrair_dados=False
        )

        if not driver:
            print('[TESTE] ❌ Falha ao iniciar SISBAJUD')
            return False

        print('[TESTE] ✅ SISBAJUD iniciado e autenticado')

        # 2. Navegar para ordem judicial existente
        print('\n[TESTE] 2. Navegando para ordem judicial existente...')
        url_ordem = 'https://sisbajud.cnj.jus.br/ordem-judicial/20201125967575/detalhar'
        driver.get(url_ordem)

        # Aguardar carregamento
        import time
        time.sleep(3)

        if '20201125967575' not in driver.current_url:
            print(f'[TESTE] ❌ Não conseguiu navegar para ordem judicial. URL atual: {driver.current_url}')
            return False

        print('[TESTE] ✅ Navegou para ordem judicial existente')

        # 3. Executar criação da segunda minuta usando função do módulo SISB
        print('\n[TESTE] 3. Executando criação da segunda minuta...')

        # Dados do processo (serão extraídos automaticamente pela função)
        dados_processo = {
            'numero_processo': '20201125967575',
            'tipo_acao': 'Ordem Judicial',
            'valor': 0.00  # Será copiado da ordem original
        }

        # Usar a função corrigida do módulo SISB
        protocolo_segunda_minuta = _criar_minuta_agendada_por_copia(
            driver=driver,
            dados_processo=dados_processo,
            log=True
        )

        if protocolo_segunda_minuta:
            print(f'[TESTE] ✅ Segunda minuta criada com sucesso!')
            print(f'[TESTE]  Protocolo: {protocolo_segunda_minuta}')
            return True
        else:
            print('[TESTE] ❌ Falha na criação da segunda minuta')
            return False

    except Exception as e:
        print(f'[TESTE] ❌ Erro durante execução: {e}')
        import traceback
        traceback.print_exc()
        return False

    finally:
        if driver:
            print('\n[TESTE] Fechando driver...')
            driver.quit()
            print('[TESTE] ✅ Driver fechado')

if __name__ == '__main__':
    sucesso = testar_segunda_minuta_completa()
    print('\n' + '=' * 80)
    if sucesso:
        print('RESULTADO: ✅ TESTE COMPLETO BEM-SUCEDIDO')
        print('Segunda minuta agendada criada com sucesso!')
    else:
        print('RESULTADO: ❌ TESTE FALHOU')
        print('Verificar logs acima para detalhes do erro')
    print('=' * 80)
