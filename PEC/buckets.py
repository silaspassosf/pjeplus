"""PEC buckets configuration.

Each bucket maps to a tipo_atividade and optional observacao used to
query the GIGS activities API and build execution groups.
"""
from typing import List, Dict, Any

BUCKETS_PEC: List[Dict[str, Any]] = [
    {
        "tipo_atividade": "INTIMACAO",
        "observacao":     "RPV",
        "acao_pec":       "intimar_polo_ativo",
    },
    {
        "tipo_atividade": "COMUNICACAO",
        "observacao":     "PRECATORIO",
        "acao_pec":       "intimar_polo_passivo",
    },
    # Buckets encontrados no repositório / logs (strings usadas como observação
    # ou tipo nas Ações/AutoGIGS). Mantemos as strings exatamente como aparecem
    # para maximizar correspondência com a API de GIGS.
    {"tipo_atividade": "", "observacao": "xs pec", "acao_pec": "pec_generic"},
    {"tipo_atividade": "", "observacao": "xs pec cp", "acao_pec": "pec_cpgeral"},
    {"tipo_atividade": "", "observacao": "xs pec edital", "acao_pec": "pec_editaldec"},
    {"tipo_atividade": "", "observacao": "xs pec dec", "acao_pec": "pec_decisao"},
    {"tipo_atividade": "", "observacao": "xs pec idpj", "acao_pec": "pec_editalidpj"},
    {"tipo_atividade": "", "observacao": "PEC processada", "acao_pec": "pec_processada"},
    {"tipo_atividade": "", "observacao": "PEC processada - Gabinete", "acao_pec": "pec_processada_gabinete"},
    {"tipo_atividade": "", "observacao": "RPV", "acao_pec": "rpv_precatorio"},
    {"tipo_atividade": "", "observacao": "PRECATÓRIO", "acao_pec": "precatorio"},
    {"tipo_atividade": "", "observacao": "atualizacaorapidaRPVPrec", "acao_pec": "atualizacao_rapida_rpv_prec"},
    # Fallback genérico (captura ocorrências não categorizadas)
    {"tipo_atividade": "", "observacao": "pec", "acao_pec": "pec_fallback"},
]
