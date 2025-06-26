# Restricted Copilot

A VS Code extension that provides AI assistance with strict context limitations and user control. Designed for environments where careful, controlled code analysis is required. **Now includes automatic compilation and error detection!**

## 🎯 Purpose

This extension addresses scenarios where standard AI assistants might be too broad or presumptuous:
- **Sensitive codebases** requiring limited AI exposure
- **Learning environments** where step-by-step analysis is preferred  
- **Code reviews** needing focused, specific feedback
- **Legacy systems** where broad suggestions could be harmful
- **Development workflows** requiring automatic error detection and fixing

## ✨ Features

### 🔒 Restrictive Mode (Default: Enabled)
- **No unsolicited suggestions** - Only analyzes what you explicitly request
- **Limited scope analysis** - Focuses only on selected functions or code blocks
- **Prevents scope creep** - Won't suggest changes to unrelated code

### ❓ Inquisitive Mode (Default: Enabled)  
- **Always asks before changes** - Requires explicit permission for modifications
- **Multiple options** - Presents choices instead of making assumptions
- **Clear impact explanation** - Shows exactly what will be changed

### 🔧 **NEW: Auto-Compile & Fix**
- **Automatic compilation** - Validates Python, JavaScript, TypeScript files
- **Error detection** - Monitors logs and automatically focuses on error lines
- **PowerShell integration** - Windows-optimized commands without && operators
- **Smart navigation** - Jumps directly to problematic code
- **Chat integration** - Seamless connection with @restricted for fixes

### 💬 Chat Participant (@restricted)
- **@restricted** participant in GitHub Copilot Chat
- **Filtered responses** - All AI responses pass through restrictive filter
- **Context-aware** - Respects the limited context settings
- **Integration with auto-compile** - Provides fixes for detected errors

### 📏 Context Limitations
- **Function analysis**: Analyzes only the current function (from declaration to closing brace)
- **Selection analysis**: Analyzes selection + configurable context (default: 50 lines before/after)
- **Maximum context**: Never exceeds 200 lines total
- **Incremental expansion**: Can expand context in 50-line increments with permission

## 🚀 Usage

### Right-click Context Menu
1. **Analyze Current Function** - Place cursor in any function and right-click
2. **Analyze Selection with Limited Context** - Select code and right-click

### Command Palette
- `Restricted Copilot: Analyze Current Function`
- `Restricted Copilot: Analyze Selection with Limited Context` 
- `Restricted Copilot: Toggle Restrictive Mode`

### Example Workflow
1. Place cursor in a function
2. Right-click → "Analyze Current Function"
3. Extension shows analysis in side panel
4. Ask specific questions about the code
5. Request specific changes if needed
6. Confirm before any modifications are applied

## ⚙️ Configuration

### Settings

Access settings via: File → Preferences → Settings → Extensions → Restricted Copilot

- **`restrictedCopilot.restrictiveMode`** (boolean, default: `true`)
  - When enabled: No unsolicited suggestions, only analyzes explicitly requested code
  - When disabled: More proactive analysis and suggestions

- **`restrictedCopilot.inquisitiveMode`** (boolean, default: `true`)  
  - When enabled: Always asks before making changes
  - When disabled: Can apply approved changes immediately

- **`restrictedCopilot.maxContextLines`** (number, default: `50`, range: 10-200)
  - Maximum lines of context around selections
  - Higher values provide more context but less restriction

### Typical Configurations

**Maximum Security** (recommended for sensitive code):
```json
{
  "restrictedCopilot.restrictiveMode": true,
  "restrictedCopilot.inquisitiveMode": true,
  "restrictedCopilot.maxContextLines": 25
}
```

**Balanced Mode** (good for general development):
```json
{
  "restrictedCopilot.restrictiveMode": true,
  "restrictedCopilot.inquisitiveMode": true,  
  "restrictedCopilot.maxContextLines": 50
}
```

**Learning Mode** (expanded context for educational purposes):
```json
{
  "restrictedCopilot.restrictiveMode": false,
  "restrictedCopilot.inquisitiveMode": true,
  "restrictedCopilot.maxContextLines": 100
}
```

## 🤝 Integration with GitHub Copilot

This extension is designed to **complement**, not replace, GitHub Copilot:

- **Use GitHub Copilot** for: Autocomplete, broad suggestions, new code generation
- **Use Restricted Copilot** for: Focused analysis, sensitive code review, controlled refactoring

Both can be active simultaneously - Restricted Copilot provides a "cautious mode" when you need more control.

## 📋 Requirements

- VS Code 1.101.0 or higher
- No additional dependencies required
- Works with any programming language (language-specific features optimized for JavaScript, TypeScript, Python, Java, C#)

## 🐛 Known Issues

- Function detection may not work perfectly with all coding styles (especially heavily nested or unconventional formatting)
- Context analysis limited to text-based parsing (no full AST analysis)
- Webview panel may not preserve state between VS Code restarts

## 📝 Release Notes

### 0.0.1 (Initial Release)

- ✨ **Core Features**:
  - Function-scoped analysis with automatic boundary detection
  - Selection-based analysis with configurable context limits
  - Restrictive mode (no unsolicited suggestions)
  - Inquisitive mode (ask before changes)

- 🎯 **Supported Languages**:
  - JavaScript, TypeScript, Python, Java, C# function detection
  - Generic analysis for other languages

- ⚙️ **Configuration**:
  - Three configuration options with sensible defaults
  - Right-click context menu integration
  - Command palette commands

## 🔄 Future Roadmap

- **Enhanced Language Support**: Better AST-based parsing for more languages
- **AI Integration**: Optional integration with AI providers for actual suggestions
- **Team Settings**: Workspace-level configuration for teams
- **Analysis Templates**: Predefined analysis types (security, performance, style)

## 🚀 Development

### Building from Source
```bash
cd Agente
npm install
npm run compile
```

### Testing
```bash
npm run test
```

### Packaging
```bash
npm run package
```

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

Contributions welcome! Please read contributing guidelines and submit PRs for:
- Additional language support
- Better function detection algorithms  
- UI/UX improvements
- Bug fixes

---

**Enjoy responsible AI assistance with Restricted Copilot!** 🎯
