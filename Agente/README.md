# Restricted Copilot

### 📏 Limited Context (FIXED: 300 LINES)
- ✅ **Function analysis**: Analyzes only the current function
- ✅ **Selection analysis**: Selection + 150 lines before/after (total: 300 lines max)
- ✅ **No expansion**: Context never exceeds 300 lines
- ✅ **Consistent behavior**: Same limits every timeCode extension with **FIXED BEHAVIOR** - always operates with restrictive, inquisitive, and limited context (300 lines). **No configuration needed!**

## 🎯 Purpose

This extension provides **consistent, controlled AI assistance** with fixed parameters:
- **🔒 ALWAYS Restrictive** - No unsolicited suggestions
- **❓ ALWAYS Inquisitive** - Always asks before changes  
- **📏 ALWAYS Limited** - Maximum 300 lines of context
- **🔧 ALWAYS Auto-compile** - Automatic error detection and fixing

## ✨ Fixed Features (No Configuration Required)

### 🔒 Restrictive Mode (ALWAYS ACTIVE)
- ✅ **No unsolicited suggestions** - Only analyzes what you explicitly request
- ✅ **Limited scope analysis** - Focuses only on selected functions or code blocks
- ✅ **Prevents scope creep** - Won't suggest changes to unrelated code

### ❓ Inquisitive Mode (ALWAYS ACTIVE)  
- ✅ **Always asks before changes** - Requires explicit permission for modifications
- ✅ **Multiple options** - Presents choices instead of making assumptions
- ✅ **Clear impact explanation** - Shows exactly what will be changed

### � Limited Context (FIXED: 50 LINES)
- ✅ **Function analysis**: Analyzes only the current function
- ✅ **Selection analysis**: Selection + 25 lines before/after (total: 50 lines max)
- ✅ **No expansion**: Context never exceeds 50 lines
- ✅ **Consistent behavior**: Same limits every time

### � Auto-Compile & Fix (ALWAYS ACTIVE)
- ✅ **Automatic compilation** - Validates Python, JavaScript, TypeScript files
- ✅ **Error detection** - Monitors logs and automatically focuses on error lines
- ✅ **PowerShell integration** - Windows-optimized commands
- ✅ **Smart navigation** - Jumps directly to problematic code

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

- **`restrictedCopilot.maxContextLines`** (number, default: `300`, range: 10-500)
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
  "restrictedCopilot.maxContextLines": 300
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

## 🚫 **PjePlus-Specific Guidelines (ALWAYS ENFORCED)** 
- **❌ NO creating test files** - No test.py, spec.js, or similar test files
- **❌ NO creating reports** - No report generation or documentation files  
- **❌ NO file creation suggestions** - Focus only on existing code analysis
- **✅ PowerShell testing only** - Use `py script.py` (no && operators)
- **✅ Autocompile integration** - Built-in error detection and fixing
- **✅ Existing code focus** - Analyze, optimize, and fix current files only

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
