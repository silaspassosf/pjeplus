# ====================================================================
# SISTEMA UNIFICADO DE PROGRESSO
# Módulo centralizado para controle de progresso entre todos os scripts
# ====================================================================

import os
import json
import time
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

class ProgressoUnificado:
    """
    Sistema unificado de controle de progresso para todos os módulos (PEC, P2B, M1, SISBAJUD)
    """
    
    def __init__(self, modulo: str = "GERAL"):
        """
        Inicializa o sistema de progresso para um módulo específico
        
        Args:
            modulo: Nome do módulo (PEC, P2B, M1, SISBAJUD, etc.)
        """
        self.modulo = modulo.upper()
        self.arquivo_principal = "progresso.json"  # Arquivo único unificado
        self.arquivo_backup = f"progresso_{modulo.lower()}.json"  # Para migração apenas
        
    def carregar_progresso(self) -> List[str]:
        """
        Carrega o progresso em formato simples - apenas lista de processos executados
        
        Returns:
            Lista de números de processos já executados
        """
        try:
            # Tentar carregar arquivo simples primeiro
            if os.path.exists(self.arquivo_principal):
                with open(self.arquivo_principal, "r", encoding="utf-8") as f:
                    dados_simples = json.load(f)
                    
                    # Validar estrutura simples
                    if not isinstance(dados_simples, dict):
                        raise ValueError("Dados simples inválidos")
                    
                    # Obter dados do módulo
                    modulo_data = dados_simples.get(self.modulo, [])
                    
                    # Se for dict (formato completo), extrair apenas a lista de processos
                    if isinstance(modulo_data, dict):
                        processos = modulo_data.get("processos_executados", [])
                    else:
                        # Se for lista direta, usar como está
                        processos = modulo_data if isinstance(modulo_data, list) else []
                    
                    print(f"[PROGRESSO_{self.modulo}] [OK] Progresso carregado: {len(processos)} processos executados")
                    
                    # ✨ NOVO: Verificar e limpar automaticamente se passou 2+ dias
                    if self._deve_limpar_progresso_antigo(dados_simples):
                        print(f"[PROGRESSO_{self.modulo}] 🧹 Detectado progresso de mais de 2 dias - limpando...")
                        processos = self._limpar_progresso_automaticamente(dados_simples)
                    
                    return processos
            
            # Fallback: tentar migrar do arquivo antigo
            elif os.path.exists(self.arquivo_backup):
                print(f"[PROGRESSO_{self.modulo}]  Migrando arquivo antigo para sistema simples...")
                return self._migrar_arquivo_antigo_simples()
            
        except (json.JSONDecodeError, ValueError, FileNotFoundError) as e:
            print(f"[PROGRESSO_{self.modulo}][AVISO] Arquivo corrompido ou inválido: {e}")
        except Exception as e:
            print(f"[PROGRESSO_{self.modulo}][AVISO] Erro inesperado ao carregar: {e}")
        
        # Retornar lista vazia
        return []
    
    def _deve_limpar_progresso_antigo(self, dados: Dict) -> bool:
        """
        Verifica se o progresso deve ser limpo baseado na data de execução
        
        Args:
            dados: Dados carregados do arquivo de progresso
            
        Returns:
            True se passou mais de 2 dias desde a última execução
        """
        try:
            modulo_data = dados.get(self.modulo, {})
            
            # Se não tem timestamp de última execução, não limpar
            if not isinstance(modulo_data, dict):
                return False
            
            ultima_execucao_str = modulo_data.get("ultima_execucao")
            if not ultima_execucao_str:
                return False
            
            # Parse da data de última execução
            ultima_execucao = datetime.fromisoformat(ultima_execucao_str)
            agora = datetime.now()
            
            # Calcular diferença em dias
            diferenca_dias = (agora - ultima_execucao).days
            
            # Se passou mais de 2 dias
            if diferenca_dias > 2:
                print(f"[PROGRESSO_{self.modulo}] ⏱️ {diferenca_dias} dias desde última execução (limite: 2 dias)")
                return True
            
            return False
            
        except Exception as e:
            print(f"[PROGRESSO_{self.modulo}] ⚠️ Erro ao verificar data de execução: {e}")
            return False
    
    def _limpar_progresso_automaticamente(self, dados: Dict) -> List[str]:
        """
        Limpa automaticamente o progresso quando detecta execução após 2+ dias
        
        Args:
            dados: Dados atuais do arquivo de progresso
            
        Returns:
            Lista limpa (vazia) de processos executados
        """
        try:
            modulo_data = dados.get(self.modulo, {})
            
            # Salvar histórico da limpeza
            if not isinstance(modulo_data, dict):
                modulo_data = {}
            
            # Arquivar lista anterior antes de limpar
            lista_anterior = modulo_data.get("processos_executados", [])
            timestamp_limpeza = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if lista_anterior:
                # Manter referência do que foi limpo
                modulo_data["historico_antes_limpeza"] = lista_anterior
                modulo_data["data_limpeza"] = timestamp_limpeza
                
                print(f"[PROGRESSO_{self.modulo}]  Histórico preservado em 'historico_antes_limpeza' ({len(lista_anterior)} processos)")
            
            # Limpar lista de processos executados
            modulo_data["processos_executados"] = []
            modulo_data["ultima_limpeza"] = datetime.now().isoformat()
            modulo_data["ultima_execucao"] = datetime.now().isoformat()
            
            # Atualizar dados
            dados[self.modulo] = modulo_data
            
            # Salvar arquivo atualizado
            with open(self.arquivo_principal, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=4, ensure_ascii=False)
            
            print(f"[PROGRESSO_{self.modulo}] ✅ Progresso limpo com sucesso. Lista resetada para início de nova sessão.")
            
            return []
            
        except Exception as e:
            print(f"[PROGRESSO_{self.modulo}] ❌ Erro ao limpar progresso: {e}")
            return []
    
    def salvar_progresso(self, processos_executados: List[str]) -> bool:
        """
        Salva o progresso em formato simples
        
        Args:
            processos_executados: Lista de processos executados
            
        Returns:
            True se salvou com sucesso, False caso contrário
        """
        try:
            # Carregar dados simples existentes
            dados_simples = {}
            if os.path.exists(self.arquivo_principal):
                try:
                    with open(self.arquivo_principal, "r", encoding="utf-8") as f:
                        dados_simples = json.load(f)
                except Exception:
                    dados_simples = {}
            
            # Garantir estrutura básica para todos os módulos
            for modulo in ["M1", "P2B", "PEC", "SISBAJUD", "MANDADO"]:
                if modulo not in dados_simples:
                    dados_simples[modulo] = {
                        "processos_executados": [],
                        "ultima_execucao": datetime.now().isoformat(),
                        "ultima_limpeza": datetime.now().isoformat(),
                        "processos_com_erro": [],
                        "session_active": True
                    }
            
            # Atualizar dados do módulo atual
            if self.modulo not in dados_simples:
                dados_simples[self.modulo] = {
                    "processos_executados": [],
                    "ultima_execucao": datetime.now().isoformat(),
                    "ultima_limpeza": datetime.now().isoformat(),
                    "processos_com_erro": [],
                    "session_active": True
                }
            
            # Garantir que os campos necessários existem
            modulo_data = dados_simples[self.modulo]
            if not isinstance(modulo_data, dict):
                modulo_data = {}
            
            modulo_data["processos_executados"] = processos_executados
            modulo_data["ultima_execucao"] = datetime.now().isoformat()  # ✨ Atualizar timestamp
            
            if "ultima_limpeza" not in modulo_data:
                modulo_data["ultima_limpeza"] = datetime.now().isoformat()
            
            if "processos_com_erro" not in modulo_data:
                modulo_data["processos_com_erro"] = []
            
            if "session_active" not in modulo_data:
                modulo_data["session_active"] = True
            
            dados_simples[self.modulo] = modulo_data
            
            # Salvar arquivo simples
            with open(self.arquivo_principal, "w", encoding="utf-8") as f:
                json.dump(dados_simples, f, indent=4, ensure_ascii=False)
            
            print(f"[PROGRESSO_{self.modulo}] [OK] Progresso salvo: {len(processos_executados)} processos no arquivo {self.arquivo_principal}")
            return True
            
        except Exception as e:
            print(f"[PROGRESSO_{self.modulo}][ERRO] Falha ao salvar progresso: {e}")
            return False
            return False
            self._atualizar_estatisticas_gerais(dados_unificados)
            
            # Salvar arquivo unificado
            with open(self.arquivo_principal, "w", encoding="utf-8") as f:
                json.dump(dados_unificados, f, ensure_ascii=False, indent=2)
            
            # Manter compatibilidade com sistema antigo
            self._salvar_arquivo_compatibilidade(progresso_modulo)
            
            return True
            
        except Exception as e:
            print(f"[PROGRESSO_{self.modulo}][ERRO] Falha ao salvar: {e}")
            return False
    
    def processo_ja_executado(self, numero_processo: str, progresso: Optional[List] = None) -> bool:
        """
        Verifica se um processo já foi executado com sucesso
        
        Args:
            numero_processo: Número do processo a verificar
            progresso: Lista de progresso (carrega automaticamente se None)
            
        Returns:
            True se o processo já foi executado com sucesso, False caso contrário
        """
        if progresso is None:
            progresso = self.carregar_progresso()
        
        # Verificar na lista simples de executados
        return numero_processo in progresso
        
        return False
    
    def marcar_processo_executado(self, numero_processo: str, status: str = "SUCESSO", 
                                 detalhes: Optional[str] = None, progresso: Optional[List] = None) -> List:
        """
        Marca um processo como executado no formato simples.
        
        Args:
            numero_processo: Número do processo
            status: Status da execução (SUCESSO, ERRO_TEMPORARIO, ERRO_PERMANENTE)
            detalhes: Detalhes adicionais sobre a execução
            progresso: Lista de progresso (carrega automaticamente se None)
            
        Returns:
            Lista de progresso atualizada
        """
        if progresso is None:
            progresso = self.carregar_progresso()
        
        # Verificar se há erros críticos que impedem marcar como executado
        erro_critico = self._detectar_erro_critico(detalhes)
        
        if erro_critico:
            print(f"[PROGRESSO_{self.modulo}]  ERRO CRÍTICO detectado - NÃO marcando {numero_processo} como executado")
            print(f"[PROGRESSO_{self.modulo}]  Detalhes: {erro_critico}")
            # Não adiciona à lista para permitir reprocessamento
            return progresso
        
        # No formato simples, só adiciona à lista se teve sucesso e não está lá ainda
        if status == "SUCESSO" and numero_processo not in progresso:
            progresso.append(numero_processo)
            print(f"[PROGRESSO_{self.modulo}] [OK] Processo {numero_processo} marcado como executado")
        elif status in ["ERRO_TEMPORARIO", "ERRO_PERMANENTE"]:
            print(f"[PROGRESSO_{self.modulo}] [INFO] Processo {numero_processo} com {status} - não adicionado à lista")
        
        # Salvar progresso atualizado
        self.salvar_progresso(progresso)
        
        return progresso
    
    def _detectar_erro_critico(self, detalhes: Optional[str] = None) -> Optional[str]:
        """
        Detecta se os detalhes contêm erros críticos que impedem marcar como executado.
        
        Args:
            detalhes: Detalhes da execução
            
        Returns:
            Descrição do erro crítico ou None se não for crítico
        """
        if not detalhes:
            return None
            
        detalhes_lower = detalhes.lower()
        
        # Erros críticos que indicam que o processo NÃO foi executado
        erros_criticos = [
            'invalid session id', 'invalidsessionidexception',
            'session not found', 'no such session',
            'connection refused', 'connection reset',
            'webdriver exception', 'unable to establish connection',
            'chrome not reachable', 'firefox not reachable'
        ]
        
        for erro in erros_criticos:
            if erro in detalhes_lower:
                return f"Erro crítico detectado: {erro}"
        
        return None
    
    def _validar_sucesso_real(self, status: str, detalhes: Optional[str] = None) -> bool:
        """
        Valida se o processo realmente teve sucesso, não apenas foi marcado como tal.
        
        Args:
            status: Status reportado
            detalhes: Detalhes da execução
            
        Returns:
            True se realmente teve sucesso, False caso contrário
        """
        # Se status não é SUCESSO, definitivamente não teve sucesso
        if status != "SUCESSO":
            return False
        
        # Se há detalhes que indicam erro, mesmo com status SUCESSO, não é sucesso real
        if detalhes:
            detalhes_lower = detalhes.lower()
            
            # Padrões que indicam erro REAL (mais específicos)
            padroes_erro = [
                'erro:', 'error:', 'falha:', 'failed:', 'exception', 'timeout',
                'não foi possível', 'falhou', 'stale', 'selenium',
                'webdriver', 'connection error', 'network error',
                'elemento não encontrado', 'page not found'
            ]
            
            for padrao in padroes_erro:
                if padrao in detalhes_lower:
                    print(f"[PROGRESSO_VALIDAÇÃO] ❌ Sucesso falso detectado - padrão '{padrao}' encontrado em: '{detalhes}'")
                    return False
            
            # Padrões que são POSITIVOS mesmo contendo palavras que poderiam confundir
            padroes_positivos = [
                'sem problemas', 'sem erro', 'concluída', 'concluído', 'executado com êxito',
                'processado com sucesso', 'finalizado', 'completado'
            ]
            
            for padrao in padroes_positivos:
                if padrao in detalhes_lower:
                    # É um padrão positivo, continuar validação
                    break
        
        # Se passou em todas as validações, é sucesso real
        return True
    
    def gerar_relatorio_simples(self) -> str:
        """
        Gera relatório SIMPLES e DIRETO - apenas módulo e lista de processos executados COM SUCESSO REAL.
        
        Returns:
            String com relatório simples e limpo
        """
        try:
            progresso = self.carregar_progresso()
            processos_executados = progresso.get("processos_executados", [])
            ultima_atualizacao = progresso.get("last_update", "N/A")
            
            relatorio = f"""
=== RELATÓRIO SIMPLES - {self.modulo} ===
Total de processos executados COM SUCESSO REAL: {len(processos_executados)}
Última atualização: {ultima_atualizacao}

Processos executados com sucesso:
"""
            
            if not processos_executados:
                relatorio += "   Nenhum processo executado com sucesso ainda.\n"
            else:
                for i, processo in enumerate(processos_executados, 1):
                    relatorio += f"   {i:2d}. {processo}\n"
            
            relatorio += f"\n=== FIM RELATÓRIO {self.modulo} ===\n"
            
            return relatorio
            
        except Exception as e:
            return f"ERRO ao gerar relatório para {self.modulo}: {e}"
    
    def obter_estatisticas(self) -> Dict:
        """
        Obtém estatísticas detalhadas do progresso
        
        Returns:
            Dicionário com estatísticas completas
        """
        try:
            if os.path.exists(self.arquivo_principal):
                with open(self.arquivo_principal, "r", encoding="utf-8") as f:
                    dados_unificados = json.load(f)
                    
                    modulo_data = dados_unificados.get("modulos", {}).get(self.modulo, {})
                    stats_gerais = dados_unificados.get("estatisticas_gerais", {})
                    
                    return {
                        "modulo": self.modulo,
                        "processos_executados": len(modulo_data.get("processos_executados", [])),
                        "processos_erro_permanente": len(modulo_data.get("processos_erro_permanente", [])),
                        "processos_tentativas": len(modulo_data.get("processos_tentativas", {})),
                        "ultimo_update": modulo_data.get("last_update"),
                        "session_active": modulo_data.get("session_active", False),
                        "estatisticas_gerais": stats_gerais
                    }
        except Exception as e:
            print(f"[PROGRESSO_{self.modulo}] ❌ Erro ao obter estatísticas: {e}")
        
        return {"modulo": self.modulo, "erro": "Não foi possível carregar estatísticas"}
    
    def resetar_progresso(self, manter_historico: bool = True) -> bool:
        """
        Reseta o progresso do módulo
        
        Args:
            manter_historico: Se True, mantém o histórico de execuções
            
        Returns:
            True se resetou com sucesso
        """
        try:
            progresso = self.carregar_progresso()
            
            if manter_historico:
                # Fazer backup do histórico
                historico = progresso.get("historico_execucoes", [])
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"historico_{self.modulo.lower()}_{timestamp}.json"
                
                try:
                    with open(backup_path, "w", encoding="utf-8") as f:
                        json.dump({"historico": historico}, f, ensure_ascii=False, indent=2)
                    print(f"[PROGRESSO_{self.modulo}]  Histórico salvo em: {backup_path}")
                except Exception as e:
                    print(f"[PROGRESSO_{self.modulo}] ⚠️ Erro ao salvar histórico: {e}")
            
            # Criar estrutura limpa
            progresso_limpo = self._estrutura_modulo_padrao()
            
            # Manter histórico se solicitado
            if manter_historico and "historico_execucoes" in progresso:
                progresso_limpo["historico_execucoes"] = progresso["historico_execucoes"]
            
            # Salvar progresso limpo
            self.salvar_progresso(progresso_limpo)
            
            print(f"[PROGRESSO_{self.modulo}] ✅ Progresso resetado com sucesso")
            return True
            
        except Exception as e:
            print(f"[PROGRESSO_{self.modulo}] ❌ Erro ao resetar progresso: {e}")
            return False
    
    def _estrutura_modulo_padrao(self) -> Dict:
        """Retorna a estrutura padrão para um módulo"""
        return {
            "processos_executados": [],
            "processos_erro_permanente": [],
            "processos_tentativas": {},
            "historico_execucoes": [],
            "total_executados": 0,
            "total_erros_permanentes": 0,
            "session_active": True,
            "created_at": datetime.now().isoformat(),
            "last_update": None
        }
    
    def _migrar_arquivo_antigo(self) -> Dict:
        """Migra arquivo do sistema antigo para o unificado"""
        try:
            with open(self.arquivo_backup, "r", encoding="utf-8") as f:
                dados_antigos = json.load(f)
            
            # Converter para nova estrutura
            modulo_data = self._estrutura_modulo_padrao()
            modulo_data["processos_executados"] = dados_antigos.get("processos_executados", [])
            modulo_data["session_active"] = dados_antigos.get("session_active", True)
            modulo_data["total_executados"] = len(modulo_data["processos_executados"])
            
            # Criar backup do arquivo antigo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_antigo = f"{self.arquivo_backup}.backup_{timestamp}"
            shutil.copy(self.arquivo_backup, backup_antigo)
            
            # Salvar no sistema unificado
            self.salvar_progresso(modulo_data)
            
            print(f"[PROGRESSO_{self.modulo}] ✅ Migração concluída. Backup: {backup_antigo}")
            return modulo_data
            
        except Exception as e:
            print(f"[PROGRESSO_{self.modulo}] ❌ Erro na migração: {e}")
            return self._estrutura_modulo_padrao()
    
    def _migrar_arquivo_antigo_simples(self) -> List[str]:
        """Migra arquivo do sistema antigo para o formato simples"""
        try:
            with open(self.arquivo_backup, "r", encoding="utf-8") as f:
                dados_antigos = json.load(f)
            
            # Extrair lista de processos executados
            processos_executados = dados_antigos.get("processos_executados", [])
            
            # Criar backup do arquivo antigo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_antigo = f"{self.arquivo_backup}.backup_{timestamp}"
            shutil.copy(self.arquivo_backup, backup_antigo)
            
            # Salvar no sistema simples
            self.salvar_progresso(processos_executados)
            
            print(f"[PROGRESSO_{self.modulo}] ✅ Migração simples concluída. Backup: {backup_antigo}")
            return processos_executados
            
        except Exception as e:
            print(f"[PROGRESSO_{self.modulo}] ❌ Erro na migração simples: {e}")
            return []
    
    def _criar_estrutura_limpa(self) -> Dict:
        """Cria e salva uma estrutura limpa"""
        dados_limpos = self._estrutura_modulo_padrao()
        self.salvar_progresso(dados_limpos)
        print(f"[PROGRESSO_{self.modulo}] ✅ Estrutura limpa criada")
        return dados_limpos
    
    def _salvar_modulo_no_unificado(self, dados_unificados: Dict, modulo_data: Dict):
        """Salva dados do módulo no arquivo unificado"""
        if "modulos" not in dados_unificados:
            dados_unificados["modulos"] = {}
        dados_unificados["modulos"][self.modulo] = modulo_data
        
        with open(self.arquivo_principal, "w", encoding="utf-8") as f:
            json.dump(dados_unificados, f, ensure_ascii=False, indent=2)
    
    def _criar_backup_corrompido(self):
        """Cria backup de arquivo corrompido"""
        try:
            if os.path.exists(self.arquivo_principal):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"progresso_unificado_backup_{timestamp}.json"
                shutil.copy(self.arquivo_principal, backup_path)
                print(f"[PROGRESSO_{self.modulo}]  Backup de arquivo corrompido: {backup_path}")
        except Exception as e:
            print(f"[PROGRESSO_{self.modulo}] ⚠️ Erro ao criar backup: {e}")
    
    def _salvar_arquivo_compatibilidade(self, progresso_modulo: Dict):
        """Mantém arquivo de compatibilidade com sistema antigo"""
        try:
            # Estrutura simplificada para compatibilidade
            dados_compatibilidade = {
                "processos_executados": progresso_modulo.get("processos_executados", []),
                "session_active": progresso_modulo.get("session_active", True),
                "last_update": progresso_modulo.get("last_update")
            }
            
            with open(self.arquivo_backup, "w", encoding="utf-8") as f:
                json.dump(dados_compatibilidade, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"[PROGRESSO_{self.modulo}] ⚠️ Erro ao manter compatibilidade: {e}")
    
    def _atualizar_estatisticas_gerais(self, dados_unificados: Dict):
        """Atualiza estatísticas gerais consolidadas"""
        try:
            modulos = dados_unificados.get("modulos", {})
            
            total_processos = 0
            total_erros = 0
            modulos_ativos = 0
            
            for nome_modulo, dados_modulo in modulos.items():
                total_processos += len(dados_modulo.get("processos_executados", []))
                total_erros += len(dados_modulo.get("processos_erro_permanente", []))
                if dados_modulo.get("session_active", False):
                    modulos_ativos += 1
            
            dados_unificados["estatisticas_gerais"] = {
                "total_processos_executados": total_processos,
                "total_erros_permanentes": total_erros,
                "total_modulos": len(modulos),
                "modulos_ativos": modulos_ativos,
                "ultima_atualizacao": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"[PROGRESSO_GERAL] ⚠️ Erro ao atualizar estatísticas gerais: {e}")
    
    def _remover_de_listas_erro(self, progresso: Dict, numero_processo: str):
        """Remove processo das listas de erro quando executado com sucesso"""
        # Remover de erros permanentes
        if "processos_erro_permanente" in progresso:
            if numero_processo in progresso["processos_erro_permanente"]:
                progresso["processos_erro_permanente"].remove(numero_processo)
        
        # Remover contadores de tentativas
        if "processos_tentativas" in progresso:
            if numero_processo in progresso["processos_tentativas"]:
                del progresso["processos_tentativas"][numero_processo]
    
    def _registrar_historico(self, progresso: Dict, numero_processo: str, 
                           status: str, detalhes: Optional[str], timestamp: str):
        """Registra entrada no histórico de execuções"""
        if "historico_execucoes" not in progresso:
            progresso["historico_execucoes"] = []
        
        entrada_historico = {
            "processo": numero_processo,
            "status": status,
            "timestamp": timestamp,
            "modulo": self.modulo
        }
        
        if detalhes:
            entrada_historico["detalhes"] = detalhes
        
        progresso["historico_execucoes"].append(entrada_historico)
        
        # Manter apenas últimas 1000 entradas para evitar arquivo muito grande
        if len(progresso["historico_execucoes"]) > 1000:
            progresso["historico_execucoes"] = progresso["historico_execucoes"][-1000:]


# ====================================================================
# FUNÇÕES DE CONVENIÊNCIA PARA COMPATIBILIDADE
# ====================================================================

def inicializar_progresso_unificado(modulo: str) -> ProgressoUnificado:
    """
    Função de conveniência para inicializar o sistema unificado
    
    Args:
        modulo: Nome do módulo (PEC, P2B, M1, SISBAJUD)
        
    Returns:
        Instância do ProgressoUnificado
    """
    return ProgressoUnificado(modulo)

def carregar_progresso_modulo(modulo: str) -> Dict:
    """
    Função de conveniência para carregar progresso de um módulo
    
    Args:
        modulo: Nome do módulo
        
    Returns:
        Dados de progresso do módulo
    """
    sistema = ProgressoUnificado(modulo)
    return sistema.carregar_progresso()

def salvar_progresso_modulo(modulo: str, progresso: Dict) -> bool:
    """
    Função de conveniência para salvar progresso de um módulo
    
    Args:
        modulo: Nome do módulo
        progresso: Dados de progresso
        
    Returns:
        True se salvou com sucesso
    """
    sistema = ProgressoUnificado(modulo)
    return sistema.salvar_progresso(progresso)

def marcar_processo_executado_modulo(modulo: str, numero_processo: str, 
                                   status: str = "SUCESSO", detalhes: Optional[str] = None) -> Dict:
    """
    Função de conveniência para marcar processo como executado
    
    Args:
        modulo: Nome do módulo
        numero_processo: Número do processo
        status: Status da execução
        detalhes: Detalhes adicionais
        
    Returns:
        Progresso atualizado
    """
    sistema = ProgressoUnificado(modulo)
    return sistema.marcar_processo_executado(numero_processo, status, detalhes)

def processo_ja_executado_modulo(modulo: str, numero_processo: str) -> bool:
    """
    Função de conveniência para verificar se processo já foi executado
    
    Args:
        modulo: Nome do módulo
        numero_processo: Número do processo
        
    Returns:
        True se já foi executado
    """
    sistema = ProgressoUnificado(modulo)
    return sistema.processo_ja_executado(numero_processo)