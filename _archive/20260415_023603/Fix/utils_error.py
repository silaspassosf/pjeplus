import logging
logger = logging.getLogger(__name__)

"""
Fix.utils_error - Módulo de tratamento de erros para PJe automação.

Parte da refatoração do Fix.utils.py para melhor granularidade IA.
"""

import datetime
from typing import List, Dict, Any, Optional

# =============================
# COLETOR DE ERROS (ex-Core)
# =============================
class ErroCollector:
    """
    Coleta erros sem interromper execução
    Permite processar tudo e gerar relatório completo no final
    """

    def __init__(self) -> None:
        self.erros: List[Dict[str, Any]] = []
        self.sucessos: List[str] = []

    def registrar_erro(self, processo: str, erro: Any, modulo: str = "") -> None:
        """Registra erro mas NÃO interrompe execução"""
        self.erros.append({
            'processo': processo,
            'erro': str(erro),
            'modulo': modulo,
            'timestamp': datetime.datetime.now().strftime('%H:%M:%S')
        })
        print(f" Erro em {processo}: {str(erro)[:100]}")

    def registrar_sucesso(self, processo: str) -> None:
        """Registra processamento bem-sucedido"""
        self.sucessos.append(processo)

    def gerar_relatorio(self) -> None:
        """Imprime relatório completo de execução"""
        total = len(self.sucessos) + len(self.erros)
        taxa_sucesso = (len(self.sucessos) / total * 100) if total > 0 else 0

        print("\n" + "="*70)
        print("="*70)
        print(f"Total processados: {total}")
        print(f" Sucessos: {len(self.sucessos)} ({taxa_sucesso:.1f}%)")
        print(f" Erros: {len(self.erros)} ({100-taxa_sucesso:.1f}%)")

        if self.erros:
            print("\n" + "="*70)
            print("DETALHES DOS ERROS:")
            print("="*70)
            for erro in self.erros:
                print(f"\n📋 Processo: {erro['processo']}")
                if erro['modulo']:
                    print(f"   Módulo: {erro['modulo']}")
                print(f"   Erro: {erro['erro'][:200]}")
                print(f"   Horário: {erro['timestamp']}")

        print("\n" + "="*70)

    def exportar_csv(self, arquivo: str = 'erros.csv') -> None:
        """Exporta erros para CSV para análise posterior"""
        if not self.erros:
            logger.error("Nenhum erro para exportar")
            return

        import csv
        with open(arquivo, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Processo', 'Módulo', 'Erro', 'Timestamp'])
            for erro in self.erros:
                writer.writerow([
                    erro['processo'],
                    erro['modulo'],
                    erro['erro'],
                    erro['timestamp']
                ])