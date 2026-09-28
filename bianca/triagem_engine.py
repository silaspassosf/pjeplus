# -*- coding: utf-8 -*-
"""Shim de compatibilidade — delega para o pacote bianca.triagem.

Mantido para nao quebrar imports existentes:
  from bianca.triagem_engine import run_triagem   # x.py
  from bianca.triagem_engine import run_dom        # (se existir, manter)
"""
from bianca.triagem import run_triagem, triagem_peticao
from bianca.dom_engine import run_dom
