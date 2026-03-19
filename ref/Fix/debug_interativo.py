"""
Fix/debug_interativo.py
Sistema de debug interativo - pausa execuo em erros crticos para anlise
"""
import os
import time
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from selenium.webdriver.remote.webdriver import WebDriver


class DebugInterativo:
    """
    Sistema de debug que pausa execuo em erros crticos.
    Permite anlise e correo interativa de problemas headless.
    """
    
    # Padres de erro que devem pausar execuo
    ERROS_CRITICOS = [
        'click intercepted',
        'element click intercepted',
        'obscures it',
        'not clickable at point',
        'backdrop',
        'overlay',
        'timeout',
        'timed out',
        'no such element',
        'stale element',
    ]
    
    def __init__(self, enabled: bool = False, debug_dir: str = "debug_interativo", 
                 auto_mode: bool = False):
        self.enabled = enabled
        self.auto_mode = auto_mode  #  NOVO: Modo automtico (sem input humano)
        self.debug_dir = debug_dir
        self.erro_count = 0
        self.pausa_count = 0
        self.screenshots_salvos = []
        self.erros_log = []  #  NOVO: Log de erros para anlise automtica
        
        if enabled and not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
    
    def is_erro_critico(self, erro_msg: str) -> bool:
        """Verifica se erro  crtico o suficiente para pausar"""
        if not erro_msg:
            return False
        
        erro_lower = str(erro_msg).lower()
        return any(padrao in erro_lower for padrao in self.ERROS_CRITICOS)
    
    def capturar_contexto(self, driver: WebDriver, erro_msg: str) -> Dict[str, Any]:
        """Captura screenshot e contexto do DOM para anlise"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        contexto = {
            'timestamp': timestamp,
            'erro_msg': erro_msg,
            'url': None,
            'screenshot': None,
            'html': None,
            'overlays': [],
        }
        
        try:
            # URL atual
            contexto['url'] = driver.current_url
        except:
            pass
        
        try:
            # Screenshot
            screenshot_path = os.path.join(self.debug_dir, f'erro_{timestamp}.png')
            driver.save_screenshot(screenshot_path)
            contexto['screenshot'] = screenshot_path
            self.screenshots_salvos.append(screenshot_path)
            print(f" Screenshot salvo: {screenshot_path}")
        except Exception as e:
            print(f" Erro ao salvar screenshot: {e}")
        
        try:
            # Detectar overlays/backdrops no DOM
            overlays = driver.execute_script("""
                const overlays = [];
                
                // Backdrops CDK
                document.querySelectorAll('.cdk-overlay-backdrop').forEach(el => {
                    overlays.push({
                        type: 'cdk-backdrop',
                        classes: el.className,
                        visible: el.offsetParent !== null,
                        zIndex: window.getComputedStyle(el).zIndex
                    });
                });
                
                // Modals
                document.querySelectorAll('.modal-backdrop, .fade.show').forEach(el => {
                    overlays.push({
                        type: 'modal-backdrop',
                        classes: el.className,
                        visible: el.offsetParent !== null
                    });
                });
                
                // Elementos com z-index alto
                const allElements = document.querySelectorAll('*');
                allElements.forEach(el => {
                    const zIndex = parseInt(window.getComputedStyle(el).zIndex);
                    if (zIndex > 1000 && el.offsetParent !== null) {
                        overlays.push({
                            type: 'high-zindex',
                            tag: el.tagName,
                            classes: el.className,
                            zIndex: zIndex
                        });
                    }
                });
                
                return overlays;
            """)
            contexto['overlays'] = overlays
            if overlays:
                print(f" Overlays detectados: {len(overlays)}")
                for ov in overlays[:3]:  # Mostrar primeiros 3
                    print(f"   - {ov.get('type')}: z-index={ov.get('zIndex', 'N/A')}")
        except:
            pass
        
        try:
            # HTML da pgina (ltimas 5000 chars)
            html_path = os.path.join(self.debug_dir, f'dom_{timestamp}.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            contexto['html'] = html_path
            print(f" HTML salvo: {html_path}")
        except Exception as e:
            print(f" Erro ao salvar HTML: {e}")
        
        return contexto
    
    def pausar_para_analise(self, driver: WebDriver, erro_msg: str, contexto_extra: dict = None) -> str:
        """
        Pausa execucao em modo interativo para analise de erro.
        Em modo auto, aplica fix automatico e continua.
        
        Returns:
            'c' = continuar
            's' = skip (pular este item)
            'a' = abortar execucao
            'f' = fix (tentar correcao automatica)
        """
        if not self.enabled:
            return 'c'  # Modo debug desabilitado, continuar
        
        self.pausa_count += 1
        
        #  NOVO: Registrar erro para anlise posterior
        erro_info = {
            'numero': self.pausa_count,
            'mensagem': erro_msg[:500],
            'contexto': contexto_extra,
            'timestamp': datetime.now().isoformat()
        }
        self.erros_log.append(erro_info)
        
        print("\n" + "=" * 80)
        print(" DEBUG INTERATIVO - ERRO CRTICO DETECTADO")
        print("=" * 80)
        print(f"Pausa #{self.pausa_count} | Erros totais: {self.erro_count}")
        print(f"\n Erro: {erro_msg[:200]}")
        
        # Capturar contexto
        contexto = self.capturar_contexto(driver, erro_msg)
        
        if contexto_extra:
            print(f"\n Contexto adicional:")
            for key, value in contexto_extra.items():
                print(f"   {key}: {value}")
        
        #  NOVO: Modo automtico - aplica fix e continua
        if self.auto_mode:
            print("\n MODO AUTOMTICO ATIVADO")
            print("   Aplicando correo automtica...")
            self._tentar_fix_automatico(driver)
            
            # Salvar relatrio do erro
            self._salvar_relatorio_erro(erro_info, contexto)
            
            print("    Continuando execuo automaticamente...")
            return 'f'  # Fix aplicado
        
        # Menu de opes
        print("\n" + "-" * 80)
        print("OPES:")
        print("  [C] Continuar - Tenta continuar execuo")
        print("  [S] Skip - Pula este item e vai para o prximo")
        print("  [F] Fix - Tenta correo automtica (limpa overlays)")
        print("  [I] Info - Mostra mais informaes do erro")
        print("  [A] Abortar - Para execuo completamente")
        print("-" * 80)
        
        while True:
            try:
                escolha = input("\n Escolha uma opo [C/S/F/I/A]: ").strip().upper()
                
                if escolha == 'C':
                    print(" Continuando execuo...")
                    return 'c'
                
                elif escolha == 'S':
                    print(" Pulando item atual...")
                    return 's'
                
                elif escolha == 'F':
                    print(" Tentando correo automtica...")
                    self._tentar_fix_automatico(driver)
                    return 'f'
                
                elif escolha == 'I':
                    self._mostrar_info_detalhada(contexto)
                    continue
                
                elif escolha == 'A':
                    print(" Abortando execuo...")
                    return 'a'
                
                else:
                    print(" Opo invlida. Use C, S, F, I ou A.")
            
            except (KeyboardInterrupt, EOFError):
                print("\n Interrompido pelo usurio - Abortando")
                return 'a'
    
    def _tentar_fix_automatico(self, driver: WebDriver):
        """Tenta correes automticas conhecidas"""
        print(" Aplicando correes automticas:")
        
        try:
            # 1. Limpar overlays
            print("   - Limpando overlays...")
            from Fix.headless_helpers import limpar_overlays_headless
            limpar_overlays_headless(driver)
            time.sleep(0.5)
            print("    Overlays limpos")
        except Exception as e:
            print(f"    Erro ao limpar overlays: {e}")
        
        try:
            # 2. Scroll para topo
            print("   - Scroll para topo da pgina...")
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.3)
            print("    Scroll realizado")
        esalvar_relatorio_erro(self, erro_info: Dict, contexto: Dict):
        """Salva relatrio detalhado do erro para anlise"""
        try:
            relatorio_path = os.path.join(self.debug_dir, f'erro_{erro_info["numero"]:03d}_relatorio.json')
            relatorio = {
                **erro_info,
                'screenshot': contexto.get('screenshot'),
                'html': contexto.get('html'),
                'url': contexto.get('url'),
                'overlays_count': len(contexto.get('overlays', [])),
                'overlays': contexto.get('overlays', [])[:5],  # Primeiros 5
            }
            
            import json
            with open(relatorio_path, 'w', encoding='utf-8') as f:
                json.dump(relatorio, f, indent=2, ensure_ascii=False)
            
            print(f"    Relatrio salvo: {relatorio_path}")
        except Exception as e:
            print(f"    Erro ao salvar relatrio: {e}")
    
    def obter_relatorio_final(self) -> Dict[str, Any]:
        """Retorna relatrio final de todos os erros encontrados"""
        return {
            'total_erros': self.erro_count,
            'total_pausas': self.pausa_count,
            'screenshots': self.screenshots_salvos,
            'erros_detalhados': self.erros_log,
            'modo_automatico': self.auto_mode,
        }
    
    def _xcept Exception as e:
            print(f"    Erro no scroll: {e}")
        
        try:,
                                auto_mode: bool = False) -> DebugInterativo:
    """
    Inicializa sistema de debug interativo
    
    Args:
        enabled: Ativa/desativa debug
        debug_dir: Diretrio para screenshots/logs
        auto_mode: Modo automtico (aplica fixes sem input humano)
    """
    global _debug
    _debug = DebugInterativo(enabled=enabled, debug_dir=debug_dir, auto_mode=auto_mode)
    if enabled:
        modo = "AUTOMTICO " if auto_mode else "INTERATIVO "
        print(f" Debug {modo}torAll('.modal .close, .modal button[aria-label*="fechar"]').forEach(el => {
                    el.click();
                });
                
                // Pressionar ESC
                document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape'}));
            """)
            time.sleep(0.5)
            print("    Modals processados")
        except Exception as e:
            print(f"    Erro ao fechar modals: {e}")
        
        print(" Correes automticas aplicadas")
    
    def _mostrar_info_detalhada(self, contexto: Dict[str, Any]):
        """Mostra informaes detalhadas do erro"""
        print("\n" + "=" * 80)
        print(" INFORMAES DETALHADAS")
        print("=" * 80)
        
        print(f"\n Timestamp: {contexto['timestamp']}")
        print(f" URL: {contexto['url']}")
        print(f" Screenshot: {contexto['screenshot']}")
        print(f" HTML: {contexto['html']}")
        
        if contexto['overlays']:
            print(f"\n Overlays encontrados ({len(contexto['overlays'])}):")
            for ov in contexto['overlays']:
                print(f"   - Tipo: {ov.get('type')}")
                print(f"     Classes: {ov.get('classes', 'N/A')}")
                print(f"     Z-Index: {ov.get('zIndex', 'N/A')}")
                print(f"     Visvel: {ov.get('visible', 'N/A')}")
                print()
        else:
            print("\n Nenhum overlay detectado")
        
        print("\n SUGESTES:")
        print("   1. Abra o screenshot para ver estado visual")
        print("   2. Verifique o HTML para encontrar elementos bloqueadores")
        print("   3. Use opo [F] para tentar correo automtica")
        print("   4. Se persistir, reporte o erro com screenshot/HTML")
        print("=" * 80)


# Singleton global
_debug = None


def obter_relatorio_debug() -> Optional[Dict[str, Any]]:
    """Obtm relatrio final do debug (para anlise automtica)"""
    debug = get_debug_interativo()
    if debug:
        return debug.obter_relatorio_final()
    return None


def inicializar_debug_interativo(enabled: bool = True, debug_dir: str = "debug_interativo") -> DebugInterativo:
    """Inicializa sistema de debug interativo"""
    global _debug
    _debug = DebugInterativo(enabled=enabled, debug_dir=debug_dir)
    if enabled:
        print(f" Debug interativo ATIVADO - Pasta: {debug_dir}")
    return _debug


def get_debug_interativo() -> Optional[DebugInterativo]:
    """Retorna instncia do debug interativo (ou None se no inicializado)"""
    return _debug


def on_erro_critico(driver: WebDriver, erro_msg: str, 
                   contexto: Optional[Dict] = None) -> str:
    """
    Callback para ser chamado quando erro crtico ocorre.
    
    Returns:
        'c' = continuar, 's' = skip, 'a' = abortar, 'f' = fix
    """
    debug = get_debug_interativo()
    if not debug or not debug.enabled:
        return 'c'
    
    debug.erro_count += 1
    
    if debug.is_erro_critico(erro_msg):
        return debug.pausar_para_analise(driver, erro_msg, contexto)
    
    return 'c'


def is_debug_ativo() -> bool:
    """Verifica se debug interativo est ativo"""
    debug = get_debug_interativo()
    return debug is not None and debug.enabled
