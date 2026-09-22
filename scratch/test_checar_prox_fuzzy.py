import re
from Fix.utils import normalizar_texto

# Exatamente como em Prazo/p2b_documentos.py
pats = [
    re.compile(r'\bin\w*r\b[^\n]*?\bseus\b[^\n]*?\bdados\b[^\n]*?\bbancari\w*\b', re.IGNORECASE),
    re.compile(r'\bindicac\w*\b[^\n]*?\bdados\b[^\n]*?\bbancari\w*\b', re.IGNORECASE),
    re.compile(r'\bindic\w*\b[^\n]*?\bendereco\b[^\n]*?\bcomplet\w*\b', re.IGNORECASE),
]

casos = [
    # (texto bruto, esperado)
    ("Intime-se a parte autora para indicar seus dados bancários.", True),
    ("intime-se a reclamante para incluir seus dados bancários no sistema", True),
    ("deverá inserir seus dados bancários", True),
    ("apresentar indicação de dados bancários válidos", True),
    ("apresentar a indicação dos dados bancários para bloqueio", True),
    ("favor indicar o endereço completo da parte", True),
    ("deve indicar, corretamente, o endereco completo", True),
    ("indicar\nseus dados bancarios em outra linha", False),  # cruzou linha
    ("a parte indicaraendereco", False),  # sem espaco: indicara + endereco colados
]

for bruto, esperado in casos:
    t = normalizar_texto(bruto)
    hits = [i for i, p in enumerate(pats) if p.search(t)]
    ok = (bool(hits) == esperado)
    print(("OK  " if ok else "FAIL"), bruto[:60], "->", hits)
