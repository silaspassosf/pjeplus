# pec.py
import time, re, unicodedata, json
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from datetime import datetime, timedelta

# =============================================
# CLASSE PRINCIPAL - GERENCIADOR DE FLUXO PEC
# =============================================

class PECFluxo:
    def __init__(self, driver=None):
        self.driver = driver
        self.siscon_login_feito = False
        self.progresso = {"processos_executados": [], "session_active": True, "last_update": None}
        
    # =============================================
    # MÉTODOS DE CONTROLE DE SESSÃO
    # =============================================
    
    def fazer_login_siscon_manual(self, debug=False):
        """Login manual no Siscon/Alvará Eletrônico"""
        if self.siscon_login_feito:
            return True
            
        try:
            url_login = "https://alvaraeletronico.trt2.jus.br/portaltrtsp/login.jsp"
            self.driver.get(url_login)
            time.sleep(3)
            
            print("\n" + "🚨" * 20)
            print("INSTRUÇÕES PARA LOGIN:")
            print("1. Faça login no sistema que apareceu no navegador")
            print("2. Complete a autenticação (inclusive token do email se necessário)")
            print("3. Após fazer login com sucesso, volte aqui e pressione ENTER")
            print("4. NÃO feche o navegador!")
            print("🚨" * 20 + "\n")
            
            input("⏳ Pressione ENTER após completar o login no navegador...")
            
            url_busca = "https://alvaraeletronico.trt2.jus.br/portaltrtsp/pages/movimentacao/conta/buscar"
            self.driver.get(url_busca)
            time.sleep(5)
            
            if 'login.jsp' in self.driver.current_url:
                print("\n⚠️ ERRO: Login não foi completado corretamente")
                return False
            elif 'buscar' in self.driver.current_url:
                self.siscon_login_feito = True
                print("\n🎉 LOGIN REALIZADO COM SUCESSO!")
                return True
            else:
                self.siscon_login_feito = True
                return True
                
        except Exception as e:
            print(f"❌ Erro durante login manual: {e}")
            return False
    
    # =============================================
    # MÉTODOS DE INDEXAÇÃO E EXTRAÇÃO
    # =============================================
    
    def indexar_processo_atual_gigs(self):
        """Extrai número do processo e observação da página atual"""
        try:
            # Extrair número do processo
            url_atual = self.driver.current_url
            numero_processo = None
            
            if "processo" in url_atual:
                match = re.search(r'processo/(\d+)', url_atual)
                if match:
                    numero_processo = match.group(1)
            
            if not numero_processo:
                candidatos = self.driver.find_elements(By.CSS_SELECTOR, 
                    'h1, h2, h3, .processo-numero, [data-testid*="numero"], .cabecalho')
                for elemento in candidatos:
                    texto = elemento.text.strip()
                    match = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', texto)
                    if match:
                        numero_processo = match.group(1)
                        break
            
            if not numero_processo:
                numero_processo = f"PROC_{hash(url_atual) % 1000000}"
            
            # Extrair observação
            observacao = ""
            elementos_descricao = self.driver.find_elements(By.CSS_SELECTOR, 'span.descricao')
            for elemento in elementos_descricao:
                texto_completo = elemento.text.strip()
                if texto_completo.startswith('Prazo:'):
                    observacao = texto_completo[6:].strip().lower().rstrip('.')
                    break
            
            if not observacao:
                texto_pagina = self.driver.page_source.lower()
                padroes = ['xs carta', 'xs pec cp', 'xs pec edital', 'xs bloq', 'sob chip', 'sobrestamento vencido']
                for padrao in padroes:
                    if padrao in texto_pagina:
                        observacao = padrao
                        break
            
            if not observacao:
                observacao = "observacao nao encontrada"
            
            return (numero_processo, observacao)
            
        except Exception as e:
            print(f"[INDEXAR_GIGS] ❌ Erro: {e}")
            return None
    
    # =============================================
    # MÉTODOS DE DETERMINAÇÃO DE AÇÕES
    # =============================================
    
    def determinar_acao_por_observacao(self, observacao):
        """Determina a ação baseada na observação"""
        observacao_lower = observacao.lower().strip()
        
        if re.search(r'\bsob\s+\d+', observacao_lower):
            return "mov_sob"
        elif "sob chip" in observacao_lower:
            return "def_chip"
        elif "sobrestamento vencido" in observacao_lower:
            return "def_sob"
        elif "xs pec cp" in observacao_lower:
            return "pec_cpgeral"
        elif "xs pec edital" in observacao_lower:
            return "pec_editaldec"
        elif "pec dec" in observacao_lower:
            return "pec_decisao"
        elif "pec idpj" in observacao_lower:
            return "pec_editalidpj"
        elif "pz idpj" in observacao_lower:
            return "ato_idpj"
        elif "xs carta" in observacao_lower:
            return "carta"
        elif "xs bloq" in observacao_lower:
            return "pec_bloqueio"
        elif "xs parcial" in observacao_lower:
            return "ato_bloq"
        elif "meios" in observacao_lower:
            return "ato_meios"
        elif "aud" in observacao_lower:
            return "pec_editalaud"
        else:
            return "PULAR"
    
    # =============================================
    # MÉTODOS DE EXECUÇÃO DE AÇÕES
    # =============================================
    
    def executar_acao(self, acao, numero_processo, observacao):
        """Executa a ação determinada"""
        print(f"[AÇÃO] Executando '{acao}' para processo {numero_processo}")
        
        try:
            if acao == "carta":
                from carta import carta
                return bool(carta(self.driver, log=True))
            elif acao == "mov_sob":
                from atos import mov_sob
                return bool(mov_sob(self.driver, numero_processo, observacao))
            elif acao == "def_chip":
                from atos import def_chip
                return bool(def_chip(self.driver, numero_processo, observacao, debug=True))
            elif acao == "def_sob":
                return self.def_sob(numero_processo, observacao, debug=True)
            elif acao == "pec_cpgeral":
                from atos import pec_cpgeral
                return bool(pec_cpgeral(self.driver, debug=True))
            elif acao == "pec_editaldec":
                from atos import pec_editaldec
                return bool(pec_editaldec(self.driver, debug=True))
            elif acao == "pec_decisao":
                from atos import pec_decisao
                return bool(pec_decisao(self.driver, debug=True))
            elif acao == "pec_editalidpj":
                from atos import pec_editalidpj
                return bool(pec_editalidpj(self.driver, debug=True))
            elif acao == "ato_idpj":
                from atos import ato_idpj
                return bool(ato_idpj(self.driver, debug=True))
            elif acao == "pec_bloqueio":
                from atos import pec_bloqueio
                return bool(pec_bloqueio(self.driver, debug=True))
            elif acao == "ato_bloq":
                from atos import ato_bloq
                return bool(ato_bloq(self.driver, debug=True))
            elif acao == "saldo":
                return self.saldo(numero_processo, observacao, debug=True)
            elif acao == "pec_editalaud":
                from atos import pec_editalaud
                return bool(pec_editalaud(self.driver, debug=True))
            else:
                print(f"[AÇÃO] ❌ Ação '{acao}' não reconhecida")
                return False
        except Exception as e:
            print(f"[AÇÃO] Erro ao executar '{acao}': {e}")
            return False
    
    # =============================================
    # MÉTODOS DE NAVEGAÇÃO
    # =============================================
    
    def navegar_para_atividades(self):
        """Navega para a tela de atividades do GIGS"""
        try:
            url_atividades = 'https://pje.trt2.jus.br/pjekz/gigs/relatorios/atividades'
            self.driver.get(url_atividades)
            time.sleep(3)
            return 'atividades' in self.driver.current_url
        except Exception as e:
            print(f"[NAVEGAR] Erro: {e}")
            return False
    
    def aplicar_filtro_xs(self):
        """Aplica filtro 'xs' na tela de atividades do GIGS"""
        try:
            btn_fa_pen = self.driver.find_element(By.CSS_SELECTOR, 'i.fa-pen')
            btn_fa_pen.click()
            time.sleep(2)
            
            campo_descricao = self.driver.find_element(By.CSS_SELECTOR, 'input[aria-label*="Descrição"]')
            campo_descricao.clear()
            campo_descricao.send_keys('xs')
            campo_descricao.send_keys(Keys.ENTER)
            
            print('[FILTRO_XS] ✅ Filtro aplicado')
            time.sleep(3)
            return True
        except Exception as e:
            print(f"[FILTRO_XS] ❌ Erro: {e}")
            return False
    
    # =============================================
    # MÉTODOS DE ANÁLISE DE DOCUMENTOS
    # =============================================
    
    def def_sob(self, numero_processo, observacao, debug=False, timeout=10):
        """Analisa última decisão e executa ação baseada no conteúdo"""
        try:
            # Selecionar última decisão
            itens = self.driver.find_elements(By.CSS_SELECTOR, 'li.tl-item-container')
            if not itens:
                return False
            
            doc_encontrado = None
            doc_link = None
            
            # Procurar documento relevante
            for idx, item in enumerate(itens):
                try:
                    link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                    doc_text = link.text.lower()
                    
                    if re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                        mag_icons = item.find_elements(By.CSS_SELECTOR, 'div.tl-icon[aria-label*="Magistrado"]')
                        if mag_icons:
                            doc_encontrado = item
                            doc_link = link
                            break
                except Exception:
                    continue
            
            if not doc_encontrado:
                for item in itens:
                    try:
                        link = item.find_element(By.CSS_SELECTOR, 'a.tl-documento:not([target="_blank"])')
                        doc_text = link.text.lower()
                        if re.search(r'despacho|decisão|sentença|conclusão', doc_text):
                            doc_encontrado = item
                            doc_link = link
                            break
                    except Exception:
                        continue
            
            if not doc_encontrado or not doc_link:
                return False
            
            # Extrair data da decisão
            data_decisao_str = None
            try:
                hora_element = doc_encontrado.find_element(By.CSS_SELECTOR, '.tl-item-hora')
                if hora_element:
                    title_attr = hora_element.get_attribute('title')
                    if title_attr:
                        data_decisao_str = title_attr.split(' ')[0]
            except Exception:
                pass
            
            # Extrair conteúdo
            doc_link.click()
            time.sleep(2)
            
            from Fix import extrair_documento
            texto_tuple = extrair_documento(self.driver, timeout=timeout, log=debug)
            if not texto_tuple or not texto_tuple[0]:
                return False
            
            texto = texto_tuple[0].lower()
            
            # Aplicar regras
            def normalizar(txt):
                return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn').lower()
            
            texto_normalizado = normalizar(texto)
            
            # Regras
            regras = [
                (['precatório', 'RPV', 'pequeno valor'], self._executar_mov_sob_precatorio),
                (['juízo universal'], self._executar_juizo_universal),
                (['prazo prescricional'], lambda: self.def_presc(numero_processo, texto, data_decisao_str, debug=debug)),
                (['atos principais'], self._executar_ato_prov),
                (['andamento da penhora no rosto'], self._executar_ato_x90),
            ]
            
            for termos, acao_func in regras:
                for termo in termos:
                    if re.search(r'\b' + re.escape(termo) + r'\b', texto_normalizado):
                        return acao_func()
            
            return False
            
        except Exception as e:
            print(f"[DEF_SOB] ❌ Erro: {e}")
            return False
    
    def _executar_mov_sob_precatorio(self):
        """Executa mov_sob com 1 mês para precatório/RPV/pequeno valor"""
        try:
            from atos import mov_sob
            return mov_sob(self.driver, None, "sob 1", debug=True)
        except Exception as e:
            print(f"[DEF_SOB] Erro em mov_sob: {e}")
            return False
    
    def _executar_juizo_universal(self):
        """Executa sequência mov_fimsob + ato_fal"""
        try:
            abas_antes = self.driver.window_handles
            aba_atual = self.driver.current_window_handle
            
            from atos import mov_fimsob
            if not mov_fimsob(self.driver):
                return False
            
            if aba_atual in self.driver.window_handles:
                self.driver.switch_to.window(aba_atual)
            
            from atos import ato_fal
            return ato_fal(self.driver)
        except Exception as e:
            print(f"[DEF_SOB] Erro em juízo universal: {e}")
            return False
    
    def _executar_ato_prov(self):
        """Executa sequência mov_fimsob + ato_prov"""
        try:
            abas_antes = self.driver.window_handles
            aba_atual = self.driver.current_window_handle
            
            from atos import mov_fimsob
            if not mov_fimsob(self.driver):
                return False
            
            if aba_atual in self.driver.window_handles:
                self.driver.switch_to.window(aba_atual)
            
            from atos import ato_prov
            return ato_prov(self.driver)
        except Exception as e:
            print(f"[DEF_SOB] Erro em autos principais: {e}")
            return False
    
    def _executar_ato_x90(self):
        """Executa sequência mov_fimsob + ato_x90"""
        try:
            abas_antes = self.driver.window_handles
            aba_atual = self.driver.current_window_handle
            
            from atos import mov_fimsob
            if not mov_fimsob(self.driver):
                return False
            
            if aba_atual in self.driver.window_handles:
                self.driver.switch_to.window(aba_atual)
            
            from atos import ato_x90
            return ato_x90(self.driver)
        except Exception as e:
            print(f"[DEF_SOB] Erro em andamento da penhora: {e}")
            return False
    
    def def_presc(self, numero_processo, texto_decisao, data_decisao_str=None, debug=False):
        """Analisa timeline para determinar prescrição"""
        try:
            data_atual = datetime.now()
            seis_meses_atras = data_atual - timedelta(days=180)
            
            # Usar data da decisão fornecida
            if not data_decisao_str:
                match = re.search(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})', texto_decisao[:500])
                if match:
                    data_decisao_str = match.group(1).replace('-', '/').replace('.', '/')
            
            # Analisar timeline
            seletores_timeline = [
                'li.tl-item-container',
                '.tl-data .tl-item-container', 
                '.timeline-item'
            ]
            
            itens = []
            for seletor in seletores_timeline:
                try:
                    itens = self.driver.find_elements(By.CSS_SELECTOR, seletor)
                    if itens:
                        break
                except Exception:
                    continue
            
            if not itens:
                return False
            
            # Verificar documentos do autor recentes
            def extrair_data_item(item):
                try:
                    return item.find_element(By.CSS_SELECTOR, '.tl-item-hora').get_attribute('title')
                except Exception:
                    return None
            
            for item in itens:
                data_item = extrair_data_item(item)
                if data_item:
                    try:
                        data_item = datetime.strptime(data_item.split(' ')[0], '%d/%m/%Y')
                        if data_item > seis_meses_atras:
                            # Documento recente encontrado
                            return True
                    except Exception:
                        continue
            
            return False
            
        except Exception as e:
            print(f"[DEF_PRESC] ❌ Erro: {e}")
            return False
    
    def saldo(self, numero_processo, observacao, debug=False):
        """Analisa alvará e consulta sistemas"""
        # Placeholder para implementação
        print(f"[SALDO] Processando saldo para {numero_processo}")
        return True
    
    # =============================================
    # MÉTODO PRINCIPAL DE FLUXO
    # =============================================
    
    def executar_fluxo_novo(self):
        """Executa o fluxo principal do PEC"""
        try:
            # Criar driver e login
            from driver_config import criar_driver, login_func
            self.driver = criar_driver(headless=False)
            if not self.driver or not login_func(self.driver):
                return False
            
            # Navegar para atividades
            if not self.navegar_para_atividades():
                return False
            
            time.sleep(5)
            
            # Aplicar filtro de 100 itens
            from Fix import aplicar_filtro_100
            if aplicar_filtro_100(self.driver):
                time.sleep(2)
            
            # Callback de processamento
            def callback_processo(driver_processo):
                try:
                    todas_abas_inicio = driver_processo.window_handles
                    aba_lista_gigs = todas_abas_inicio[0] if len(todas_abas_inicio) > 1 else None
                    
                    processo_atual = self.indexar_processo_atual_gigs()
                    if not processo_atual:
                        return
                    
                    numero_processo, observacao = processo_atual
                    acao = self.determinar_acao_por_observacao(observacao)
                    
                    if acao == "PULAR":
                        return
                    
                    # Executar ação
                    if acao == "carta":
                        from carta import carta
                        carta(driver_processo)
                    elif acao == "pec_cpgeral":
                        from atos import pec_cpgeral
                        pec_cpgeral(driver_processo, debug=True)
                    elif acao == "pec_editaldec":
                        from atos import pec_editaldec
                        pec_editaldec(driver_processo, debug=True)
                    elif acao == "pec_editalidpj":
                        from atos import pec_editalidpj
                        pec_editalidpj(driver_processo, debug=True)
                    elif acao == "pec_bloqueio":
                        from atos import pec_bloqueio
                        pec_bloqueio(driver_processo, debug=True)
                    elif acao == "ato_bloq":
                        from atos import ato_bloq
                        ato_bloq(driver_processo, debug=True)
                    elif acao == "ato_idpj":
                        from atos import ato_idpj
                        ato_idpj(driver_processo, debug=True)
                    elif acao == "def_sob":
                        self.def_sob(numero_processo, observacao, debug=True)
                    elif acao == "mov_sob":
                        from atos import mov_sob
                        mov_sob(driver_processo, numero_processo, observacao, debug=True)
                    elif acao == "def_chip":
                        from atos import def_chip
                        def_chip(driver_processo, numero_processo, observacao, debug=True)
                    elif acao == "saldo":
                        self.saldo(numero_processo, observacao, debug=True)
                    
                    # Retornar à aba GIGS
                    if aba_lista_gigs and aba_lista_gigs in driver_processo.window_handles:
                        driver_processo.switch_to.window(aba_lista_gigs)
                    
                except Exception as e:
                    print(f'[CALLBACK_PEC] ERRO: {e}')
                    raise
                
                time.sleep(1)
            
            # Executar processamento
            from Fix import indexar_e_processar_lista
            indexar_e_processar_lista(self.driver, callback_processo)
            
            return True
            
        except Exception as e:
            print(f"[FLUXO_NOVO] ❌ Erro: {e}")
            return False
        finally:
            input("[FLUXO_NOVO] Pressione Enter para fechar o driver...")
            try:
                self.driver.quit()
            except:
                pass

# =============================================
# FUNÇÃO PRINCIPAL (MANTIDA PARA COMPATIBILIDADE)
# =============================================

def main():
    """Função principal - executa o novo fluxo"""
    fluxo = PECFluxo()
    return fluxo.executar_fluxo_novo()

if __name__ == "__main__":
    main()