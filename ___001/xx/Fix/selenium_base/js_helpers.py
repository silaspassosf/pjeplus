import logging
logger = logging.getLogger(__name__)

"""
@module: Fix.selenium_base.js_helpers
@responsibility: Utilitários JavaScript para operações no browser
@depends_on: selenium.webdriver
@used_by: element_interaction, smart_selection
@entry_points: js_base
@tags: #javascript #browser #mutationobserver #events
@created: 2026-02-06
@refactored_from: Fix/core.py lines 1218-1350
"""

def js_base() -> str:
    """
    Funções JavaScript base usando MutationObserver (padrão gigs.py)
    Substitui polling Python por espera passiva no browser
    
    Funções disponíveis:
    - esperarElemento(seletor, timeout): Aguarda elemento aparecer
    - triggerEvent(elemento, tipo): Dispara evento (input, change, blur)
    - esperarOpcoes(seletor, timeout): Aguarda opções de dropdown
    
    Returns:
        String com código JavaScript pronto para execute_script/execute_async_script
    
    Exemplo:
        script = f"{js_base()}; return await esperarElemento('#meuId', 5000);"
        elemento = driver.execute_async_script(script)
    """
    # Usar implementação mais avançada do SISB se disponível
    try:
        from SISB.utils import criar_js_otimizado
        return criar_js_otimizado()
    except ImportError:
        # Fallback para implementação original
        return """
        function esperarElemento(seletor, timeout = 5000) {
            return new Promise(resolve => {
                let elemento = document.querySelector(seletor);
                let disabled = (elemento && elemento.disabled === undefined) ? false : elemento.disabled;
                if (elemento && !disabled) {
                    resolve(elemento);
                    return;
                }
                
                let observer = new MutationObserver(mutations => {
                    let elem = document.querySelector(seletor);
                    let disabled = (elem && elem.disabled === undefined) ? false : elem.disabled;
                    if (elem && !disabled) {
                        observer.disconnect();
                        resolve(elem);
                    }
                });
                
                observer.observe(document.body, { childList: true, subtree: true });
                setTimeout(() => { 
                    observer.disconnect(); 
                    resolve(null); 
                }, timeout);
            });
        }
        
        function triggerEvent(elemento, tipo) {
            if (!elemento) return;
            if ('createEvent' in document) {
                let evento = document.createEvent('HTMLEvents');
                evento.initEvent(tipo, true, true);
                elemento.dispatchEvent(evento);
            } else {
                elemento.dispatchEvent(new Event(tipo, { bubbles: true }));
            }
        }
        
        function esperarOpcoes(seletor = 'mat-option[role="option"]', timeout = 5000) {
            return new Promise(resolve => {
                let opcoes = document.querySelectorAll(seletor);
                if (opcoes.length > 0) {
                    resolve(opcoes);
                    return;
                }
                
                let observer = new MutationObserver(mutations => {
                    let opts = document.querySelectorAll(seletor);
                    if (opts.length > 0) {
                        observer.disconnect();
                        resolve(opts);
                    }
                });
                
                observer.observe(document.body, { childList: true, subtree: true });
                setTimeout(() => { 
                    observer.disconnect(); 
                    resolve([]); 
                }, timeout);
            });
        }
        """