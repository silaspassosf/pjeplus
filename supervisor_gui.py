import threading
import tkinter as tk
from tkinter import scrolledtext
import queue
import os
import time
import openai
from p2 import AutomacaoP2

class SupervisorAgent:
    def __init__(self, automacao_cls, log_path='pje_automacao.log'):
        self.automacao_cls = automacao_cls
        self.log_path = log_path
        self.command_queue = queue.Queue()
        self.running = True
        self.last_log_pos = 0
        self.status = "inicializando"
        self.erros = []

    def monitor_logs(self):
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                f.seek(self.last_log_pos)
                while self.running:
                    line = f.readline()
                    if not line:
                        time.sleep(1)
                        continue
                    self.last_log_pos = f.tell()
                    self.process_log_line(line)
        except Exception as e:
            print(f'[Supervisor] Erro ao monitorar logs: {e}')

    def process_log_line(self, line):
        if 'ERRO' in line or 'Exception' in line:
            self.erros.append(line)
            print(f'[Supervisor] Erro detectado: {line.strip()}')
            self.status = "erro"
            self.handle_error(line)
        else:
            print(f'[Supervisor] Log: {line.strip()}')

    def handle_error(self, line):
        print('[Supervisor] Tentando recuperar...')
        try:
            if hasattr(self.automacao_cls, 'reiniciar_etapa'):
                self.automacao_cls.reiniciar_etapa()
                self.status = "recuperando"
        except Exception as e:
            print(f'[Supervisor] Falha ao tentar recuperar: {e}')

    def command_listener(self):
        while self.running:
            try:
                cmd = self.command_queue.get(timeout=1)
                self.execute_command(cmd)
            except queue.Empty:
                continue

    def execute_command(self, cmd):
        print(f'[Supervisor] Executando comando: {cmd}')
        if cmd == "pausar":
            self.running = False
        elif cmd == "retomar":
            self.running = True
        elif cmd == "reiniciar":
            if hasattr(self.automacao_cls, 'reiniciar_etapa'):
                self.automacao_cls.reiniciar_etapa()

    def start(self):
        threading.Thread(target=self.monitor_logs, daemon=True).start()
        threading.Thread(target=self.command_listener, daemon=True).start()
        sucesso = self.automacao_cls.executar_fluxo()
        if not sucesso:
            print("[Supervisor] Fluxo falhou, verifique logs.")
        else:
            print("[Supervisor] Fluxo concluído com sucesso.")

    def stop(self):
        self.running = False

class SupervisorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Supervisor PJe - GUI (Automação Selenium)")
        self.root.geometry("650x540")
        # Instruções iniciais
        self.instructions = tk.Label(root, text="Bem-vindo ao Supervisor PJe!\nDigite comandos abaixo ou clique nos botões. Exemplos: executar, pausar, retomar, status, erros, memoria, sair.", fg="blue", font=("Arial", 10, "bold"), justify="left")
        self.instructions.pack(padx=10, pady=(10,0), anchor="w")
        self.text_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, state='disabled', height=20)
        self.text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.entry = tk.Entry(root)
        self.entry.pack(padx=10, pady=(0,10), fill=tk.X)
        self.entry.bind('<Return>', self.send_command)
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=(0,10))
        self.send_btn = tk.Button(btn_frame, text="Enviar", command=self.send_command, width=10)
        self.send_btn.pack(side=tk.LEFT, padx=5)
        self.exit_btn = tk.Button(btn_frame, text="Sair", command=self.exit_app, width=10, fg="red")
        self.exit_btn.pack(side=tk.LEFT, padx=5)
        self.status_label = tk.Label(root, text="Status: inicializando", anchor='w', fg="darkgreen", font=("Arial", 10, "italic"))
        self.status_label.pack(fill=tk.X, padx=10, pady=(0,5))
        self.automacao = AutomacaoP2()
        self.supervisor = SupervisorAgent(self.automacao)
        self.running = True
        self.memory = []
        self.use_openai = bool(os.getenv("OPENAI_API_KEY"))
        threading.Thread(target=self.supervisor.start, daemon=True).start()
        threading.Thread(target=self.update_status, daemon=True).start()
        self.print_msg("[Supervisor GUI] Pronto para comandos. Digite 'ajuda' para opções.")
        if self.use_openai:
            self.print_msg("[Supervisor GUI] IA ativada (OpenAI API).")

    def exit_app(self):
        self.running = False
        self.root.quit()
        self.root.destroy()

    def print_msg(self, msg):
        self.text_area.config(state='normal')
        self.text_area.insert(tk.END, msg + '\n')
        self.text_area.see(tk.END)
        self.text_area.config(state='disabled')

    def send_command(self, event=None):
        cmd = self.entry.get().strip()
        if not cmd:
            return
        self.print_msg(f"[Você > ] {cmd}")
        self.entry.delete(0, tk.END)
        if cmd.lower() in ("sair", "exit", "quit"):
            self.running = False
            self.root.quit()
            return
        if self.use_openai:
            threading.Thread(target=self.handle_openai, args=(cmd,), daemon=True).start()
        else:
            threading.Thread(target=self.handle_command, args=(cmd,), daemon=True).start()

    def handle_command(self, cmd):
        # Comandos locais (sem IA)
        if cmd == "ajuda":
            self.print_msg("Comandos: executar, pausar, retomar, reiniciar, status, erros, memoria, sair")
        elif "executar" in cmd.lower():
            threading.Thread(target=self.automacao.executar_fluxo, daemon=True).start()
            self.print_msg("[Supervisor] Executando fluxo...")
        elif "pausar" in cmd.lower():
            self.supervisor.command_queue.put("pausar")
            self.print_msg("[Supervisor] Execução pausada.")
        elif "retomar" in cmd.lower():
            self.supervisor.command_queue.put("retomar")
            self.print_msg("[Supervisor] Execução retomada.")
        elif "reiniciar" in cmd.lower():
            self.supervisor.command_queue.put("reiniciar")
            self.print_msg("[Supervisor] Reiniciando etapa atual.")
        elif "status" in cmd.lower():
            self.print_msg(f"[Supervisor] Status: {self.supervisor.status}")
        elif "erros" in cmd.lower():
            self.print_msg("[Supervisor] Últimos erros:")
            for e in self.supervisor.erros[-5:]:
                self.print_msg(e.strip())
        elif "memoria" in cmd.lower():
            self.print_msg(f"[Supervisor] Memória de erros: {len(self.supervisor.erros)} erros registrados.")
        else:
            self.print_msg(f"[Supervisor] Comando não reconhecido: {cmd}")

    def handle_openai(self, cmd):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.print_msg("[Supervisor IA] OPENAI_API_KEY não encontrada no ambiente.")
            return
        client = openai.OpenAI(api_key=api_key)
        context = f"Status: {self.supervisor.status}\nÚltimos erros: {self.supervisor.erros[-3:]}\nComando: {cmd}\nMemória: {len(self.supervisor.erros)} erros."
        prompt = (
            "Você é um agente supervisor de automações Selenium para o PJe. "
            "Recebe comandos do usuário, monitora logs, aprende com execuções e sugere melhorias. "
            "Responda de forma útil, clara e, se possível, sugira ações para garantir robustez.\n"
            f"Contexto: {context}\n"
            "Responda ao comando do usuário e, se for um comando de automação (executar, pausar, reiniciar, analisar, etc), oriente ou execute a ação.\n"
            f"Usuário: {cmd}\nSupervisor:")
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": prompt}],
                max_tokens=256,
                temperature=0.2
            )
            reply = response.choices[0].message.content.strip()
        except Exception as e:
            reply = f"[Supervisor] Erro ao consultar OpenAI: {e}"
        self.print_msg(f"[Supervisor IA] {reply}")
        self.memory.append({"cmd": cmd, "reply": reply, "status": self.supervisor.status, "erros": list(self.supervisor.erros)})
        if "executar" in cmd.lower():
            threading.Thread(target=self.automacao.executar_fluxo, daemon=True).start()
        elif "pausar" in cmd.lower():
            self.supervisor.command_queue.put("pausar")
        elif "retomar" in cmd.lower():
            self.supervisor.command_queue.put("retomar")
        elif "reiniciar" in cmd.lower():
            self.supervisor.command_queue.put("reiniciar")
        elif "erros" in cmd.lower():
            self.print_msg("[Supervisor] Últimos erros:")
            for e in self.supervisor.erros[-5:]:
                self.print_msg(e.strip())
        elif "status" in cmd.lower():
            self.print_msg(f"[Supervisor] Status: {self.supervisor.status}")
        elif "memoria" in cmd.lower():
            self.print_msg(f"[Supervisor] Memória de erros: {len(self.supervisor.erros)} erros registrados.")

    def update_status(self):
        while self.running:
            status = self.supervisor.status
            self.status_label.config(text=f"Status: {status}")
            time.sleep(2)

if __name__ == "__main__":
    root = tk.Tk()
    app = SupervisorGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.exit_app)
    root.mainloop()
