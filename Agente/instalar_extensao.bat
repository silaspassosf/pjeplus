@echo off
echo 🔄 Atualizando Restricted Copilot Extension...
echo.

echo 📦 Empacotando extensão...
call vsce package

echo.
echo 🚀 Instalando extensão no VS Code...
call code --install-extension restricted-copilot-0.0.1.vsix

echo.
echo ✅ Extensão Restricted Copilot atualizada com sucesso!
echo.
echo 📋 Para usar a extensão:
echo    1. Abra seu workspace PjePlus
echo    2. Coloque o cursor em uma função
echo    3. Clique com botão direito → "Analyze Current Function"
echo.
echo 💡 Ou use Ctrl+Shift+P e digite "Restricted Copilot"
echo.
pause
