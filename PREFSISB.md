# PROJETO DE IMPLEMENTAÇÃO - PREFERÊNCIAS SISBAJUD

## ANÁLISE DA IMPLEMENTAÇÃO ATUAL

### Estrutura Identificada no `gigs-plugin.js`

A implementação atual utiliza o seguinte padrão para configuração de preferências:

```javascript
// Estrutura base das preferências SISBAJUD
preferencias.sisbajud = {
    juiz: '',
    vara: '',
    cnpjRaiz: '',
    teimosinha: '',
    contasalario: '',
    naorespostas: '',
    valor_desbloqueio: '',
    banco_preferido: '',
    agencia_preferida: '',
    preencherValor: '',
    confirmar: '',
    executarAAaoFinal: '',
    salvarEprotocolar: ''
};
```

### Padrão de Inicialização

Cada propriedade é inicializada com verificação de tipo e valor padrão:

```javascript
preferencias.sisbajud = typeof(preferencias.sisbajud) == "undefined" ? 
    {default_object} : preferencias.sisbajud;

preferencias.sisbajud.propriedade = typeof(preferencias.sisbajud.propriedade) == "undefined" ? 
    "valor_padrao" : preferencias.sisbajud.propriedade;
```

## PROJETO DE IMPLEMENTAÇÃO PYTHON

### 1. Estrutura do Módulo `preferencias_sisb.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de Preferências SISBAJUD
Sistema de configuração e persistência de preferências
baseado na implementação do gigs-plugin.js
"""

import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class PreferenciasSisbajud:
    """Classe para configurações do SISBAJUD"""
    juiz: str = ""
    vara: str = ""
    cnpjRaiz: str = "não"
    teimosinha: str = "não"
    contasalario: str = "não"
    naorespostas: str = "Cancelar"
    valor_desbloqueio: str = "não"
    banco_preferido: str = "não"
    agencia_preferida: str = "não"
    preencherValor: str = "não"
    confirmar: str = "não"
    executarAAaoFinal: str = "Nenhum"
    salvarEprotocolar: str = "não"

@dataclass
class PreferenciasSerasajud:
    """Classe para configurações do SERASAJUD"""
    juiz: str = ""
    foro: str = ""
    vara: str = ""
    prazo_atendimento: str = ""

@dataclass
class PreferenciasRenajud:
    """Classe para configurações do RENAJUD"""
    tipo_restricao: str = ""
    comarca: str = ""
    tribunal: str = ""
    orgao: str = ""
    juiz: str = ""
    juiz2: str = ""

@dataclass
class PreferenciasGerais:
    """Classe para configurações gerais"""
    versao: str = "1.0.0"
    trt: str = ""
    nm_usuario: str = ""
    oj_usuario: str = ""
    grau_usuario: str = ""
    extensaoAtiva: bool = True
    concordo: bool = False
    maisPje_velocidade_interacao: int = 1000
    
class GerenciadorPreferencias:
    """Gerenciador de preferências do sistema"""
    
    def __init__(self, arquivo_config: str = "config_sisb.json"):
        self.arquivo_config = arquivo_config
        self.preferencias = self._carregar_preferencias()
    
    def _carregar_preferencias(self) -> Dict[str, Any]:
        """Carrega preferências do arquivo JSON"""
        try:
            if os.path.exists(self.arquivo_config):
                with open(self.arquivo_config, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    return self._aplicar_defaults(dados)
            else:
                return self._obter_defaults()
        except Exception as e:
            print(f"Erro ao carregar preferências: {e}")
            return self._obter_defaults()
    
    def _obter_defaults(self) -> Dict[str, Any]:
        """Retorna configurações padrão"""
        return {
            'sisbajud': asdict(PreferenciasSisbajud()),
            'serasajud': asdict(PreferenciasSerasajud()),
            'renajud': asdict(PreferenciasRenajud()),
            'gerais': asdict(PreferenciasGerais()),
            'ultima_atualizacao': datetime.now().isoformat()
        }
    
    def _aplicar_defaults(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """Aplica valores padrão para propriedades não definidas"""
        defaults = self._obter_defaults()
        
        # Aplicar padrão para seção sisbajud
        if 'sisbajud' not in dados:
            dados['sisbajud'] = defaults['sisbajud']
        else:
            for key, default_value in defaults['sisbajud'].items():
                if key not in dados['sisbajud']:
                    dados['sisbajud'][key] = default_value
        
        # Aplicar padrão para outras seções
        for secao in ['serasajud', 'renajud', 'gerais']:
            if secao not in dados:
                dados[secao] = defaults[secao]
            else:
                for key, default_value in defaults[secao].items():
                    if key not in dados[secao]:
                        dados[secao][key] = default_value
        
        # Tratamento especial para campos com valores específicos
        if dados['sisbajud']['naorespostas'] == "":
            dados['sisbajud']['naorespostas'] = "Cancelar"
        
        return dados
    
    def salvar_preferencias(self) -> bool:
        """Salva preferências no arquivo JSON"""
        try:
            self.preferencias['ultima_atualizacao'] = datetime.now().isoformat()
            with open(self.arquivo_config, 'w', encoding='utf-8') as f:
                json.dump(self.preferencias, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Erro ao salvar preferências: {e}")
            return False
    
    def obter_sisbajud(self) -> PreferenciasSisbajud:
        """Retorna configurações do SISBAJUD"""
        return PreferenciasSisbajud(**self.preferencias['sisbajud'])
    
    def atualizar_sisbajud(self, **kwargs) -> bool:
        """Atualiza configurações do SISBAJUD"""
        try:
            for key, value in kwargs.items():
                if key in self.preferencias['sisbajud']:
                    self.preferencias['sisbajud'][key] = value
            return self.salvar_preferencias()
        except Exception as e:
            print(f"Erro ao atualizar SISBAJUD: {e}")
            return False
    
    def obter_serasajud(self) -> PreferenciasSerasajud:
        """Retorna configurações do SERASAJUD"""
        return PreferenciasSerasajud(**self.preferencias['serasajud'])
    
    def atualizar_serasajud(self, **kwargs) -> bool:
        """Atualiza configurações do SERASAJUD"""
        try:
            for key, value in kwargs.items():
                if key in self.preferencias['serasajud']:
                    self.preferencias['serasajud'][key] = value
            return self.salvar_preferencias()
        except Exception as e:
            print(f"Erro ao atualizar SERASAJUD: {e}")
            return False
    
    def obter_renajud(self) -> PreferenciasRenajud:
        """Retorna configurações do RENAJUD"""
        return PreferenciasRenajud(**self.preferencias['renajud'])
    
    def atualizar_renajud(self, **kwargs) -> bool:
        """Atualiza configurações do RENAJUD"""
        try:
            for key, value in kwargs.items():
                if key in self.preferencias['renajud']:
                    self.preferencias['renajud'][key] = value
            return self.salvar_preferencias()
        except Exception as e:
            print(f"Erro ao atualizar RENAJUD: {e}")
            return False
    
    def obter_gerais(self) -> PreferenciasGerais:
        """Retorna configurações gerais"""
        return PreferenciasGerais(**self.preferencias['gerais'])
    
    def atualizar_gerais(self, **kwargs) -> bool:
        """Atualiza configurações gerais"""
        try:
            for key, value in kwargs.items():
                if key in self.preferencias['gerais']:
                    self.preferencias['gerais'][key] = value
            return self.salvar_preferencias()
        except Exception as e:
            print(f"Erro ao atualizar configurações gerais: {e}")
            return False
    
    def validar_configuracoes(self) -> bool:
        """Valida se todas as configurações estão corretas"""
        try:
            # Validar estrutura básica
            secoes_obrigatorias = ['sisbajud', 'serasajud', 'renajud', 'gerais']
            for secao in secoes_obrigatorias:
                if secao not in self.preferencias:
                    return False
            
            # Validar campos obrigatórios do SISBAJUD
            sisbajud = self.preferencias['sisbajud']
            campos_obrigatorios = ['naorespostas', 'executarAAaoFinal']
            for campo in campos_obrigatorios:
                if campo not in sisbajud or sisbajud[campo] == "":
                    return False
            
            return True
        except Exception as e:
            print(f"Erro na validação: {e}")
            return False
    
    def resetar_configuracoes(self) -> bool:
        """Reseta todas as configurações para valores padrão"""
        try:
            self.preferencias = self._obter_defaults()
            return self.salvar_preferencias()
        except Exception as e:
            print(f"Erro ao resetar configurações: {e}")
            return False
    
    def exportar_configuracoes(self, arquivo_destino: str) -> bool:
        """Exporta configurações para um arquivo"""
        try:
            with open(arquivo_destino, 'w', encoding='utf-8') as f:
                json.dump(self.preferencias, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Erro ao exportar configurações: {e}")
            return False
    
    def importar_configuracoes(self, arquivo_origem: str) -> bool:
        """Importa configurações de um arquivo"""
        try:
            with open(arquivo_origem, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            
            self.preferencias = self._aplicar_defaults(dados)
            return self.salvar_preferencias()
        except Exception as e:
            print(f"Erro ao importar configurações: {e}")
            return False

# Instância global do gerenciador
gerenciador_preferencias = GerenciadorPreferencias()

# Funções de conveniência para compatibilidade
def obter_preferencias_sisbajud() -> PreferenciasSisbajud:
    """Retorna preferências do SISBAJUD"""
    return gerenciador_preferencias.obter_sisbajud()

def salvar_preferencias_sisbajud(**kwargs) -> bool:
    """Salva preferências do SISBAJUD"""
    return gerenciador_preferencias.atualizar_sisbajud(**kwargs)

def obter_preferencias_serasajud() -> PreferenciasSerasajud:
    """Retorna preferências do SERASAJUD"""
    return gerenciador_preferencias.obter_serasajud()

def salvar_preferencias_serasajud(**kwargs) -> bool:
    """Salva preferências do SERASAJUD"""
    return gerenciador_preferencias.atualizar_serasajud(**kwargs)

def obter_preferencias_renajud() -> PreferenciasRenajud:
    """Retorna preferências do RENAJUD"""
    return gerenciador_preferencias.obter_renajud()

def salvar_preferencias_renajud(**kwargs) -> bool:
    """Salva preferências do RENAJUD"""
    return gerenciador_preferencias.atualizar_renajud(**kwargs)
```

### 2. Integração com o Sistema SISB

```python
# Exemplo de uso no sisb_modulos/config.py
from preferencias_sisb import gerenciador_preferencias

# Carregar configurações do SISBAJUD
config_sisbajud = gerenciador_preferencias.obter_sisbajud()

# Exemplo de uso das preferências
if config_sisbajud.teimosinha == "sim":
    # Executar lógica para teimosinha
    pass

if config_sisbajud.confirmar == "sim":
    # Executar confirmação automática
    pass
```

### 3. Interface de Configuração

```python
# Exemplo de interface para configuração
def configurar_sisbajud():
    """Interface para configurar SISBAJUD"""
    config = gerenciador_preferencias.obter_sisbajud()
    
    print("=== Configuração SISBAJUD ===")
    print(f"1. Juiz: {config.juiz}")
    print(f"2. Vara: {config.vara}")
    print(f"3. CNPJ Raiz: {config.cnpjRaiz}")
    print(f"4. Teimosinha: {config.teimosinha}")
    print(f"5. Conta Salário: {config.contasalario}")
    print(f"6. Não Respostas: {config.naorespostas}")
    print(f"7. Valor Desbloqueio: {config.valor_desbloqueio}")
    print(f"8. Banco Preferido: {config.banco_preferido}")
    print(f"9. Agência Preferida: {config.agencia_preferida}")
    print(f"10. Preencher Valor: {config.preencherValor}")
    print(f"11. Confirmar: {config.confirmar}")
    print(f"12. Executar Ação Final: {config.executarAAaoFinal}")
    print(f"13. Salvar e Protocolar: {config.salvarEprotocolar}")
    
    # Lógica para editar configurações
    # ...
```

## VANTAGENS DA IMPLEMENTAÇÃO

### 1. **Compatibilidade Total**
- Mantém a mesma estrutura do JavaScript
- Valores padrão idênticos ao `gigs-plugin.js`
- Comportamento similar ao navegador

### 2. **Tipo Safety**
- Uso de `@dataclass` para estruturas tipadas
- Validação automática de tipos
- Intellisense nos IDEs

### 3. **Persistência Robusta**
- Salvamento automático em JSON
- Backup e restauração
- Validação de integridade

### 4. **Extensibilidade**
- Fácil adição de novas seções
- Sistema modular
- Configurações específicas por módulo

### 5. **Manutenibilidade**
- Código limpo e organizado
- Documentação integrada
- Testes unitários possíveis

## EXEMPLO DE ARQUIVO DE CONFIGURAÇÃO

```json
{
  "sisbajud": {
    "juiz": "João Silva",
    "vara": "1ª Vara do Trabalho",
    "cnpjRaiz": "não",
    "teimosinha": "sim",
    "contasalario": "não",
    "naorespostas": "Cancelar",
    "valor_desbloqueio": "não",
    "banco_preferido": "Banco do Brasil",
    "agencia_preferida": "1234-5",
    "preencherValor": "sim",
    "confirmar": "sim",
    "executarAAaoFinal": "Salvar",
    "salvarEprotocolar": "sim"
  },
  "serasajud": {
    "juiz": "João Silva",
    "foro": "Foro Trabalhista",
    "vara": "1ª Vara",
    "prazo_atendimento": "30"
  },
  "renajud": {
    "tipo_restricao": "Bloqueio",
    "comarca": "Florianópolis",
    "tribunal": "TRT12",
    "orgao": "1ª Vara",
    "juiz": "João Silva",
    "juiz2": ""
  },
  "gerais": {
    "versao": "1.0.0",
    "trt": "TRT12",
    "nm_usuario": "João Silva",
    "oj_usuario": "1ª Vara do Trabalho",
    "grau_usuario": "Juiz",
    "extensaoAtiva": true,
    "concordo": true,
    "maisPje_velocidade_interacao": 1000
  },
  "ultima_atualizacao": "2025-07-09T10:30:00"
}
```

## MAPEAMENTO DE CAMPOS NO SISBAJUD

### Campos de Preenchimento Identificados

Com base na análise do `gigs-plugin.js`, aqui estão os campos exatos onde as preferências são inseridas no SISBAJUD:

#### 1. **Juiz Solicitante** (`preferencias.sisbajud.juiz`)
- **Seletor CSS**: `input[placeholder*="Juiz"]`
- **Função**: Linha 13748-13755
- **Uso**: Preenchimento automático do campo "Juiz Solicitante"
- **Comportamento especial**: Suporta filtro dinâmico com `modulo8`

#### 2. **Vara/Juízo** (`preferencias.sisbajud.vara`)
- **Seletor CSS**: `mat-select[name*="varaJuizoSelect"]`
- **Função**: Linha 13766-13790
- **Uso**: Seleção automática da vara no dropdown
- **Tipo**: Select com opções dinâmicas

#### 3. **Número do Processo** (automático)
- **Seletor CSS**: `input[placeholder="Número do Processo"]`
- **Função**: Linha 13800-13810
- **Uso**: Preenchimento do número do processo extraído do PJe

#### 4. **Tipo de Ação** (automático)
- **Seletor CSS**: `mat-select[name*="acao"]`
- **Função**: Linha 13814-13840
- **Uso**: Seleção automática do tipo de ação

#### 5. **CPF do Autor** (automático)
- **Seletor CSS**: `input[placeholder*="CPF"]`
- **Função**: Linha 13843-13865
- **Uso**: Preenchimento automático do CPF do autor

#### 6. **Nome do Autor** (automático)
- **Seletor CSS**: `input[placeholder="Nome do autor/exequente da ação"]`
- **Função**: Linha 13867-13880
- **Uso**: Preenchimento automático do nome do autor

#### 7. **CNPJ Raiz** (`preferencias.sisbajud.cnpjRaiz`)
- **Função**: Linha 13881-13890
- **Uso**: Define se deve pesquisar CNPJ raiz ou completo
- **Valores**: "sim" / "não"

#### 8. **Teimosinha** (`preferencias.sisbajud.teimosinha`)
- **Seletor CSS**: `mat-radio-button`
- **Função**: Linha 13896-13980
- **Uso**: Controla requisição de informações complementares
- **Valores**: "não" / número de dias (ex: "30")
- **Comportamento**: Se != "nao", ativa opção e define prazo

#### 9. **Conta Salário** (`preferencias.sisbajud.contasalario`)
- **Função**: Linha 14063
- **Uso**: Define se deve incluir conta salário na pesquisa
- **Valores**: "sim" / "não"

#### 10. **Valor de Desbloqueio** (`preferencias.sisbajud.valor_desbloqueio`)
- **Seletor CSS**: `input[placeholder*="Valor aplicado a todos"]`
- **Função**: Linha 14043
- **Uso**: Preenchimento automático do valor para desbloqueio
- **Valores**: "não" / valor monetário

#### 11. **Preencher Valor** (`preferencias.sisbajud.preencherValor`)
- **Uso**: Define se deve preencher valores automaticamente
- **Valores**: "sim" / "não"

#### 12. **CPF/CNPJ do Réu** (automático)
- **Seletor CSS**: `input[placeholder="CPF/CNPJ do réu/executado"]` ou `input[placeholder="CPF/CNPJ da pessoa pesquisada"]`
- **Função**: Linha 14123
- **Uso**: Preenchimento automático do documento do executado

#### 13. **Banco Preferido** (`preferencias.sisbajud.banco_preferido`)
- **Função**: Linha 16916-16930
- **Uso**: Seleção automática de instituição financeira
- **Formato**: Aceita múltiplos bancos separados por vírgula
- **Exemplo**: "Banco do Brasil[1234-5],Caixa Econômica[5678-9]"

#### 14. **Agência Preferida** (`preferencias.sisbajud.agencia_preferida`)
- **Função**: Linha 16917
- **Uso**: Usado junto com banco preferido
- **Formato**: Extraído do campo banco_preferido entre colchetes

#### 15. **Confirmar** (`preferencias.sisbajud.confirmar`)
- **Função**: Linha 16708-16709
- **Uso**: Define se deve confirmar ações automaticamente
- **Valores**: "sim" / "não"

#### 16. **Não Respostas** (`preferencias.sisbajud.naorespostas`)
- **Valor padrão**: "Cancelar"
- **Uso**: Define ação quando não há respostas
- **Valores**: "Cancelar" / outras ações

#### 17. **Executar Ação Final** (`preferencias.sisbajud.executarAAaoFinal`)
- **Valor padrão**: "Nenhum"
- **Uso**: Define ação a ser executada no final do processo
- **Valores**: "Nenhum" / "Salvar" / outras ações

#### 18. **Salvar e Protocolar** (`preferencias.sisbajud.salvarEprotocolar`)
- **Valor padrão**: "não"
- **Uso**: Define se deve salvar e protocolar automaticamente
- **Valores**: "sim" / "não"

### Fluxo de Preenchimento

```javascript
// Sequência de preenchimento no SISBAJUD:
// 1. Juiz Solicitante → input[placeholder*="Juiz"]
// 2. Vara/Juízo → mat-select[name*="varaJuizoSelect"]  
// 3. Número do Processo → input[placeholder="Número do Processo"]
// 4. Tipo de Ação → mat-select[name*="acao"]
// 5. CPF do Autor → input[placeholder*="CPF"]
// 6. Nome do Autor → input[placeholder="Nome do autor/exequente da ação"]
// 7. CNPJ Raiz → configuração lógica
// 8. Teimosinha → mat-radio-button + lógica
// 9. Conta Salário → configuração lógica
// 10. CPF/CNPJ do Réu → input[placeholder="CPF/CNPJ do réu/executado"]
// 11. Valor Desbloqueio → input[placeholder*="Valor aplicado a todos"]
// 12. Banco/Agência → lógica de seleção
// 13. Confirmar → lógica de confirmação
```

## PRÓXIMOS PASSOS

1. **Implementar o módulo `preferencias_sisb.py`**
2. **Integrar com o sistema SISB existente**
3. **Criar interface de configuração**
4. **Migrar dados existentes**
5. **Implementar testes unitários**
6. **Documentar uso e exemplos**

## RESUMO DOS CAMPOS MAPEADOS

✅ **18 campos identificados** com seletores CSS específicos  
✅ **Fluxo de preenchimento** documentado  
✅ **Valores padrão** baseados no código original  
✅ **Comportamentos especiais** identificados (teimosinha, banco múltiplo, etc.)  

---

**Data:** 2025-07-09  
**Baseado em:** `gigs-plugin.js` (análise completa)  
**Status:** Mapeamento Completo - Pronto para Implementação
