import * as vscode from 'vscode';
import { TerminalErrorDetector, ErrorInfo } from './terminalErrorDetector';

interface ChatRequest {
    prompt: string;
    context?: string;
}

interface ChatResponse {
    content: string;
    filtered: boolean;
    restrictions: string[];
}

interface RestrictedCopilotConfig {
    enabled: boolean;
    // Valores fixos - não configuráveis
    readonly restrictiveMode: true;
    readonly inquisitiveMode: true;
    readonly maxContextLines: 300;
    readonly chatFilterStrength: 'strict';
    readonly autoFixErrors: true;
    readonly watchTerminal: true;
}

class RestrictedChatParticipant {
    public readonly id = 'restrictedCopilot.participant';
    private config: RestrictedCopilotConfig;

    constructor() {
        this.config = this.loadConfig();
    }

    private loadConfig(): RestrictedCopilotConfig {
        const config = vscode.workspace.getConfiguration('restrictedCopilot');
        return {
            enabled: config.get('enabled', true),
            // Valores fixos - sempre ativos
            restrictiveMode: true,
            inquisitiveMode: true,
            maxContextLines: 300,
            chatFilterStrength: 'strict',
            autoFixErrors: true,
            watchTerminal: true
        };
    }

    public updateConfig(): void {
        this.config = this.loadConfig();
    }

    public readonly requestHandler: vscode.ChatRequestHandler = async (
        request: vscode.ChatRequest,
        context: vscode.ChatContext,
        stream: vscode.ChatResponseStream,
        token: vscode.CancellationToken
    ): Promise<vscode.ChatResult> => {
        
        const activeEditor = vscode.window.activeTextEditor;
        
        if (!activeEditor) {
            stream.markdown("❌ **RESTRICTED COPILOT**: Nenhum editor ativo. Abra um arquivo no workspace PjePlus para análise.");
            return { metadata: { command: 'restricted-analysis' } };
        }

        // Get current context
        const currentContext = this.getCurrentContext(activeEditor);
        const fileName = activeEditor.document.fileName;
        const language = activeEditor.document.languageId;
        
        // Process request through restrictive filter
        const chatResponse = await this.processChatRequest({
            prompt: request.prompt,
            context: currentContext
        }, activeEditor);

        // Stream the response
        stream.markdown(chatResponse.content);

        return { 
            metadata: { 
                command: 'restricted-analysis',
                filtered: chatResponse.filtered,
                restrictions: chatResponse.restrictions,
                contextLines: currentContext.split('\n').length,
                fileName: fileName.split('\\').pop(),
                language
            } 
        };
    };

    private getCurrentContext(editor: vscode.TextEditor): string {
        const selection = editor.selection;
        const document = editor.document;
        
        if (!selection.isEmpty) {
            // User has selected text - analyze only selection + limited context
            const maxLines = 300; // Valor fixo
            const startLine = Math.max(0, selection.start.line - maxLines);
            const endLine = Math.min(document.lineCount - 1, selection.end.line + maxLines);
            const range = new vscode.Range(startLine, 0, endLine, document.lineAt(endLine).text.length);
            return document.getText(range);
        }
        
        // No selection - get context around cursor
        const line = selection.active.line;
        const startLine = Math.max(0, line - 150); // Fixo: 150 linhas antes
        const endLine = Math.min(document.lineCount - 1, line + 150); // Fixo: 150 linhas depois
        const range = new vscode.Range(startLine, 0, endLine, document.lineAt(endLine).text.length);
        
        return document.getText(range);
    }

    private async processChatRequest(request: ChatRequest, editor: vscode.TextEditor): Promise<ChatResponse> {
        const context = request.context || '';
        const fileName = editor.document.fileName;
        const language = editor.document.languageId;
        
        // Build restricted response
        let response = `🔒 **RESTRICTED COPILOT MEDIANDO CHAT**\n\n`;
        
        // Context information
        const contextLines = context.split('\n').length;
        response += `📍 **Workspace PjePlus** | ${contextLines} linhas | \`${fileName.split('\\').pop()}\` (${language})\n\n`;
        
        // Check if request violates PjePlus-specific restrictions
        const pjePlusRestrictedPatterns = [
            // 1. Não criar novos arquivos para teste
            /criar.*arquivo.*test|test.*arquivo|novo.*test|arquivo.*teste/i,
            /criar.*spec|novo.*spec|arquivo.*spec/i,
            /test\.py|test\.js|spec\.js|spec\.py/i,
            
            // 2. Não criar relatórios
            /criar.*relat[óo]rio|novo.*relat[óo]rio|gerar.*relat[óo]rio/i,
            /report\.py|report\.js|relatorio\.py|relatorio\.js/i,
            /criar.*documenta[çc][ãa]o|gerar.*documenta[çc][ãa]o/i,
            
            // 3. Não sugerir criação de arquivos em geral
            /criar.*arquivo|novo.*arquivo|arquivo.*novo/i,
            /touch |mkdir |new file|criar pasta/i
        ];
        
        const violatesPjePlusRules = pjePlusRestrictedPatterns.some(pattern => pattern.test(request.prompt));
        
        if (violatesPjePlusRules) {
            response += `🚫 **VIOLAÇÃO DE DIRETRIZES PJEPLUS**\n\n`;
            response += `❌ **NÃO PERMITIDO NO PJEPLUS**:\n`;
            response += `   • ❌ Criar novos arquivos de teste\n`;
            response += `   • ❌ Criar relatórios ou documentação\n`;
            response += `   • ❌ Sugerir criação de arquivos\n\n`;
            response += `✅ **ALTERNATIVAS PERMITIDAS**:\n`;
            response += `   • ✅ Analisar código existente\n`;
            response += `   • ✅ Corrigir problemas no código atual\n`;
            response += `   • ✅ Usar autocompile (PowerShell): \`py arquivo.py\`\n`;
            response += `   • ✅ Otimizar funções específicas\n\n`;
            
            return {
                content: response,
                filtered: true,
                restrictions: ["PjePlus guidelines violation - file creation blocked"]
            };
        }
        
        // Check if request is asking for broad changes
        const broadRequestPatterns = [
            /refactor|reescrever|reestruturar|otimizar tudo/i,
            /melhorar todo|revisar todo|corrigir todo/i,
            /analisar arquivo|arquivo inteiro/i,
            /todo o código|código completo/i
        ];
        
        const isBroadRequest = broadRequestPatterns.some(pattern => pattern.test(request.prompt));
        
        if (isBroadRequest && this.config.restrictiveMode) {
            response += `❌ **ANÁLISE AMPLA BLOQUEADA**\n\n`;
            response += `🎯 **ESCOPO PERMITIDO**:\n`;
            response += `   • Função onde está o cursor\n`;
            response += `   • Código selecionado + 300 linhas (fixo)\n\n`;
            response += `💡 **REFORMULE SUA PERGUNTA**:\n`;
            response += `   ✅ "Há bugs nesta função?"\n`;
            response += `   ✅ "Como otimizar este loop?"\n`;
            response += `   ✅ "Esta variável está correta?"\n`;
            response += `   ❌ "Melhore todo o arquivo"\n\n`;
            
            return {
                content: response,
                filtered: true,
                restrictions: ["Broad analysis request blocked"]
            };
        }
        
        // Analyze specific request
        response += `💬 **SUA PERGUNTA**: "${request.prompt}"\n\n`;
        
        // Analyze current context for issues
        response += this.analyzeContextForIssues(context, language);
        
        // Inquisitive mode
        if (this.config.inquisitiveMode) {
            response += `❓ **MODO INQUISITIVO**: Preciso esclarecer:\n\n`;
            
            if (request.prompt.toLowerCase().includes('corrigir') || request.prompt.toLowerCase().includes('fix')) {
                response += `🔧 **Sobre correções** - Você quer:\n`;
                response += `   A) Identificar problemas?\n`;
                response += `   B) Sugerir correções?\n`;
                response += `   C) Aplicar correções?\n\n`;
            }
            
            if (request.prompt.toLowerCase().includes('melhorar') || request.prompt.toLowerCase().includes('otimizar')) {
                response += `⚡ **Sobre melhorias** - Qual aspecto?\n`;
                response += `   🚀 Performance\n`;
                response += `   📖 Legibilidade\n`;
                response += `   🛡️ Segurança\n`;
                response += `   🏗️ Estrutura\n\n`;
            }
            if (request.prompt.toLowerCase().includes('test') || request.prompt.toLowerCase().includes('teste')) {
                response += `🧪 **Sobre testes** - Use APENAS:\n`;
                response += `   ✅ PowerShell: \`py arquivo.py\`\n`;
                response += `   ✅ Autocompile já implementado\n`;
                response += `   ❌ NÃO criar novos arquivos de teste\n`;
                response += `   ❌ NÃO usar && (use comandos separados)\n\n`;
            }
        }
        
        // PjePlus Testing Guidelines
        response += `🧪 **DIRETRIZES DE TESTE PJEPLUS**:\n`;
        response += `   ✅ Use: \`py script.py\` (PowerShell)\n`;
        response += `   ✅ Autocompile implementado\n`;
        response += `   ❌ Não criar arquivos de teste\n`;
        response += `   ❌ Não usar && (comandos separados)\n\n`;
        
        // Footer
        response += `---\n`;
        response += `🔒 **RESTRIÇÕES ATIVAS** | Modo: ${this.config.restrictiveMode ? 'Restritivo' : 'Permissivo'}\n`;
        response += `📏 Contexto limitado a 300 linhas | ❓ Modo inquisitivo: SEMPRE ATIVO\n`;
        response += `🚫 **PJEPLUS**: Sem novos arquivos | Sem relatórios | PowerShell apenas\n`;
        
        return {
            content: response,
            filtered: false,
            restrictions: []
        };
    }

    private analyzeContextForIssues(context: string, language: string): string {
        let analysis = `🔍 **ANÁLISE AUTOMÁTICA**:\n\n`;
        
        const issues: string[] = [];
        const warnings: string[] = [];
        
        // Check for PjePlus-specific violations in code context
        if (context.includes('&&')) {
            issues.push("🚫 Operador && detectado - Use comandos PowerShell separados");
        }
        
        if (context.match(/test_|_test\.py|teste_|_teste\.py/)) {
            issues.push("🚫 Arquivo de teste detectado - Não permitido no PjePlus");
        }
        
        if (context.match(/report|relatorio|documentation/i)) {
            warnings.push("⚠️ Código relacionado a relatórios - Verificar se é necessário");
        }
        
        // Check for debug statements
        if (context.includes('console.log') || context.includes('print(')) {
            warnings.push("🐛 Debug statements detectados");
        }
        
        // Check for TODO/FIXME
        if (context.includes('TODO') || context.includes('FIXME')) {
            warnings.push("📝 TODOs/FIXMEs encontrados");
        }
        
        // Python-specific checks
        if (language === 'python') {
            if (context.includes('import *')) {
                warnings.push("🚫 Import * detectado");
            }
            if (context.match(/=\s*[^=]/g) && context.includes('if') && !context.includes('==')) {
                issues.push("🔴 Possível erro: = em vez de == em condição");
            }
        }
        
        // Present findings
        if (issues.length > 0) {
            analysis += `🔴 **PROBLEMAS CRÍTICOS**:\n`;
            issues.forEach(issue => analysis += `   ${issue}\n`);
            analysis += `\n`;
        }
        
        if (warnings.length > 0) {
            analysis += `🟡 **AVISOS**:\n`;
            warnings.forEach(warning => analysis += `   ${warning}\n`);
            analysis += `\n`;
        }
        
        if (issues.length === 0 && warnings.length === 0) {
            analysis += `✅ **Contexto aparentemente correto**\n\n`;
        }
        
        return analysis;
    }
}

// Extension activation
export function activate(context: vscode.ExtensionContext) {
    console.log('🔒 Restricted Copilot with CHAT INTEGRATION activated!');
    
    const chatParticipant = new RestrictedChatParticipant();
    const terminalDetector = new TerminalErrorDetector();
    terminalDetector.startWatching();
    
    // Register chat participant
    const chatRegistration = vscode.chat.createChatParticipant(
        'restrictedCopilot.participant',
        chatParticipant.requestHandler
    );
    
    chatRegistration.followupProvider = {
        provideFollowups: async (result, context, token) => {
            return [
                {
                    prompt: 'Analise mais detalhes desta função',
                    label: '🔍 Análise Detalhada'
                },
                {
                    prompt: 'Há problemas de segurança?',
                    label: '🛡️ Verificar Segurança'
                },
                {
                    prompt: 'Como otimizar performance?',
                    label: '🚀 Performance'
                }
            ];
        }
    };
    
    // Commands redirect to chat
    const analyzeFunction = vscode.commands.registerCommand('restricted-copilot.analyzeFunction', async () => {
        vscode.window.showInformationMessage(
            '💬 Use @restricted no chat do GitHub Copilot!',
            'Open Chat'
        ).then(selection => {
            if (selection === 'Open Chat') {
                vscode.commands.executeCommand('workbench.panel.chat.view.copilot.focus');
            }
        });
    });
    
    const analyzeSelection = vscode.commands.registerCommand('restricted-copilot.analyzeSelection', async () => {
        vscode.window.showInformationMessage(
            '💬 Selecione código e use @restricted no chat!',
            'Open Chat'
        ).then(selection => {
            if (selection === 'Open Chat') {
                vscode.commands.executeCommand('workbench.panel.chat.view.copilot.focus');
            }
        });
    });

    const compileCurrentFile = vscode.commands.registerCommand('restricted-copilot.compileCurrentFile', async () => {
        await terminalDetector.compileCurrentFile();
    });
    
    const toggleRestrictiveMode = vscode.commands.registerCommand('restricted-copilot.toggleRestrictiveMode', async () => {
        const config = vscode.workspace.getConfiguration('restrictedCopilot');
        const current = config.get('restrictiveMode', true);
        await config.update('restrictiveMode', !current, vscode.ConfigurationTarget.Global);
        chatParticipant.updateConfig();
        
        vscode.window.showInformationMessage(
            `🔒 Modo Restritivo ${!current ? 'ATIVADO' : 'DESATIVADO'}`
        );
    });
    
    const configListener = vscode.workspace.onDidChangeConfiguration(e => {
        if (e.affectsConfiguration('restrictedCopilot')) {
            chatParticipant.updateConfig();
        }
    });
    
    context.subscriptions.push(
        chatRegistration,
        analyzeFunction,
        analyzeSelection,
        compileCurrentFile,
        toggleRestrictiveMode,
        configListener
    );
    
    // Welcome message
    vscode.window.showInformationMessage(
        '🎉 RESTRICTED COPILOT CHAT ATIVO! Digite @restricted no chat para usar.',
        'Testar Chat',
        'Configurações'
    ).then(selection => {
        if (selection === 'Testar Chat') {
            vscode.commands.executeCommand('workbench.panel.chat.view.copilot.focus');
        } else if (selection === 'Configurações') {
            vscode.commands.executeCommand('workbench.action.openSettings', 'restrictedCopilot');
        }
    });
}

export function deactivate() {
    console.log('🔒 Restricted Copilot deactivated');
}
