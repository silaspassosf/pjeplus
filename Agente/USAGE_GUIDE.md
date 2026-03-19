# 🎯 Restricted Copilot Extension - Installation & Usage Guide

## ✅ Extension Status: READY FOR USE

Your "Restricted Copilot" VS Code extension has been successfully created and compiled. Here's how to use it:

## 🚀 Quick Start

### 1. Extension is Already Loaded
The extension has been compiled and is ready to use. You can see it in your VS Code workspace.

### 2. Testing the Extension
A test development window should have opened automatically. If not, run:
```powershell
cd "d:\PjePlus\Agente"
code --extensionDevelopmentHost=. .
```

### 3. Using the Extension

#### Method 1: Right-Click Context Menu
1. Open the `test-example.js` file in the Agente folder
2. Place your cursor inside any function (e.g., `calculateTotal`)
3. Right-click → Select "Analyze Current Function"
4. A side panel will open showing the restricted analysis

#### Method 2: Command Palette
1. Press `Ctrl+Shift+P` (Windows) to open Command Palette
2. Type "Restricted Copilot"
3. Choose from:
   - `Restricted Copilot: Analyze Current Function`
   - `Restricted Copilot: Analyze Selection with Limited Context`
   - `Restricted Copilot: Toggle Restrictive Mode`

#### Method 3: Selection Analysis
1. Select some code in any file
2. Right-click → "Analyze Selection with Limited Context"
3. Extension will analyze only the selection + 50 lines of context

## ⚙️ Configuration

Access via: File → Preferences → Settings → Extensions → Restricted Copilot

- **Restrictive Mode** (default: ON) - Prevents unsolicited suggestions
- **Inquisitive Mode** (default: ON) - Asks before making changes  
- **Max Context Lines** (default: 50) - Limits analysis scope

## 🔍 Key Features Demonstrated

### Restrictive Behavior
- ✅ Only analyzes code you explicitly request
- ✅ Won't suggest changes to other functions or files
- ✅ Shows warning when restrictive mode is active
- ✅ Limits context to specified function or selection

### Inquisitive Behavior  
- ✅ Asks what specific aspect you want analyzed
- ✅ Presents options instead of making assumptions
- ✅ Requires confirmation before any code changes
- ✅ Explains the scope and impact of suggestions

### Context Limitations
- ✅ Function analysis: from declaration to closing brace only
- ✅ Selection analysis: selection + configurable context lines
- ✅ Maximum 200 lines total context
- ✅ Can expand context incrementally with permission

## 🧪 Test Scenarios

Use the `test-example.js` file to test these scenarios:

1. **Function Analysis**: Place cursor in `calculateTotal()` function
   - Should detect TODO and console.log statements
   - Should offer to analyze only that function
   - Should NOT suggest changes to other functions

2. **Selection Analysis**: Select just the for loop in `calculateTotal()`
   - Should analyze loop + surrounding context
   - Should respect max context lines setting
   - Should ask permission to expand context if needed

3. **Restrictive Mode**: Try to get suggestions for the entire file
   - Should refuse and ask you to specify what to analyze
   - Should show restrictive mode warning

## 🔧 Troubleshooting

### Extension Not Visible
If the extension doesn't appear in the context menu:
1. Ensure VS Code version is 1.101.0+
2. Check that the extension compiled successfully (no errors above)
3. Reload the extension development window (Ctrl+R)

### Watch Mode Issues
If you make changes to the extension code:
1. The watch mode is already running (background terminal)
2. Changes should auto-compile
3. Reload the development window to see changes

### Configuration Not Working
1. Close and reopen VS Code
2. Check that settings are being saved in the correct scope (User vs Workspace)
3. Use Command Palette → "Developer: Reload Window"

## 📦 Installation for Regular Use

### Option 1: Install Locally (Recommended)
```powershell
cd "d:\PjePlus\Agente"
npm run package  # Creates .vsix file
code --install-extension restricted-copilot-0.0.1.vsix
```

### Option 2: Copy to Extensions Folder
1. Copy the entire `Agente` folder to your VS Code extensions directory
2. Restart VS Code
3. The extension will be available in all workspaces

## 🎯 Usage Best Practices

### For Sensitive Code
```json
{
  "restrictedCopilot.restrictiveMode": true,
  "restrictedCopilot.inquisitiveMode": true,
  "restrictedCopilot.maxContextLines": 25
}
```

### For Learning/Teaching
```json
{
  "restrictedCopilot.restrictiveMode": false,
  "restrictedCopilot.inquisitiveMode": true,
  "restrictedCopilot.maxContextLines": 100
}
```

## ✨ Success Indicators

The extension is working correctly if you see:
- ✅ "Restricted Copilot is ready!" message when VS Code starts
- ✅ Context menu items when right-clicking in code
- ✅ Commands available in Command Palette
- ✅ Analysis panel opens when using commands
- ✅ Configuration settings are respected

## 🔄 Next Steps

1. **Test thoroughly** with your actual code files
2. **Adjust settings** based on your security/analysis needs
3. **Package for distribution** if you want to share with team
4. **Submit feedback** for any improvements needed

## 📞 Support

If you encounter issues:
1. Check the VS Code Developer Console (Help → Toggle Developer Tools)
2. Look for error messages in the console
3. Verify the extension is listed in Extensions view
4. Check that all files compiled without TypeScript errors

---

**Your Restricted Copilot extension is ready to provide controlled, focused AI assistance! 🎉**
