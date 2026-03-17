"""
f2.py - Teste isolado para `obter_texto_documento`.

Comportamento:
- Cria um driver logado (usa cookies se existentes) via `Fix.core.credencial`
- Navega para a URL do documento fornecida
- Cria uma sessão a partir do driver e instancia `PjeApiClient`
- Chama `obter_texto_documento(client, id_processo, id_documento)` e imprime resultado

Uso:
    py f2.py
"""

from Fix.core import credencial, finalizar_driver
from Fix.variaveis import session_from_driver, PjeApiClient, obter_texto_documento
import time
import traceback

# URL e IDs para teste
TEST_URL = 'https://pje.trt2.jus.br/pjekz/processo/2189908/documento/428080041/conteudo'
ID_PROCESSO = '2189908'
ID_DOCUMENTO = '428080041'


def executar_teste_obter_texto():
    print('[F2] Iniciando teste de obter_texto_documento')
    driver = credencial(tipo_driver='PC', tipo_login='CPF', headless=False)
    if not driver:
        print('[F2][ERRO] Falha ao criar/obter driver logado')
        return False

    try:
        print(f'[F2] Navegando para: {TEST_URL}')
        driver.get(TEST_URL)
        time.sleep(3)

        try:
            sess, trt = session_from_driver(driver)
            client = PjeApiClient(sess, trt)

            print('[F2] Chamando obter_texto_documento via API...')
            texto = obter_texto_documento(client, ID_PROCESSO, ID_DOCUMENTO)

            if texto:
                print('[F2] ✅ Texto obtido com sucesso')
                print(f'[F2] Tamanho do texto: {len(texto)} caracteres')
                print('\n--- INÍCIO (primeiros 1000 chars) ---')
                print(texto[:1000])
                print('--- FIM ---\n')
                return True
            else:
                print('[F2] ⚠️ Não foi possível obter texto via API (retornou None)')
                return False

        except Exception as e:
            print(f'[F2][ERRO] Falha ao executar chamada API: {e}')
            traceback.print_exc()
            return False

    finally:
        try:
            finalizar_driver(driver, log=True)
        except Exception:
            pass


if __name__ == '__main__':
    executar_teste_obter_texto()
