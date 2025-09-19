"""
Processador de Timeline para análise de prescrição
Substitui a função monolítica analisar_timeline_prescreve_js_puro()
"""

from ..utils.js_helpers import TimelineJSAnalyzer


class TimelineProcessor:
    """
    Processador especializado para análise de timeline
    Responsável por extrair e processar documentos da timeline judicial
    """

    def __init__(self, debug=False):
        """
        Inicializa o processador de timeline

        Args:
            debug (bool): Habilita modo debug
        """
        self.debug = debug
        self.js_analyzer = TimelineJSAnalyzer()

    def analyze_timeline(self, driver):
        """
        Analisa a timeline completa do processo usando JavaScript

        Args:
            driver: Instância do WebDriver

        Returns:
            list: Lista de documentos encontrados na timeline
        """
        try:
            print('[TIMELINE_PROCESSOR] Iniciando análise da timeline...')

            # Usar o analisador JavaScript extraído
            documentos = self.js_analyzer.execute_timeline_analysis(driver)

            if self.debug:
                print(f'[TIMELINE_PROCESSOR][DEBUG] Documentos encontrados: {len(documentos)}')
                for i, doc in enumerate(documentos[:5]):  # Mostra apenas os primeiros 5
                    print(f'[TIMELINE_PROCESSOR][DEBUG] {i+1}. {doc["tipo"]}: {doc["texto"][:50]}...')

            print(f'[TIMELINE_PROCESSOR] ✅ Análise concluída: {len(documentos)} documentos')
            return documentos

        except Exception as e:
            print(f'[TIMELINE_PROCESSOR] ❌ Erro na análise: {e}')
            return []

    def filter_documents_by_type(self, documents, document_types):
        """
        Filtra documentos por tipos específicos

        Args:
            documents (list): Lista de documentos
            document_types (list): Tipos de documento para filtrar

        Returns:
            list: Documentos filtrados
        """
        if not document_types:
            return documents

        filtered = []
        for doc in documents:
            if doc.get('tipo', '').lower() in [t.lower() for t in document_types]:
                filtered.append(doc)

        if self.debug:
            print(f'[TIMELINE_PROCESSOR] Filtrados {len(filtered)} documentos dos tipos: {document_types}')

        return filtered

    def get_documents_summary(self, documents):
        """
        Gera um resumo dos documentos encontrados

        Args:
            documents (list): Lista de documentos

        Returns:
            dict: Resumo por tipo de documento
        """
        summary = {}
        for doc in documents:
            doc_type = doc.get('tipo', 'Desconhecido')
            if doc_type not in summary:
                summary[doc_type] = []
            summary[doc_type].append({
                'id': doc.get('id', ''),
                'data': doc.get('data', ''),
                'texto': doc.get('texto', '')[:100] + '...' if len(doc.get('texto', '')) > 100 else doc.get('texto', ''),
                'isAnexo': doc.get('isAnexo', False)
            })

        return summary