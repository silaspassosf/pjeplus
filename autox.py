#!/usr/bin/env python3
"""autox.py — monitora o clipboard e aplica blocos PJePlus automaticamente

Fluxo resumido:
- monitorar clipboard
- detectar respostas PJePlus (## Objetivo + ## Alteração Proposta)
- ao detectar: enviar markdown para o chat do Copilot no VS Code via GUI
"""
import os
import re
import time

import pyperclip

import tkinter as tk
from tkinter import scrolledtext
import threading

RAIZ = os.path.dirname(os.path.abspath(__file__))
INTERVALO = 1.5  # segundos entre checagens
SEND_COUNT = 0
SENTINEL = "<!-- pjeplus:apply -->"


def extrair_blocos(texto):
    """Extrai listas de arquivos, trechos originais e propostas do markdown.

    Tolerante a variações de espaçamento, CRLF e acentos.
    """
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    arquivos = re.findall(r"-\s*`([^`]+\.[^`]+)`", texto)
    originais = re.findall(r"##\s*Trecho\s+Original\s*\n```[^\n]*\n(.*?)(?:^```|^##)", texto, re.DOTALL | re.MULTILINE)
    propostas = re.findall(r"##\s*Altera[çc][aã]o\s+Proposta\s*\n```[^\n]*\n(.*?)(?:^```|^##)", texto, re.DOTALL | re.MULTILINE)
    try:
        log(f"   arquivos encontrados: {arquivos}")
        log(f"   blocos originais: {len(originais)}")
        log(f"   blocos propostas: {len(propostas)}")
    except Exception:
        print(f"   arquivos encontrados: {arquivos}")
        print(f"   blocos originais: {len(originais)}")
        print(f"   blocos propostas: {len(propostas)}")
    return arquivos, originais, propostas


def criar_janela_log():
    global _log_widget
    root = tk.Tk()
    root.title("autox — monitor clipboard")
    root.geometry("700x400")
    _log_widget = scrolledtext.ScrolledText(root, state="disabled", font=("Consolas", 9))
    _log_widget.pack(fill="both", expand=True)
    root.mainloop()


_log_widget = None


def log(msg):
    """Substitui print — exibe na janela e no terminal."""
    try:
        print(msg)
    except Exception:
        pass
    if _log_widget:
        try:
            _log_widget.configure(state="normal")
            _log_widget.insert("end", msg + "\n")
            _log_widget.see("end")
            _log_widget.configure(state="disabled")
        except Exception:
            pass


def aplicar(texto):
    """Enviar o markdown ao chat do Copilot no VS Code.

    Usa pygetwindow/pyautogui para automação; usa win32gui para foco confiável
    e tenta localizar o campo de input por imagem antes de colar.
    """
    global SEND_COUNT
    try:
        import pygetwindow as gw
        import pyautogui
    except Exception as e:
        log(f"⚠️  Dependência ausente: {e} — instalar pygetwindow e pyautogui")
        return

    try:
        log("📨 Iniciando envio ao Copilot...")
        pyperclip.copy(texto)
        log(f"📋 Clipboard preenchido ({len(texto)} chars)")

        # Tentar foco via Win32 para maior confiabilidade
        try:
            import win32gui
            import win32con

            def encontrar_vscode(hwnd, resultado):
                if win32gui.IsWindowVisible(hwnd):
                    titulo = win32gui.GetWindowText(hwnd)
                    if "Visual Studio Code" in titulo:
                        resultado.append((hwnd, titulo))

            janelas = []
            win32gui.EnumWindows(encontrar_vscode, janelas)
            log(f"🪟 Janelas VS Code encontradas: {[t for _, t in janelas]}")

            if not janelas:
                log("⚠️  VS Code não encontrado.")
                return

            hwnd, titulo = janelas[0]
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            except Exception:
                pass
            try:
                win32gui.SetForegroundWindow(hwnd)
            except Exception as e:
                log(f"⚠️  Falha ao trazer janela ao primeiro plano: {e}")
            log(f"🎯 Janela ativada: {titulo}")
            time.sleep(0.8)

            # Tenta abrir painel Copilot e localizar input
            try:
                log("🤖 Focando input do Copilot Chat via command nativo...")
                # Abre o Command Palette e executa o command ID que foca o input do Copilot Chat
                try:
                    pyautogui.hotkey("ctrl", "shift", "p")
                    time.sleep(0.35)
                    pyautogui.typewrite("workbench.panel.chat.view.copilot.focus", interval=0.03)
                    time.sleep(0.25)
                    pyautogui.press("enter")
                    time.sleep(0.6)  # aguarda painel abrir e foco assentar
                    log("🎯 Foco no input via command nativo — colando...")
                    log("🔎 Comando executado: workbench.panel.chat.view.copilot.focus")
                except Exception as e:
                    log(f"⚠️  Falha ao executar command palette: {e}")

                log("⌨️  Colando no chat...")
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.5)

                log("↵  Enviando...")
                pyautogui.press("enter")
                SEND_COUNT += 1
                log(f"✅ Enviado. [envio #{SEND_COUNT} — apenas este deve aparecer]")
                return  # evita execução duplicada abaixo
            except Exception as e:
                log(f"⚠️  Falha na sequência de foco/cola: {e}")
                return

        except Exception:
            # Fallback: usar pygetwindow se win32 não disponível
            janelas = [w for w in gw.getAllWindows() if "Visual Studio Code" in w.title]
            log(f"🪟 (fallback) Janelas VS Code encontradas: {[w.title for w in janelas]}")
            if not janelas:
                log("⚠️  VS Code não encontrado.")
                return
            try:
                janelas[0].activate()
                log(f"🎯 Janela ativada: {janelas[0].title}")
            except Exception as e:
                log(f"⚠️  Falha ao ativar janela via pygetwindow: {e}")
            time.sleep(0.8)

            # Fallback de cola (só chega aqui se win32 falhou completamente)
            log("⌨️  Colando no chat (fallback)...")
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.5)
            log("↵  Enviando...")
            pyautogui.press("enter")
            SEND_COUNT += 1
            log(f"✅ Enviado. [envio #{SEND_COUNT} — apenas este deve aparecer]")

    except Exception as e:
        import traceback
        log(f"❌ ERRO em aplicar: {e}")
        log(traceback.format_exc())


def monitorar():
    log("👁  Monitorando clipboard...\n")
    ultimo = ""
    while True:
        try:
            atual = pyperclip.paste()
            if atual != ultimo:
                ultimo = atual
                tem_sentinel = SENTINEL in atual
                log(f"📋 Clipboard atualizado — {len(atual)} chars | sentinel={tem_sentinel}")
                if tem_sentinel:
                    log("🔔 Sentinel PJePlus detectado — enviando ao Copilot...")
                    aplicar(atual)
                    log("👁  Aguardando próxima resposta...\n")
            time.sleep(INTERVALO)
        except KeyboardInterrupt:
            log("⛔ Monitor encerrado.")
            break
        except Exception as e:
            log(f"⚠️  Erro: {e}")
            time.sleep(INTERVALO)


if __name__ == "__main__":
    import sys
    import subprocess
    import shutil

    if "--background" in sys.argv:
        threading.Thread(target=criar_janela_log, daemon=True).start()
        time.sleep(0.5)
        monitorar()
    elif "--debug" in sys.argv:
        _log_widget = None
        monitorar()
    else:
        python = shutil.which("python") or "python"
        args = [python, __file__, "--background"]
        try:
            subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.DETACHED_PROCESS,
            )
            print("✅ Monitor iniciado em background.")
        except Exception as e:
            print("⚠️  Falha ao iniciar em background:", e)
            print("↪️  Tentando executar no foreground...")
            threading.Thread(target=criar_janela_log, daemon=True).start()
            time.sleep(0.5)
            monitorar()
