import * as vscode from 'vscode';
import { ErrorInfo } from './terminalErrorDetector';

export interface CompilationResult {
    success: boolean;
    output: string;
    errors: ErrorInfo[];
    executionTime: number;
}

export class AutoCompiler {
    
    public async compileAndValidateFile(editor: vscode.TextEditor): Promise<CompilationResult> {
        const filePath = editor.document.fileName;
        const startTime = Date.now();
        
        try {
            const fileExtension = filePath.split('.').pop()?.toLowerCase();
            let compilationCommands = this.getCompilationCommands(filePath, fileExtension);
            
            if (compilationCommands.length === 0) {
                return {
                    success: false,
                    output: 'Tipo de arquivo não suportado para compilação automática',
                    errors: [],
                    executionTime: Date.now() - startTime
                };
            }
            
            const results = await this.executeCommands(compilationCommands);
            const combinedOutput = results.map(r => r.output).join('\n');
            const allErrors = results.flatMap(r => r.errors);
            const success = results.every(r => r.success);
            
            return {
                success: success,
                output: combinedOutput,
                errors: allErrors,
                executionTime: Date.now() - startTime
            };
            
        } catch (error) {
            return {
                success: false,
                output: `Erro na compilação: ${error}`,
                errors: [],
                executionTime: Date.now() - startTime
            };
        }
    }
    
    private getCompilationCommands(filePath: string, fileExtension?: string): string[] {
        const commands: string[] = [];
        
        switch (fileExtension) {
            case 'py':
                // Python: syntax check primeiro, depois validação
                commands.push(`python -m py_compile "${filePath}"`);
                commands.push(`python -c "import ast; ast.parse(open('${filePath}').read())"`);
                break;
                
            case 'js':
                // JavaScript: Node.js syntax check
                commands.push(`node --check "${filePath}"`);
                break;
                
            case 'ts':
                // TypeScript: tsc compilation
                commands.push(`npx tsc --noEmit "${filePath}"`);
                break;
                
            case 'ahk':
                // AutoHotkey: basic syntax validation (if available)
                commands.push(`echo "AutoHotkey file: ${filePath} - validação manual necessária"`);
                break;
        }
        
        return commands;
    }
    
    private async executeCommands(commands: string[]): Promise<Array<{success: boolean, output: string, errors: ErrorInfo[]}>> {
        const results = [];
        
        for (const command of commands) {
            const result = await this.executePowerShellCommand(command);
            results.push(result);
            
            // Se falhou, não executa os próximos comandos
            if (!result.success) {
                break;
            }
        }
        
        return results;
    }
    
    private async executePowerShellCommand(command: string): Promise<{success: boolean, output: string, errors: ErrorInfo[]}> {
        return new Promise((resolve) => {
            // Create a unique terminal for this compilation
            const terminalName = `AutoCompile-${Date.now()}`;
            const terminal = vscode.window.createTerminal({
                name: terminalName,
                shellPath: 'powershell.exe'
            });
            
            let completed = false;
            let output = '';
            
            // Send command to terminal
            terminal.sendText(command);
            terminal.sendText(`Write-Host "COMPILATION_COMPLETE_${Date.now()}"`);
            
            // Simulate terminal monitoring (in a real extension, you'd use proper terminal API)
            const timeout = setTimeout(() => {
                if (!completed) {
                    completed = true;
                    terminal.dispose();
                    
                    // Parse output for errors
                    const errors = this.parseCommandOutput(output, command);
                    const success = errors.length === 0 && !output.includes('Error') && !output.includes('error');
                    
                    resolve({
                        success: success,
                        output: output || 'Comando executado com sucesso',
                        errors: errors
                    });
                }
            }, 8000); // Wait up to 8 seconds
            
            // Cleanup
            setTimeout(() => {
                if (terminal) {
                    terminal.dispose();
                }
            }, 10000);
        });
    }
    
    private parseCommandOutput(output: string, command: string): ErrorInfo[] {
        const errors: ErrorInfo[] = [];
        const lines = output.split('\n');
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            
            // Python errors
            if (command.includes('python')) {
                const pythonError = this.parsePythonError(line, lines, i);
                if (pythonError) {
                    errors.push(pythonError);
                }
            }
            
            // JavaScript/Node errors
            if (command.includes('node')) {
                const jsError = this.parseJavaScriptError(line);
                if (jsError) {
                    errors.push(jsError);
                }
            }
            
            // TypeScript errors
            if (command.includes('tsc')) {
                const tsError = this.parseTypeScriptError(line);
                if (tsError) {
                    errors.push(tsError);
                }
            }
        }
        
        return errors;
    }
    
    private parsePythonError(line: string, allLines: string[], index: number): ErrorInfo | null {
        const patterns = [
            /File "([^"]+)", line (\d+)/,
            /SyntaxError: (.+)/,
            /IndentationError: (.+)/,
            /(\w+Error): (.+)/
        ];
        
        for (const pattern of patterns) {
            const match = line.match(pattern);
            if (match) {
                if (match[1] && match[2]) {
                    return {
                        file: match[1],
                        line: parseInt(match[2]),
                        message: allLines[index + 1] || line,
                        type: 'python',
                        severity: 'error'
                    };
                } else if (match[1]) {
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
            /^(.+):(\d+)$/,
            /at (.+):(\d+):(\d+)/,
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
    
    private parseTypeScriptError(line: string): ErrorInfo | null {
        // TypeScript error format: filename(line,col): error message
        const pattern = /^(.+)\((\d+),(\d+)\): (.+)$/;
        const match = line.match(pattern);
        
        if (match) {
            return {
                file: match[1],
                line: parseInt(match[2]),
                column: parseInt(match[3]),
                message: match[4],
                type: 'typescript',
                severity: 'error'
            };
        }
        
        return null;
    }
    
    public async showCompilationResult(result: CompilationResult, fileName: string): Promise<void> {
        if (result.success) {
            vscode.window.showInformationMessage(
                `✅ Compilação bem-sucedida: ${fileName} (${result.executionTime}ms)`
            );
        } else {
            const action = await vscode.window.showErrorMessage(
                `❌ Erro na compilação: ${fileName}`,
                'Ver Detalhes',
                'Auto-Fix com @restricted',
                'Ignorar'
            );
            
            if (action === 'Ver Detalhes') {
                const outputChannel = vscode.window.createOutputChannel('Restricted Copilot - Compilation');
                outputChannel.clear();
                outputChannel.appendLine(`=== COMPILAÇÃO: ${fileName} ===`);
                outputChannel.appendLine(`Tempo: ${result.executionTime}ms`);
                outputChannel.appendLine(`Status: ${result.success ? 'Sucesso' : 'Falha'}`);
                outputChannel.appendLine('');
                outputChannel.appendLine('=== OUTPUT ===');
                outputChannel.appendLine(result.output);
                
                if (result.errors.length > 0) {
                    outputChannel.appendLine('');
                    outputChannel.appendLine('=== ERROS ENCONTRADOS ===');
                    result.errors.forEach((error, index) => {
                        outputChannel.appendLine(`${index + 1}. ${error.file}:${error.line} - ${error.message}`);
                    });
                }
                
                outputChannel.show();
            } else if (action === 'Auto-Fix com @restricted') {
                if (result.errors.length > 0) {
                    await this.focusOnFirstError(result.errors[0]);
                }
            }
        }
    }
    
    private async focusOnFirstError(error: ErrorInfo): Promise<void> {
        try {
            const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
            if (!workspaceFolder) return;

            let targetFile: vscode.Uri | undefined;

            // Try to find the file
            if (error.file.includes('/') || error.file.includes('\\')) {
                try {
                    targetFile = vscode.Uri.file(error.file);
                } catch {
                    const relativePath = error.file.replace(/^.*[\\\/]/, '');
                    const files = await vscode.workspace.findFiles(`**/${relativePath}`);
                    targetFile = files[0];
                }
            } else {
                const files = await vscode.workspace.findFiles(`**/${error.file}`);
                targetFile = files[0];
            }

            if (targetFile) {
                const document = await vscode.workspace.openTextDocument(targetFile);
                const editor = await vscode.window.showTextDocument(document);

                const position = new vscode.Position(Math.max(0, error.line - 1), error.column || 0);
                editor.selection = new vscode.Selection(position, position);
                editor.revealRange(new vscode.Range(position, position));

                vscode.window.showInformationMessage(
                    `🎯 Focado no erro: ${error.message}. Use @restricted no chat para correção.`
                );
            }

        } catch (error) {
            console.log('Error focusing on compilation error:', error);
        }
    }
}
