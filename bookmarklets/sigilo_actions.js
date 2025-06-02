// ====================
// BOOKMARKLET SIGILO - Ações para controle de sigilo
// ====================

javascript:(function(){
    // Funções auxiliares comuns
    function esperarElemento(seletor, timeout = 5000) {
        return new Promise((resolve) => {
            const start = Date.now();
            const check = () => {
                const element = document.querySelector(seletor);
                if (element) {
                    resolve(element);
                } else if (Date.now() - start < timeout) {
                    setTimeout(check, 100);
                } else {
                    resolve(null);
                }
            };
            check();
        });
    }

    function clicarElemento(elemento) {
        if (elemento) {
            elemento.scrollIntoView({block: 'center'});
            elemento.click();
            return true;
        }
        return false;
    }

    function criarBotaoFlutuante() {
        if (document.getElementById('pje-bookmarklet-sigilo')) return;
        
        const botao = document.createElement('div');
        botao.id = 'pje-bookmarklet-sigilo';
        botao.innerHTML = `
            <div style="position: fixed; top: 20px; right: 20px; z-index: 99999; background: #673AB7; color: white; padding: 15px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.3); font-family: Arial, sans-serif; cursor: move;">
                <div style="font-weight: bold; margin-bottom: 10px; text-align: center;">PJe Plus - Sigilo</div>
                <div style="display: flex; flex-direction: column; gap: 8px;">
                    <button onclick="ativarSigilo()" style="padding: 8px 12px; border: none; border-radius: 4px; background: #FF5722; color: white; cursor: pointer; font-size: 12px;">🔒 Ativar Sigilo</button>
                    <button onclick="desativarSigilo()" style="padding: 8px 12px; border: none; border-radius: 4px; background: #4CAF50; color: white; cursor: pointer; font-size: 12px;">🔓 Desativar Sigilo</button>
                    <button onclick="verificarSigilo()" style="padding: 8px 12px; border: none; border-radius: 4px; background: #2196F3; color: white; cursor: pointer; font-size: 12px;">👁️ Verificar Status</button>
                    <button onclick="aplicarVisibilidadeSigilosa()" style="padding: 8px 12px; border: none; border-radius: 4px; background: #795548; color: white; cursor: pointer; font-size: 12px;">👥 Visibilidade Sigilosa</button>
                    <button onclick="document.getElementById('pje-bookmarklet-sigilo').remove()" style="padding: 8px 12px; border: none; border-radius: 4px; background: #f44336; color: white; cursor: pointer; font-size: 12px;">Fechar</button>
                </div>
            </div>
        `;
        document.body.appendChild(botao);

        // Tornar o botão arrastável
        let isDragging = false;
        let currentX, currentY, initialX, initialY;
        const header = botao.firstElementChild;
        
        header.addEventListener('mousedown', (e) => {
            isDragging = true;
            initialX = e.clientX - botao.offsetLeft;
            initialY = e.clientY - botao.offsetTop;
        });

        document.addEventListener('mousemove', (e) => {
            if (isDragging) {
                currentX = e.clientX - initialX;
                currentY = e.clientY - initialY;
                header.style.left = currentX + 'px';
                header.style.top = currentY + 'px';
            }
        });

        document.addEventListener('mouseup', () => {
            isDragging = false;
        });
    }

    // Função para controlar sigilo
    async function alterarSigilo(ativar = true) {
        try {
            const seletores = [
                'input.mat-slide-toggle-input[name="sigiloso"]',
                'mat-slide-toggle[name="sigiloso"] input',
                'input[name="sigiloso"]',
                '.mat-slide-toggle input[type="checkbox"]'
            ];

            let sigiloInput = null;
            for (const seletor of seletores) {
                sigiloInput = await esperarElemento(seletor);
                if (sigiloInput) break;
            }

            if (!sigiloInput) {
                console.log('[SIGILO] Campo de sigilo não encontrado');
                return false;
            }

            // Verifica estado atual
            const checked = sigiloInput.checked || 
                          sigiloInput.getAttribute('aria-checked') === 'true';

            console.log(`[SIGILO] Estado atual: ${checked ? 'ativado' : 'desativado'}, alvo: ${ativar ? 'ativar' : 'desativar'}`);

            // Executa ação se necessário
            if ((ativar && !checked) || (!ativar && checked)) {
                // Tenta clicar no input ou no container do slide toggle
                const slideToggle = sigiloInput.closest('mat-slide-toggle');
                if (slideToggle) {
                    clicarElemento(slideToggle);
                } else {
                    clicarElemento(sigiloInput);
                }
                console.log(`[SIGILO] Sigilo ${ativar ? 'ativado' : 'desativado'}`);
                return true;
            }

            console.log('[SIGILO] Nenhuma ação necessária');
            return true;

        } catch (error) {
            console.error('[SIGILO] Erro ao alterar sigilo:', error);
            return false;
        }
    }

    // Função para aplicar visibilidade sigilosa (baseada na função Fix.visibilidade_sigilosos)
    async function aplicarVisibilidadeEspecial() {
        try {
            console.log('[VISIBILIDADE] Aplicando visibilidade sigilosa...');
            
            // Busca por botões relacionados à visibilidade
            const botoes = document.querySelectorAll('button, .mat-button, .mat-raised-button');
            let botaoVisibilidade = null;
            
            for (const botao of botoes) {
                const texto = botao.textContent.toLowerCase();
                const ariaLabel = (botao.getAttribute('aria-label') || '').toLowerCase();
                
                if (texto.includes('visibilidade') || 
                    texto.includes('sigiloso') ||
                    ariaLabel.includes('visibilidade') ||
                    ariaLabel.includes('sigiloso')) {
                    botaoVisibilidade = botao;
                    break;
                }
            }

            if (botaoVisibilidade) {
                clicarElemento(botaoVisibilidade);
                console.log('[VISIBILIDADE] Botão de visibilidade clicado');
                
                // Aguarda modal abrir e procura opções específicas
                await new Promise(resolve => setTimeout(resolve, 1000));
                
                // Busca por checkbox ou opção de "Sigiloso para partes e terceiros"
                const opcoesSigilo = document.querySelectorAll('mat-checkbox, .mat-checkbox, input[type="checkbox"]');
                for (const opcao of opcoesSigilo) {
                    const label = opcao.closest('label') || opcao.nextElementSibling;
                    if (label && label.textContent.toLowerCase().includes('sigiloso')) {
                        clicarElemento(opcao);
                        console.log('[VISIBILIDADE] Opção sigilosa selecionada');
                        break;
                    }
                }
                
                // Procura botão de confirmação
                const botoesConfirmar = document.querySelectorAll('button');
                for (const botao of botoesConfirmar) {
                    const texto = botao.textContent.toLowerCase();
                    if (texto.includes('confirmar') || texto.includes('salvar') || texto.includes('ok')) {
                        clicarElemento(botao);
                        console.log('[VISIBILIDADE] Configuração confirmada');
                        break;
                    }
                }
                
                return true;
            } else {
                console.log('[VISIBILIDADE] Botão de visibilidade não encontrado');
                return false;
            }
            
        } catch (error) {
            console.error('[VISIBILIDADE] Erro:', error);
            return false;
        }
    }

    // Ativar sigilo
    window.ativarSigilo = async function() {
        console.log('[SIGILO] Ativando sigilo...');
        
        try {
            const sucesso = await alterarSigilo(true);
            if (sucesso) {
                alert('✅ Sigilo ativado com sucesso!');
            } else {
                alert('❌ Não foi possível ativar o sigilo');
            }
        } catch (error) {
            console.error('[SIGILO] Erro ao ativar:', error);
            alert('❌ Erro ao ativar sigilo: ' + error.message);
        }
    };

    // Desativar sigilo
    window.desativarSigilo = async function() {
        console.log('[SIGILO] Desativando sigilo...');
        
        try {
            const sucesso = await alterarSigilo(false);
            if (sucesso) {
                alert('✅ Sigilo desativado com sucesso!');
            } else {
                alert('❌ Não foi possível desativar o sigilo');
            }
        } catch (error) {
            console.error('[SIGILO] Erro ao desativar:', error);
            alert('❌ Erro ao desativar sigilo: ' + error.message);
        }
    };

    // Verificar status do sigilo
    window.verificarSigilo = async function() {
        console.log('[SIGILO] Verificando status...');
        
        try {
            const seletores = [
                'input.mat-slide-toggle-input[name="sigiloso"]',
                'mat-slide-toggle[name="sigiloso"] input',
                'input[name="sigiloso"]',
                '.mat-slide-toggle input[type="checkbox"]'
            ];

            let sigiloInput = null;
            for (const seletor of seletores) {
                sigiloInput = await esperarElemento(seletor);
                if (sigiloInput) break;
            }

            if (sigiloInput) {
                const checked = sigiloInput.checked || 
                              sigiloInput.getAttribute('aria-checked') === 'true';
                
                const status = checked ? '🔒 ATIVADO' : '🔓 DESATIVADO';
                alert(`Status do Sigilo: ${status}`);
            } else {
                alert('❌ Campo de sigilo não encontrado na tela atual');
            }
            
        } catch (error) {
            console.error('[SIGILO] Erro ao verificar:', error);
            alert('❌ Erro ao verificar sigilo: ' + error.message);
        }
    };

    // Aplicar visibilidade sigilosa
    window.aplicarVisibilidadeSigilosa = async function() {
        console.log('[VISIBILIDADE] Aplicando visibilidade sigilosa...');
        
        try {
            const sucesso = await aplicarVisibilidadeEspecial();
            if (sucesso) {
                alert('✅ Visibilidade sigilosa aplicada!');
            } else {
                alert('❌ Não foi possível aplicar visibilidade sigilosa.\nVerifique se está na tela correta.');
            }
        } catch (error) {
            console.error('[VISIBILIDADE] Erro:', error);
            alert('❌ Erro ao aplicar visibilidade: ' + error.message);
        }
    };

    // Criar interface
    criarBotaoFlutuante();
    
})();
