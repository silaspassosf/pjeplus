import * as vscode from 'vscode';

interface ChatRequest {
    prompt: string;
    context?: string;
    location?: vscode.Location;
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
}

export class RestrictedChatParticipant {
    public readonly id = 'restrictedCopilot.participant';
    private config: RestrictedCopilotConfig;
    private _onDidReceiveFeedback = new vscode.EventEmitter<vscode.ChatResultFeedback>();

    public readonly onDidReceiveFeedback = this._onDidReceiveFeedback.event;

    constructor() {
        this.config = this.loadConfig();
    }

    public dispose(): void {
        this._onDidReceiveFeedback.dispose();
    }

    public readonly requestHandler: vscode.ChatRequestHandler = async (
        request: vscode.ChatRequest,
        context: vscode.ChatContext,
        stream: vscode.ChatResponseStream,
        token: vscode.CancellationToken
    ): Promise<vscode.ChatResult> => {
        return this.handleChatRequest(request, context, stream, token);
    };

    private loadConfig(): RestrictedCopilotConfig {
        const config = vscode.workspace.getConfiguration('restrictedCopilot');
        return {
            restrictiveMode: config.get('restrictiveMode', true),
            inquisitiveMode: config.get('inquisitiveMode', true),
            maxContextLines: config.get('maxContextLines', 50),
            interceptCopilotChat: config.get('interceptCopilotChat', true),
            chatFilterStrength: config.get('chatFilterStrength', 'strict') as 'strict' | 'moderate' | 'permissive'
        };
    }

    public updateConfig(): void {
        this.config = this.loadConfig();
    }

    async handleChatRequest(
        request: vscode.ChatRequest,
        context: vscode.ChatContext,
        stream: vscode.ChatResponseStream,
        token: vscode.CancellationToken
    ): Promise<vscode.ChatResult> {
        
        const activeEditor = vscode.window.activeTextEditor;
        
        if (!activeEditor) {
            stream.markdown("❌ **Modo Restritivo Ativo**: Nenhum editor ativo encontrado. Por favor, abra um arquivo para análise.");
            return { metadata: { command: 'restricted-analysis' } };
        }

        // Get current context based on cursor position or selection
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
    }

    private getCurrentContext(editor: vscode.TextEditor): string {
        const selection = editor.selection;
        const document = editor.document;
        
        if (!selection.isEmpty) {
            // User has selected text - analyze only selection + limited context
            const contextRange = this.getLimitedContext(document, selection);
            return document.getText(contextRange);
        }
        
        // No selection - try to find current function
        const functionRange = this.findFunctionRange(document, selection.active);
        if (functionRange) {
            return document.getText(functionRange);
        }
        
        // Fallback to limited context around cursor
        const line = selection.active.line;
        const startLine = Math.max(0, line - this.config.maxContextLines / 2);
        const endLine = Math.min(document.lineCount - 1, line + this.config.maxContextLines / 2);
        const range = new vscode.Range(startLine, 0, endLine, document.lineAt(endLine).text.length);
        
        return document.getText(range);
    }

    private getLimitedContext(document: vscode.TextDocument, selection: vscode.Selection): vscode.Range {
        const maxLines = this.config.maxContextLines;
        const startLine = Math.max(0, selection.start.line - maxLines);
        const endLine = Math.min(document.lineCount - 1, selection.end.line + maxLines);
        
        return new vscode.Range(
            new vscode.Position(startLine, 0),
            new vscode.Position(endLine, document.lineAt(endLine).text.length)
        );
    }

    private findFunctionRange(document: vscode.TextDocument, position: vscode.Position): vscode.Range | null {
        const languageId = document.languageId;
        const text = document.getText();
        const lines = text.split('\n');
        const currentLine = position.line;

        let functionStart = -1;
        let functionEnd = -1;

        // Find function start (look backward)
        for (let i = currentLine; i >= 0; i--) {
            const line = lines[i].trim();
            
            if (this.isFunctionStart(line, languageId)) {
                functionStart = i;
                break;
            }
        }

        if (functionStart === -1) {
            return null;
        }

        // Find function end (look forward)
        let braceCount = 0;
        let inFunction = false;
        
        for (let i = functionStart; i < lines.length; i++) {
            const line = lines[i];
            
            for (const char of line) {
                if (char === '{') {
                    braceCount++;
                    inFunction = true;
                } else if (char === '}') {
                    braceCount--;
                    if (inFunction && braceCount === 0) {
                        functionEnd = i;
                        break;
                    }
                }
            }
            
            if (functionEnd !== -1) {
                break;
            }
        }

        if (functionEnd === -1) {
            functionEnd = Math.min(functionStart + 50, lines.length - 1);
        }

        return new vscode.Range(
            new vscode.Position(functionStart, 0),
            new vscode.Position(functionEnd, lines[functionEnd]?.length || 0)
        );
    }

    private isFunctionStart(line: string, languageId: string): boolean {
        const patterns = {
            javascript: /^(function\s+\w+|const\s+\w+\s*=\s*\([^)]*\)\s*=>|class\s+\w+)/,
            typescript: /^(function\s+\w+|const\s+\w+\s*:\s*[^=]*=|class\s+\w+|public\s+|private\s+|protected\s+)/,
            python: /^(def\s+\w+|class\s+\w+)/,
            java: /^(public\s+|private\s+|protected\s+).*\s+\w+\s*\(/,
            csharp: /^(public\s+|private\s+|protected\s+).*\s+\w+\s*\(/
        };

        const pattern = patterns[languageId as keyof typeof patterns] || patterns.javascript;
        return pattern.test(line);
    }

    private async processChatRequest(request: ChatRequest, editor: vscode.TextEditor): Promise<ChatResponse> {
        if (this.config.restrictiveMode) {
            return this.processRestrictedChat(request, request.context || '', editor);
        }
        
        return this.processPermissiveChat(request, request.context || '', editor);
    }

    private async processRestrictedChat(request: ChatRequest, context: string, editor: vscode.TextEditor): Promise<ChatResponse> {
        const restrictions: string[] = [];
        const fileName = editor.document.fileName;
        const language = editor.document.languageId;
        
        // Build restricted response
        let response = `🔒 **RESTRICTED COPILOT ATIVO** - Chat Mediado\n\n`;
        
        // Context information
        const contextLines = context.split('\n').length;
        response += `📍 **Contexto Analisado**: ${contextLines} linhas em \`${fileName.split('\\').pop()}\` (${language})\n\n`;
        
        // Check if request is asking for broad changes
        const broadRequestPatterns = [
            /refactor|reescrever|reestruturar|otimizar tudo/i,
            /melhorar todo|revisar todo|corrigir todo/i,
            /analisar arquivo|arquivo inteiro/i,
            /todo o código|código completo/i
        ];
        
        const isBroadRequest = broadRequestPatterns.some(pattern => pattern.test(request.prompt));
        
        if (isBroadRequest) {
            restrictions.push("Broad analysis request blocked");
            response += `❌ **SOLICITAÇÃO BLOQUEADA**: Análise muito ampla detectada.\n\n`;
            response += `🎯 **ESCOPO PERMITIDO**: Apenas o contexto atual:\n`;
            response += `   • Função onde está o cursor\n`;
            response += `   • Código selecionado + ${this.config.maxContextLines} linhas\n`;
            response += `   • Máximo ${this.config.maxContextLines * 2} linhas total\n\n`;
            response += `💡 **REFORMULE SUA PERGUNTA**:\n`;
            response += `   ✅ "Há bugs nesta função?"\n`;
            response += `   ✅ "Como otimizar este loop?"\n`;
            response += `   ✅ "Esta variável está correta?"\n`;
            response += `   ❌ "Melhore todo o arquivo"\n`;
            response += `   ❌ "Refatore tudo"\n\n`;
            
            return {
                content: response,
                filtered: true,
                restrictions
            };
        }
        
        // Inquisitive mode - ask clarifying questions
        if (this.config.inquisitiveMode) {
            response += `❓ **MODO INQUISITIVO**: Preciso esclarecer antes de prosseguir:\n\n`;
            
            if (request.prompt.toLowerCase().includes('corrigir') || request.prompt.toLowerCase().includes('fix')) {
                response += `🔧 **Sobre sua solicitação de correção**:\n`;
                response += `   A) Apenas identificar possíveis problemas?\n`;
                response += `   B) Sugerir correções específicas?\n`;
                response += `   C) Explicar o problema em detalhes?\n`;
                response += `   D) Mostrar código corrigido?\n\n`;
                response += `**Por favor, especifique qual opção deseja.**\n\n`;
            }
            
            if (request.prompt.toLowerCase().includes('melhorar') || request.prompt.toLowerCase().includes('otimizar')) {
                response += `⚡ **Sobre melhorias - qual aspecto específico?**:\n`;
                response += `   🚀 Performance/velocidade de execução\n`;
                response += `   📖 Legibilidade e clareza do código\n`;
                response += `   🛡️ Tratamento de erros e robustez\n`;
                response += `   🏗️ Estrutura e organização\n`;
                response += `   🔒 Segurança do código\n\n`;
                response += `**Escolha um ou mais aspectos específicos.**\n\n`;
            }
        }
        
        // Analyze current context for specific issues
        response += this.analyzeContextForIssues(context, language);
        
        // Add footer with current restrictions
        response += `\n---\n`;
        response += `🛡️ **STATUS DAS RESTRIÇÕES**:\n`;
        response += `🔒 Modo Restritivo: **ATIVO**\n`;
        response += `❓ Modo Inquisitivo: **${this.config.inquisitiveMode ? 'ATIVO' : 'INATIVO'}**\n`;
        response += `📏 Limite de Contexto: **${this.config.maxContextLines} linhas**\n`;
        response += `🎯 Escopo: **${this.getContextType(editor)}**\n\n`;
        
        response += `💡 **Para alterar configurações**: \`Ctrl+Shift+P\` → "Restricted Copilot: Toggle Restrictive Mode"\n`;
        
        return {
            content: response,
            filtered: restrictions.length > 0,
            restrictions
        };
    }

    private getContextType(editor: vscode.TextEditor): string {
        const selection = editor.selection;
        
        if (!selection.isEmpty) {
            return "Seleção + contexto limitado";
        }
        
        const functionRange = this.findFunctionRange(editor.document, selection.active);
        if (functionRange) {
            return "Função atual";
        }
        
        return "Contexto ao redor do cursor";
    }

    private analyzeContextForIssues(context: string, language: string): string {
        let analysis = `🔍 **ANÁLISE AUTOMÁTICA DO CONTEXTO**:\n\n`;
        
        const issues: string[] = [];
        const warnings: string[] = [];
        const info: string[] = [];
        
        // Check for debug statements
        if (context.includes('console.log') || context.includes('print(')) {
            warnings.push("🐛 Statements de debug detectados");
        }
        
        // Check for TODO/FIXME
        if (context.includes('TODO') || context.includes('FIXME')) {
            info.push("📝 Comentários TODO/FIXME encontrados");
        }
        
        // Check for error handling
        if (context.includes('try') && !context.includes('except') && !context.includes('catch')) {
            issues.push("⚠️ Try block sem tratamento de erro adequado");
        }
        
        // Language-specific checks
        if (language === 'python') {
            if (context.includes('import *')) {
                warnings.push("🚫 Import * detectado (não recomendado)");
            }
            if (context.match(/=\s*[^=]/g) && context.includes('if') && !context.includes('==')) {
                issues.push("🔴 Possível erro: atribuição (=) em vez de comparação (==)");
            }
        }
        
        if (language === 'javascript' || language === 'typescript') {
            if (context.includes('var ')) {
                warnings.push("📉 Uso de 'var' detectado (considere let/const)");
            }
        }
        
        // Present findings
        let hasFindings = false;
        
        if (issues.length > 0) {
            hasFindings = true;
            analysis += `🔴 **PROBLEMAS CRÍTICOS**:\n`;
            issues.forEach(issue => analysis += `   ${issue}\n`);
            analysis += `\n`;
        }
        
        if (warnings.length > 0) {
            hasFindings = true;
            analysis += `🟡 **AVISOS**:\n`;
            warnings.forEach(warning => analysis += `   ${warning}\n`);
            analysis += `\n`;
        }
        
        if (info.length > 0) {
            hasFindings = true;
            analysis += `🔵 **INFORMAÇÕES**:\n`;
            info.forEach(item => analysis += `   ${item}\n`);
            analysis += `\n`;
        }
        
        if (!hasFindings) {
            analysis += `✅ **Nenhum problema óbvio detectado** no contexto atual.\n\n`;
            analysis += `📋 **Contexto analisado está aparentemente correto.**\n\n`;
        }
        
        return analysis;
    }

    private async processPermissiveChat(request: ChatRequest, context: string, editor: vscode.TextEditor): Promise<ChatResponse> {
        let response = `🔓 **MODO PERMISSIVO ATIVO** - Análise Expandida\n\n`;
        
        const contextLines = context.split('\n').length;
        const fileName = editor.document.fileName;
        response += `📍 **Contexto**: ${contextLines} linhas em \`${fileName.split('\\').pop()}\`\n\n`;
        
        response += `💬 **Sua pergunta**: "${request.prompt}"\n\n`;
        response += `⚠️ **Nota**: Mesmo no modo permissivo, mantenho foco no contexto limitado para sua segurança.\n\n`;
        
        response += this.analyzeContextForIssues(context, editor.document.languageId);
        
        response += `---\n`;
        response += `🔓 Modo Permissivo: **ATIVO** (mais proativo)\n`;
        response += `📏 Contexto: **${contextLines} linhas analisadas**\n`;
        
        return {
            content: response,
            filtered: false,
            restrictions: []
        };
    }
}
