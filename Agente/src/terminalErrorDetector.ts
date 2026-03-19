import * as vscode from 'vscode';
import { AutoCompiler } from './autoCompiler';

export interface ErrorInfo {
    file: string;
    line: number;
    column?: number;
    message: string;
    type: 'python' | 'javascript' | 'typescript' | 'selenium' | 'generic';
    severity: 'error' | 'warning';
}

export class TerminalErrorDetector {
    private terminals: Map<vscode.Terminal, string> = new Map();
    private lastOutput: Map<vscode.Terminal, string> = new Map();
    private isWatching = false;
    private autoCompiler: AutoCompiler;
    
    constructor() {
        this.autoCompiler = new AutoCompiler();
        this.setupTerminalWatcher();
    }

    public startWatching(): void {
        if (this.isWatching) return;
        
        this.isWatching = true;
        console.log('🔍 Restricted Copilot: Monitoramento de erros ativado');
        
        // Start monitoring existing terminals
        for (const terminal of vscode.window.terminals) {
            this.terminals.set(terminal, '');
            this.lastOutput.set(terminal, '');
        }

        // Start output polling
        this.startOutputPolling();
    }

    public stopWatching(): void {
        this.isWatching = false;
        console.log('🔍 Restricted Copilot: Monitoramento de erros desativado');
    }

    public async compileCurrentFile(): Promise<void> {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('Nenhum arquivo ativo para compilar');
            return;
        }

        const fileName = editor.document.fileName.split('\\').pop() || editor.document.fileName.split('/').pop() || 'arquivo';
        
        vscode.window.showInformationMessage(`🔧 Compilando: ${fileName}...`);
        
        const result = await this.autoCompiler.compileAndValidateFile(editor);
        await this.autoCompiler.showCompilationResult(result, fileName);
        
        // If compilation failed, focus on first error
        if (!result.success && result.errors.length > 0) {
            await this.focusOnError(result.errors[0]);
        }
    }

    private setupTerminalWatcher(): void {
        // Monitor when terminals are created
        vscode.window.onDidOpenTerminal(terminal => {
            this.terminals.set(terminal, '');
            this.lastOutput.set(terminal, '');
        });

        // Monitor when terminals are closed
        vscode.window.onDidCloseTerminal(terminal => {
            this.terminals.delete(terminal);
            this.lastOutput.delete(terminal);
        });
    }

    private startOutputPolling(): void {
        const checkInterval = setInterval(async () => {
            if (!this.isWatching) {
                clearInterval(checkInterval);
                return;
            }
            
            for (const terminal of vscode.window.terminals) {
                await this.checkTerminalForErrors(terminal);
            }
        }, 3000); // Check every 3 seconds
    }

    private async checkTerminalForErrors(terminal: vscode.Terminal): Promise<void> {
        try {
            const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
            if (!workspaceFolder) return;

            // Check for common error log files in PjePlus workspace
            const errorLogFiles = [
                'pje_automacao.log',
                'pje_automation.log', 
                'erro_fatal_selenium.log'
            ];

            for (const logPattern of errorLogFiles) {
                const files = await vscode.workspace.findFiles(
                    new vscode.RelativePattern(workspaceFolder, logPattern)
                );

                for (const file of files) {
                    await this.analyzeLogFile(file);
                }
            }

        } catch (error) {
            console.log('Error monitoring terminal:', error);
        }
    }

    private async analyzeLogFile(logFile: vscode.Uri): Promise<void> {
        try {
            const document = await vscode.workspace.openTextDocument(logFile);
            const content = document.getText();
            
            // Parse recent errors (last 15 lines)
            const lines = content.split('\n').slice(-15);
            const recentContent = lines.join('\n');
            
            const errors = this.parseErrors(recentContent, logFile.fsPath);
            
            if (errors.length > 0) {
                await this.handleDetectedErrors(errors);
            }
        } catch (error) {
            console.log('Error analyzing log file:', error);
        }
    }

    private parseErrors(content: string, source: string): ErrorInfo[] {
        const errors: ErrorInfo[] = [];
        const lines = content.split('\n');

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            
            // Python errors
            const pythonError = this.parsePythonError(line, lines, i);
            if (pythonError) {
                errors.push(pythonError);
            }

            // JavaScript/Node errors
            const jsError = this.parseJavaScriptError(line);
            if (jsError) {
                errors.push(jsError);
            }

            // Selenium errors
            const seleniumError = this.parseSeleniumError(line);
            if (seleniumError) {
                errors.push(seleniumError);
            }
        }

        return errors;
    }

    private parsePythonError(line: string, allLines: string[], index: number): ErrorInfo | null {
        // Python traceback patterns
        const patterns = [
            /File "([^"]+)", line (\d+)(?:, in (.+))?/,
            /(\w+Error): (.+)/,
            /SyntaxError: (.+)/,
            /IndentationError: (.+)/,
            /NameError: (.+)/,
            /AttributeError: (.+)/,
            /TypeError: (.+)/,
            /ModuleNotFoundError: (.+)/,
            /ImportError: (.+)/
        ];

        for (const pattern of patterns) {
            const match = line.match(pattern);
            if (match) {
                if (match[1] && match[2]) {
                    // File and line number
                    return {
                        file: match[1],
                        line: parseInt(match[2]),
                        message: allLines[index + 1] || line,
                        type: 'python',
                        severity: 'error'
                    };
                } else {
                    // Error message
                    const prevLine = index > 0 ? allLines[index - 1] : '';
                    const fileMatch = prevLine.match(/File "([^"]+)", line (\d+)/);
                    
                    if (fileMatch) {
                        return {
                            file: fileMatch[1],
                            line: parseInt(fileMatch[2]),
                            message: match[0],
                            type: 'python',
                            severity: 'error'
                        };
                    }
                }
            }
        }

        return null;
    }

    private parseJavaScriptError(line: string): ErrorInfo | null {
        const patterns = [
            /at (.+):(\d+):(\d+)/,
            /(\w+Error): (.+)/,
            /SyntaxError: (.+)/
        ];

        for (const pattern of patterns) {
            const match = line.match(pattern);
            if (match) {
                if (match[1] && match[2]) {
                    return {
                        file: match[1],
                        line: parseInt(match[2]),
                        column: match[3] ? parseInt(match[3]) : undefined,
                        message: line,
                        type: 'javascript',
                        severity: 'error'
                    };
                }
            }
        }

        return null;
    }

    private parseSeleniumError(line: string): ErrorInfo | null {
        const patterns = [
            /selenium\.common\.exceptions\.(\w+): (.+)/,
            /WebDriverException: (.+)/,
            /TimeoutException: (.+)/,
            /NoSuchElementException: (.+)/,
            /ElementNotInteractableException: (.+)/,
            /StaleElementReferenceException: (.+)/
        ];

        for (const pattern of patterns) {
            const match = line.match(pattern);
            if (match) {
                return {
                    file: 'selenium_error',
                    line: 0,
                    message: match[0],
                    type: 'python',
                    severity: 'error'
                };
            }
        }

        return null;
    }

    private async handleDetectedErrors(errors: ErrorInfo[]): Promise<void> {
        for (const error of errors) {
            await this.focusOnError(error);
        }
    }

    private async focusOnError(error: ErrorInfo): Promise<void> {
        try {
            const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
            if (!workspaceFolder) return;

            let targetFile: vscode.Uri | undefined;

            // Try to find the file
            if (error.file.includes('/') || error.file.includes('\\')) {
                try {
                    targetFile = vscode.Uri.file(error.file);
                } catch {
                    // Try relative to workspace
                    const relativePath = error.file.replace(/^.*[\\\/]/, '');
                    const files = await vscode.workspace.findFiles(`**/${relativePath}`);
                    targetFile = files[0];
                }
            } else if (error.file !== 'selenium_error') {
                // Just filename - search in workspace
                const files = await vscode.workspace.findFiles(`**/${error.file}`);
                targetFile = files[0];
            }

            if (targetFile) {
                // Open the file and navigate to the error line
                const document = await vscode.workspace.openTextDocument(targetFile);
                const editor = await vscode.window.showTextDocument(document);

                // Navigate to the error line
                const position = new vscode.Position(Math.max(0, error.line - 1), error.column || 0);
                editor.selection = new vscode.Selection(position, position);
                editor.revealRange(new vscode.Range(position, position));

                // Show error message and offer auto-fix
                const action = await vscode.window.showErrorMessage(
                    `🔴 ERRO DETECTADO: ${error.message}`,
                    'Auto-Compile & Fix',
                    'Analisar com @restricted',
                    'Ignorar'
                );

                if (action === 'Auto-Compile & Fix') {
                    await this.compileCurrentFile();
                } else if (action === 'Analisar com @restricted') {
                    await this.analyzeErrorContext(error, editor);
                }
            } else if (error.file === 'selenium_error') {
                // For Selenium errors, show notification and open chat
                vscode.window.showErrorMessage(
                    `🕷️ ERRO SELENIUM: ${error.message}`,
                    'Analisar com @restricted',
                    'Ignorar'
                ).then(action => {
                    if (action === 'Analisar com @restricted') {
                        vscode.commands.executeCommand('workbench.panel.chat.view.copilot.focus');
                        vscode.window.showInformationMessage(
                            '💬 Use @restricted no chat para analisar o erro Selenium'
                        );
                    }
                });
            }

        } catch (error) {
            console.log('Error focusing on error:', error);
        }
    }

    private async analyzeErrorContext(error: ErrorInfo, editor: vscode.TextEditor): Promise<void> {
        // Select context around the error for analysis
        const document = editor.document;
        const errorLine = Math.max(0, error.line - 1);
        const startLine = Math.max(0, errorLine - 10);
        const endLine = Math.min(document.lineCount - 1, errorLine + 10);
        
        const startPos = new vscode.Position(startLine, 0);
        const endPos = new vscode.Position(endLine, document.lineAt(endLine).text.length);
        
        editor.selection = new vscode.Selection(startPos, endPos);
        
        vscode.window.showInformationMessage(
            `📍 Contexto selecionado ao redor da linha ${error.line}. Use @restricted no chat para análise.`
        );
    }
}
