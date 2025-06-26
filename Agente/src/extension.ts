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
    restrictiveMode: boolean;
    inquisitiveMode: boolean;
    maxContextLines: number;
    interceptCopilotChat: boolean;
    chatFilterStrength: 'strict' | 'moderate' | 'permissive';
    autoFixErrors: boolean;
    watchTerminal: boolean;
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
            restrictiveMode: config.get('restrictiveMode', true),
            inquisitiveMode: config.get('inquisitiveMode', true),
            maxContextLines: config.get('maxContextLines', 50),
            interceptCopilotChat: config.get('interceptCopilotChat', true),
            chatFilterStrength: config.get('chatFilterStrength', 'strict') as 'strict' | 'moderate' | 'permissive',
            autoFixErrors: config.get('autoFixErrors', true),
            watchTerminal: config.get('watchTerminal', true)
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
            const maxLines = this.config.maxContextLines;
            const startLine = Math.max(0, selection.start.line - maxLines);
            const endLine = Math.min(document.lineCount - 1, selection.end.line + maxLines);
            const range = new vscode.Range(startLine, 0, endLine, document.lineAt(endLine).text.length);
            return document.getText(range);
        }
        
        // No selection - get context around cursor
        const line = selection.active.line;
        const startLine = Math.max(0, line - this.config.maxContextLines / 2);
        const endLine = Math.min(document.lineCount - 1, line + this.config.maxContextLines / 2);
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
            response += `   • Código selecionado + ${this.config.maxContextLines} linhas\n\n`;
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
        }
        
        // Footer
        response += `---\n`;
        response += `🔒 **RESTRIÇÕES ATIVAS** | Modo: ${this.config.restrictiveMode ? 'Restritivo' : 'Permissivo'}\n`;
        response += `📏 Contexto limitado a ${this.config.maxContextLines} linhas | ❓ Modo inquisitivo: ${this.config.inquisitiveMode ? 'ON' : 'OFF'}\n`;
        
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
