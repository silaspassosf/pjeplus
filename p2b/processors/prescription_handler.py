"""
Handler de Prescrição - Coordena BNDT, Timeline e PEC
Substitui a função monolítica prescreve() que fazia tudo
"""

from ..processors.timeline_processor import TimelineProcessor
from ..core.state_manager import StateManager


class PrescriptionHandler:
    """
    Handler especializado para processamento de prescrição
    Coordena as operações de BNDT, análise de timeline e PEC
    """

    def __init__(self, bndt_service=None, pec_service=None, debug=False):
        """
        Inicializa o handler de prescrição

        Args:
            bndt_service: Serviço BNDT (opcional, será criado se não fornecido)
            pec_service: Serviço PEC (opcional, será criado se não fornecido)
            debug (bool): Habilita modo debug
        """
        self.debug = debug
        self.timeline_processor = TimelineProcessor(debug=debug)
        self.state_manager = StateManager()

        # Serviços (serão implementados nas próximas fases)
        self.bndt_service = bndt_service
        self.pec_service = pec_service

    def handle_prescription(self, driver, process_id=None):
        """
        Processa prescrição completa: BNDT + Timeline + PEC

        Args:
            driver: Instância do WebDriver
            process_id (str): ID do processo (opcional)

        Returns:
            dict: Resultado do processamento
        """
        try:
            print('[PRESCRIPTION_HANDLER] Iniciando processamento de prescrição...')

            result = {
                'success': False,
                'bndt_result': None,
                'timeline_documents': [],
                'pec_result': None,
                'process_id': process_id,
                'errors': []
            }

            # 1. Verificar se processo já foi executado
            if process_id and self.state_manager.is_process_executed(process_id):
                print(f'[PRESCRIPTION_HANDLER] Processo {process_id} já foi executado')
                result['already_executed'] = True
                result['success'] = True
                return result

            # 2. Executar BNDT (se serviço disponível)
            if self.bndt_service:
                try:
                    print('[PRESCRIPTION_HANDLER] Executando BNDT...')
                    bndt_result = self.bndt_service.execute_exclusion(driver)
                    result['bndt_result'] = bndt_result
                    print(f'[PRESCRIPTION_HANDLER] BNDT concluído: {bndt_result}')
                except Exception as e:
                    error_msg = f'Erro no BNDT: {e}'
                    print(f'[PRESCRIPTION_HANDLER] ❌ {error_msg}')
                    result['errors'].append(error_msg)
            else:
                print('[PRESCRIPTION_HANDLER] ⚠️ Serviço BNDT não disponível')

            # 3. Analisar timeline
            try:
                print('[PRESCRIPTION_HANDLER] Analisando timeline...')
                documents = self.timeline_processor.analyze_timeline(driver)
                result['timeline_documents'] = documents

                if self.debug:
                    print(f'[PRESCRIPTION_HANDLER][DEBUG] {len(documents)} documentos encontrados')

            except Exception as e:
                error_msg = f'Erro na análise de timeline: {e}'
                print(f'[PRESCRIPTION_HANDLER] ❌ {error_msg}')
                result['errors'].append(error_msg)
                documents = []

            # 4. Processar PEC (se serviço disponível e documentos encontrados)
            if self.pec_service and documents:
                try:
                    print('[PRESCRIPTION_HANDLER] Processando PEC...')
                    pec_result = self.pec_service.process_exclusions(driver, documents)
                    result['pec_result'] = pec_result
                    print(f'[PRESCRIPTION_HANDLER] PEC concluído: {pec_result}')
                except Exception as e:
                    error_msg = f'Erro no PEC: {e}'
                    print(f'[PRESCRIPTION_HANDLER] ❌ {error_msg}')
                    result['errors'].append(error_msg)
            else:
                if not self.pec_service:
                    print('[PRESCRIPTION_HANDLER] ⚠️ Serviço PEC não disponível')
                if not documents:
                    print('[PRESCRIPTION_HANDLER] ⚠️ Nenhum documento para processar PEC')

            # 5. Marcar como executado se teve sucesso
            if not result['errors']:
                result['success'] = True
                if process_id:
                    self.state_manager.mark_process_executed(process_id)
                    self.state_manager.update_statistics(success=True)
                print('[PRESCRIPTION_HANDLER] ✅ Prescrição processada com sucesso')
            else:
                if process_id:
                    self.state_manager.update_statistics(success=False)
                print(f'[PRESCRIPTION_HANDLER] ⚠️ Prescrição processada com {len(result["errors"])} erros')

            return result

        except Exception as e:
            error_msg = f'Erro geral no processamento de prescrição: {e}'
            print(f'[PRESCRIPTION_HANDLER] ❌ {error_msg}')
            result['errors'].append(error_msg)
            if process_id:
                self.state_manager.update_statistics(success=False)
            return result

    def get_prescription_summary(self, result):
        """
        Gera um resumo do resultado da prescrição

        Args:
            result (dict): Resultado do processamento

        Returns:
            str: Resumo formatado
        """
        summary = []
        summary.append("=== RESUMO DA PRESCRIÇÃO ===")
        summary.append(f"Sucesso: {'✅' if result.get('success') else '❌'}")
        summary.append(f"Processo: {result.get('process_id', 'N/A')}")

        if result.get('already_executed'):
            summary.append("Status: Já executado anteriormente")

        if result.get('bndt_result'):
            summary.append(f"BNDT: {result['bndt_result']}")

        documents = result.get('timeline_documents', [])
        summary.append(f"Documentos na timeline: {len(documents)}")

        if documents:
            doc_types = {}
            for doc in documents:
                doc_type = doc.get('tipo', 'Desconhecido')
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1

            summary.append("Tipos de documento:")
            for doc_type, count in doc_types.items():
                summary.append(f"  - {doc_type}: {count}")

        if result.get('pec_result'):
            summary.append(f"PEC: {result['pec_result']}")

        errors = result.get('errors', [])
        if errors:
            summary.append(f"Erros ({len(errors)}):")
            for error in errors:
                summary.append(f"  - {error}")

        return "\n".join(summary)