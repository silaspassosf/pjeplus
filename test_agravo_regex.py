"""Teste para validar o fix do regex agravo_exequente_interlocutoria."""
import re
import sys
sys.path.insert(0, r'd:\PjePlus')
from Fix.utils import normalizar_texto

# Simular o texto da imagem normalizado
texto_imagem = normalizar_texto(
    'Vistos, etc.\n\nInterposto Agravo de Peticao pela parte EXEQUENTE, contra despacho ID 48b1dff, '
    'que se encontra tempestivo e subscrito por advogado regularmente constituido nos autos.\n\n'
    'Nesta Especializada, os despachos de mero expediente e as decisoes de natureza interlocutoria sao '
    'irrecorriveis, conforme interpretacao da Sumula 214 do TST e do proprio art. 893, par. 1 da CLT.\n\n'
    'O apelo apresentado busca reforma da decisao nao terminativa, razao pela qual deixo de receber o '
    'Agravo de Peticao apresentado, diante da manifesta ausencia de pressupostos de admissibilidade.\n\n'
    'SAO PAULO/SP, 17 de junho de 2026.'
)

# Testar o NOVO padrao (sem DOTALL, usando [\s\S]*)
novo = re.compile(r'(?=[\s\S]*interlocutoria)(?=[\s\S]*interposto[\s\n\r]*agravo[\s\n\r]*de[\s\n\r]*peticao[\s\n\r]*pela[\s\n\r]*parte[\s\n\r]*exequente)', re.IGNORECASE)

# Testar o ANTIGO padrao (sem flags no registry = sem DOTALL)
antigo_sem_dotall = re.compile(r'^(?=.*interlocutoria)(?=.*interposto[\s\n\r]*agravo[\s\n\r]*de[\s\n\r]*peticao[\s\n\r]*pela[\s\n\r]*parte[\s\n\r]*exequente)', re.IGNORECASE)
antigo_com_dotall = re.compile(r'^(?=.*interlocutoria)(?=.*interposto[\s\n\r]*agravo[\s\n\r]*de[\s\n\r]*peticao[\s\n\r]*pela[\s\n\r]*parte[\s\n\r]*exequente)', re.IGNORECASE | re.DOTALL)

print('Texto normalizado (primeiros 150 chars):', repr(texto_imagem[:150]))
print()
print('ANTIGO sem DOTALL (era o que o registry usava) =>', bool(antigo_sem_dotall.search(texto_imagem)))
print('ANTIGO com DOTALL (como foi escrito originalmente) =>', bool(antigo_com_dotall.search(texto_imagem)))
print('NOVO (usa [\\s\\S]*, sem DOTALL) =>', bool(novo.search(texto_imagem)))
