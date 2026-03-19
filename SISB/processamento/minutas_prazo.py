import logging

logger = logging.getLogger(__name__)

"""
SISB Minutas - Selecao de prazo
"""


def _selecionar_prazo_bloqueio(driver, padrao=30):
    """
    Helper para selecionar prazo (30 ou 60 dias) via dialogo JavaScript no SISBAJUD.
    """
    try:
        script_selecao_prazo = """
        return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                z-index: 100000;
                display: flex;
                justify-content: center;
                align-items: center;
            `;

            const dialog = document.createElement('div');
            dialog.style.cssText = `
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                text-align: center;
                min-width: 400px;
            `;

            const titulo = document.createElement('h2');
            titulo.textContent = 'Selecionar Prazo de Bloqueio';
            titulo.style.cssText = 'color: #333; margin-bottom: 20px; font-size: 18px;';
            dialog.appendChild(titulo);

            const explicacao = document.createElement('p');
            explicacao.textContent = 'Escolha o prazo para a minuta de bloqueio:';
            explicacao.style.cssText = 'color: #666; margin-bottom: 20px;';
            dialog.appendChild(explicacao);

            const btnContainer = document.createElement('div');
            btnContainer.style.cssText = 'display: flex; gap: 10px; justify-content: center;';

            const btn30 = document.createElement('button');
            btn30.textContent = '30 dias + 1';
            btn30.style.cssText = `
                padding: 12px 30px;
                background: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
                cursor: pointer;
            `;
            btn30.onmouseover = () => btn30.style.background = '#0056b3';
            btn30.onmouseout = () => btn30.style.background = '#007bff';
            btn30.onclick = () => {
                overlay.remove();
                resolve(30);
            };
            btnContainer.appendChild(btn30);

            const btn60 = document.createElement('button');
            btn60.textContent = '60 dias + 1';
            btn60.style.cssText = `
                padding: 12px 30px;
                background: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
                cursor: pointer;
            `;
            btn60.onmouseover = () => btn60.style.background = '#1e7e34';
            btn60.onmouseout = () => btn60.style.background = '#28a745';
            btn60.onclick = () => {
                overlay.remove();
                resolve(60);
            };
            btnContainer.appendChild(btn60);

            dialog.appendChild(btnContainer);
            overlay.appendChild(dialog);
            document.body.appendChild(overlay);
        });
        """

        prazo_selecionado = driver.execute_async_script(script_selecao_prazo)

        if prazo_selecionado in [30, 60]:
            return prazo_selecionado
        return padrao

    except Exception as e:
        logger.error(f'[SISBAJUD]  Erro ao selecionar prazo: {e}, usando padrao: {padrao}')
        return padrao