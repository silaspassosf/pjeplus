# setup_credenciais.py — rode uma vez por máquina, depois pode apagar - isntalar antes pip install keyring e para autox pip install pygetwindow pyautogui
import keyring

keyring.set_password("pjeplus", "PASTEBIN_API_KEY",  "zfWDdpVkEeZ3A8fcYWYk-GZCCCF6gBDG")  # chave de API genérica, não é segredo
keyring.set_password("pjeplus", "PASTEBIN_USER",     "silaspf")
keyring.set_password("pjeplus", "PASTEBIN_PASSWORD", "SpFpaste866!")
keyring.set_password("pjeplus", "GITHUB_TOKEN",      "SEU_GITHUB_TOKEN_AQUI")
keyring.set_password("pjeplus", "PJE_USER",          "35305203813")
keyring.set_password("pjeplus", "PJE_SENHA",         "SpF5986!")
keyring.set_password("pjeplus", "SISB_USER",         "SEU_USUARIO_SISB_AQUI")
keyring.set_password("pjeplus", "SISB_SENHA",        "SUA_SENHA_SISB_AQUI")

print("✅ Credenciais salvas no Windows Credential Manager")