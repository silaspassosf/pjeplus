import importlib
modules = [
    'Fix','atos','Mandado','SISB','PEC','Prazo','Peticao','AVJT','Agente','SISB'
]
results = {}
for m in modules:
    try:
        importlib.import_module(m)
        results[m] = 'OK'
    except Exception as e:
        results[m] = f'ERR: {e!r}'

for k,v in results.items():
    print(f"{k}: {v}")
