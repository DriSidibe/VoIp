import subprocess
import threading
import tkinter as tk

# ================= CONFIG =================
WINDOW_SIZE = "600x400"
REFRESH_MS = 1000         # log refresh interval (ms)
VENV_PYTHON = "..\env\Scripts\python.exe"

# ================= FONCTIONS =================

server_running = False
cli_process = None

def toggle_server():
    global server_running
    if not server_running:
        send_command("start")
        server_running = True
    else:
        send_command("stop")
        server_running = False


def send_command(command):
    if cli_process and cli_process.stdin:
        cli_process.stdin.write(command + "\n")
        cli_process.stdin.flush()

def add_log(message):
    log_text.config(state="normal")
    log_text.insert(tk.END, message + "\n")
    log_text.see(tk.END)
    log_text.config(state="disabled")


def read_cli_output():
    while True:
        line = cli_process.stdout.readline()
        if not line:
            break
        add_log(line.strip())


def start_cli():
    global cli_process

    cli_process = subprocess.Popen(
        [VENV_PYTHON, "../server_cli.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    threading.Thread(target=read_cli_output, daemon=True).start()

# ================= MAIN WINDOW =================
root = tk.Tk()
root.title("VoIP Server")
root.geometry(WINDOW_SIZE)

# ================= TOP BAR =================
command_frame = tk.Frame(root, bg="green", height=60)
command_frame.pack(side=tk.TOP, fill=tk.X)
command_frame.pack_propagate(False)

start_stop_button = tk.Button(
    command_frame,
    command=toggle_server,
    text="START / STOP",
    bg="red",
    fg="white",
    width=15
)
start_stop_button.pack(expand=True)

# ================= BOTTOM CONTAINER =================
bottom_frame = tk.Frame(root)
bottom_frame.pack(fill=tk.BOTH, expand=True)

# ================= CLIENTS PANEL =================
clients_frame = tk.Frame(bottom_frame, bg="blue", width=200)
clients_frame.pack(side=tk.LEFT, fill=tk.Y)
clients_frame.pack_propagate(False)

tk.Label(
    clients_frame,
    text="Clients",
    bg="blue",
    fg="white",
    font=("Arial", 10, "bold")
).pack(pady=5)

clients_listbox = tk.Listbox(clients_frame)
clients_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

clients_scroll = tk.Scrollbar(clients_listbox)
clients_scroll.pack(side=tk.RIGHT, fill=tk.Y)

clients_listbox.config(yscrollcommand=clients_scroll.set)
clients_scroll.config(command=clients_listbox.yview)

# Example clients (replace with real ones)
for c in ["Client 1", "Client 2", "Client 3"]:
    clients_listbox.insert(tk.END, c)

# ================= LOG PANEL =================
log_frame = tk.Frame(bottom_frame, bg="yellow")
log_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

tk.Label(
    log_frame,
    text="Logs",
    bg="yellow",
    fg="black",
    font=("Arial", 10, "bold")
).pack(pady=5)

log_text = tk.Text(log_frame, state="disabled")
log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

log_scroll = tk.Scrollbar(log_text)
log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

log_text.config(yscrollcommand=log_scroll.set)
log_scroll.config(command=log_text.yview)

start_cli()

# ================= START UI =================
root.mainloop()
