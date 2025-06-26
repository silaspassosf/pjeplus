#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Teste - Lógica de Precedência do Argos
Valida se a regra "defiro a instauração" + SISBAJUD positivo tem prioridade absoluta.
"""

def simular_aplicar_regras_argos(resultado_sisbajud, sigilo_anexos, tipo_documento, texto_documento, debug=True):
    """
    Simula a função aplicar_regras_argos para teste da lógica de precedência.
    """
    regra_aplicada = None
    acoes_executadas = []
    
    print(f"\n=== TESTE DE PRECEDÊNCIA ===")
    print(f"Tipo documento: {tipo_documento}")
    print(f"SISBAJUD: {resultado_sisbajud}")
    print(f"Sigilo anexos: {sigilo_anexos}")
    print(f"Texto contém: {[termo for termo in ['defiro a instauração', 'argos', 'tendo em vista que'] if termo in texto_documento.lower()]}")
    print("=" * 50)
    
    # PRIORIDADE ABSOLUTA: Regra "defiro a instauração" com SISBAJUD positivo
    if 'defiro a instauração' in texto_documento.lower() and resultado_sisbajud == 'positivo':
        regra_aplicada = '[PRIORIDADE] decisao+defiro a instauracao+sisbajud positivo'
        if debug:
            print('[TESTE][PRIORIDADE] ✅ REGRA DE PRECEDÊNCIA ATIVADA!')
            print('[TESTE][PRIORIDADE] defiro a instauração + SISBAJUD positivo')
            print('[TESTE][PRIORIDADE] Esta regra prevalece sobre qualquer outra')
        regra_aplicada += ' | lembrete_bloq + pec_idpj [PRECEDENCIA ABSOLUTA]'
        acoes_executadas = ['lembrete_bloq', 'pec_idpj']
    
    # Outras regras de "defiro a instauração" (sem SISBAJUD positivo)
    elif 'defiro a instauração' in texto_documento.lower():
        regra_aplicada = 'decisao+defiro a instauracao'
        if debug:
            print('[TESTE] Documento identificado como decisão de instauração (sem precedência)')
        if resultado_sisbajud == 'negativo':
            regra_aplicada += ' | sisbajud negativo => pec_idpj'
            acoes_executadas = ['pec_idpj']
    
    # Despacho com texto específico
    elif tipo_documento == 'despacho' and any(p in texto_documento.lower() for p in ['em que pese a ausência', 'argos']):
        regra_aplicada = 'despacho+argos'
        if debug:
            print('[TESTE] Documento identificado como despacho com texto específico')
        if resultado_sisbajud == 'positivo':
            regra_aplicada += ' | sisbajud positivo => ato_bloq'
            acoes_executadas = ['ato_bloq']
        elif resultado_sisbajud == 'negativo' and all(v == 'nao' for v in sigilo_anexos.values()):
            regra_aplicada += ' | sisbajud negativo, nenhum anexo sigiloso => ato_meios'
            acoes_executadas = ['ato_meios']
    
    # Decisão com "tendo em vista que"
    elif tipo_documento == 'decisao' and 'tendo em vista que' in texto_documento.lower():
        regra_aplicada = 'decisao+tendo em vista que'
        if debug:
            print('[TESTE] Documento identificado como decisão com texto sobre reclamada')
        if resultado_sisbajud == 'positivo':
            regra_aplicada += ' | sisbajud positivo => ato_bloq'
            acoes_executadas = ['ato_bloq']
    
    else:
        regra_aplicada = f'nao identificado: {tipo_documento}'
        if debug:
            print(f'[TESTE] Tipo de documento não identificado: {tipo_documento}')
    
    return regra_aplicada, acoes_executadas

def executar_testes():
    """
    Executa bateria de testes para validar a lógica de precedência.
    """
    print("🧪 INICIANDO TESTES DE PRECEDÊNCIA - FLUXO ARGOS")
    print("=" * 70)
    
    testes = [
        {
            "nome": "Teste 1: Precedência Ativada - defiro + SISBAJUD positivo + outros termos",
            "resultado_sisbajud": "positivo",
            "sigilo_anexos": {"anexo1": "nao"},
            "tipo_documento": "decisao",
            "texto_documento": "Defiro a instauração do inquérito civil argos tendo em vista que a reclamada apresentou documentos.",
            "esperado_regra": "[PRIORIDADE]",
            "esperado_acoes": ["lembrete_bloq", "pec_idpj"]
        },
        {
            "nome": "Teste 2: Precedência NÃO Ativada - defiro + SISBAJUD negativo + outros termos",
            "resultado_sisbajud": "negativo",
            "sigilo_anexos": {"anexo1": "nao"},
            "tipo_documento": "decisao",
            "texto_documento": "Defiro a instauração do inquérito civil argos tendo em vista que a reclamada apresentou documentos.",
            "esperado_regra": "decisao+defiro a instauracao",
            "esperado_acoes": ["pec_idpj"]
        },
        {
            "nome": "Teste 3: Sem defiro - despacho + argos + SISBAJUD positivo",
            "resultado_sisbajud": "positivo",
            "sigilo_anexos": {"anexo1": "nao"},
            "tipo_documento": "despacho",
            "texto_documento": "Em que pese a ausência de documentos, argos indica necessidade de análise.",
            "esperado_regra": "despacho+argos",
            "esperado_acoes": ["ato_bloq"]
        },
        {
            "nome": "Teste 4: Sem defiro - decisão + tendo em vista que + SISBAJUD positivo",
            "resultado_sisbajud": "positivo",
            "sigilo_anexos": {"anexo1": "nao"},
            "tipo_documento": "decisao",
            "texto_documento": "Tendo em vista que a reclamada não apresentou documentos suficientes.",
            "esperado_regra": "decisao+tendo em vista que",
            "esperado_acoes": ["ato_bloq"]
        },
        {
            "nome": "Teste 5: Precedência CRÍTICA - múltiplos termos com defiro + SISBAJUD positivo",
            "resultado_sisbajud": "positivo",
            "sigilo_anexos": {"anexo1": "sim", "anexo2": "nao"},
            "tipo_documento": "decisao",
            "texto_documento": "Defiro a instauração considerando argos e tendo em vista que a reclamada tem obrigações pendentes.",
            "esperado_regra": "[PRIORIDADE]",
            "esperado_acoes": ["lembrete_bloq", "pec_idpj"]
        }
    ]
    
    resultados = []
    
    for i, teste in enumerate(testes, 1):
        print(f"\n📋 {teste['nome']}")
        print("-" * 60)
        
        regra_obtida, acoes_obtidas = simular_aplicar_regras_argos(
            teste["resultado_sisbajud"],
            teste["sigilo_anexos"],
            teste["tipo_documento"],
            teste["texto_documento"]
        )
        
        # Verificar se a regra esperada está presente
        regra_correta = teste["esperado_regra"] in regra_obtida if regra_obtida else False
        acoes_corretas = set(teste["esperado_acoes"]) == set(acoes_obtidas)
        
        print(f"\n📊 RESULTADO:")
        print(f"  Regra obtida: {regra_obtida}")
        print(f"  Ações obtidas: {acoes_obtidas}")
        print(f"  ✅ Regra correta: {'SIM' if regra_correta else 'NÃO'}")
        print(f"  ✅ Ações corretas: {'SIM' if acoes_corretas else 'NÃO'}")
        
        sucesso = regra_correta and acoes_corretas
        resultado = {
            "teste": i,
            "nome": teste["nome"],
            "sucesso": sucesso,
            "regra_obtida": regra_obtida,
            "acoes_obtidas": acoes_obtidas
        }
        resultados.append(resultado)
        
        if sucesso:
            print("  🎉 PASSOU!")
        else:
            print("  ❌ FALHOU!")
            print(f"     Esperado - Regra: {teste['esperado_regra']}, Ações: {teste['esperado_acoes']}")
    
    # Resumo final
    print("\n" + "=" * 70)
    print("📈 RESUMO DOS TESTES")
    print("=" * 70)
    
    sucessos = sum(1 for r in resultados if r["sucesso"])
    total = len(resultados)
    
    for resultado in resultados:
        status = "✅ PASSOU" if resultado["sucesso"] else "❌ FALHOU"
        print(f"  Teste {resultado['teste']}: {status}")
    
    print(f"\n🏆 RESULTADO FINAL: {sucessos}/{total} testes passaram")
    
    if sucessos == total:
        print("🎉 TODOS OS TESTES PASSARAM! Lógica de precedência implementada corretamente.")
    else:
        print("⚠️  ALGUNS TESTES FALHARAM! Verificar implementação da lógica de precedência.")
    
    return sucessos == total

if __name__ == "__main__":
    sucesso = executar_testes()
    exit(0 if sucesso else 1)
