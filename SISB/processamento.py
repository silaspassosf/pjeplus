"""SISB.processamento - Compat wrapper com shim de pacote."""

import os as _os
from importlib import import_module as _import_module

__path__ = [_os.path.join(_os.path.dirname(__file__), 'processamento')]

_validacao = _import_module(__name__ + '.validacao')
_minutas_campos = _import_module(__name__ + '.minutas_campos')

_validar_dados = _validacao._validar_dados
_preencher_campos_iniciais = _minutas_campos._preencher_campos_iniciais

from .processamento_minuta import minuta_bloqueio_refatorada
from .processamento_campos import (
    _preencher_campos_principais,
    _processar_reus_otimizado,
    _configurar_valor,
    _configurar_opcoes_adicionais,
)
from .processamento_relatorios import (
    _salvar_minuta,
    _gerar_relatorio_minuta,
    _salvar_relatorios,
    _finalizar_minuta,
)
from .processamento_extracao import _extrair_cpf_autor, _extrair_nome_autor
from .processamento_ordens_processamento import _processar_ordem

__all__ = [
    'minuta_bloqueio_refatorada',
    '_validar_dados',
    '_preencher_campos_iniciais',
    '_preencher_campos_principais',
    '_processar_reus_otimizado',
    '_configurar_valor',
    '_configurar_opcoes_adicionais',
    '_salvar_minuta',
    '_gerar_relatorio_minuta',
    '_salvar_relatorios',
    '_finalizar_minuta',
    '_extrair_cpf_autor',
    '_extrair_nome_autor',
    '_processar_ordem',
]
