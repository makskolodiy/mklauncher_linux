#!/usr/bin/env python3
import os
import uuid
import time
import threading
import subprocess
import tkinter as tk
import webbrowser
from tkinter import ttk, messagebox, scrolledtext
import shutil
from plyer import notification
from minecraft_launcher_lib.install import install_minecraft_version
from minecraft_launcher_lib.fabric import install_fabric
from minecraft_launcher_lib.quilt import install_quilt
from minecraft_launcher_lib.forge import install_forge_version
from minecraft_launcher_lib.command import get_minecraft_command
from minecraft_launcher_lib.utils import get_version_list
from tkinter import font
# ===================== PATHS =====================

HOME = os.path.expanduser("~")
LAUNCHER_DIR = os.path.join(HOME, ".mklauncher")
CONFIG_FILE = os.path.join(LAUNCHER_DIR, "config.txt")
LOG_FILE = os.path.join(LAUNCHER_DIR, "launcher.log")
INSTANCES_DIR = os.path.join(LAUNCHER_DIR, "instances")

os.makedirs(LAUNCHER_DIR, exist_ok=True)
os.makedirs(INSTANCES_DIR, exist_ok=True)

# ===================== LOG =====================

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

    if "app" in globals() and app:
        app.append_log(line)

# ===================== CONFIG =====================

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return "", str(uuid.uuid4())

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
            username = lines[0].strip() if len(lines) > 0 else ""
            uid = lines[1].strip() if len(lines) > 1 else str(uuid.uuid4())
            return username, uid
    except:
        return "", str(uuid.uuid4())

def save_config(username, uid):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write(f"{username}\n{uid}")

# ===================== MAIN APP =====================

class LauncherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.after(0, self.withdraw)  # Скрыть лаунчер
        self.title("MKLauncher (Linux) BETA-4")
        self.geometry("800x700")
        self.username, self.uuid = load_config()

        for name in (
            "TkDefaultFont",
            "TkTextFont",
            "TkFixedFont",
            "TkMenuFont",
            "TkHeadingFont",
            "TkCaptionFont",
            "TkSmallCaptionFont",
            "TkIconFont",
            "TkTooltipFont",
        ):
            try:
                font.nametofont(name).configure(family="MinecraftRus", size=9)
            except:
                messagebox.showerror("error","error loading font")
        if not self.uuid:
            self.uuid = str(uuid.uuid4())
            save_config(self.username, self.uuid)
        if messagebox.askquestion("support MKlauncher","If you enjoy using the launcher, you can visit the project's GitHub page and support its development.") == "yes":
            messagebox.showinfo("thank you","Thank you for supporting the development of MKLauncher! We truly appreciate your support. Feel free to share your ideas and suggestions for features you'd like to see added to the launcher.")
            webbrowser.open("https://github.com/makskolodiy/mklauncher_linux")
        self.after(0, self.deiconify)  # Показать лаунчер снова
        self.build_ui()

        log("Launcher started (Linux, OpenGL mode)")

        self.update_versions()

    # ================= UI =================

    def build_ui(self):
        # Nick
        f1 = tk.Frame(self)
        f1.pack(pady=10, padx=20, fill="x")

        tk.Label(f1, text="Nick:").pack(side="left")

        self.entry_nick = tk.Entry(f1, width=40)
        self.entry_nick.pack(side="left", padx=10)
        self.entry_nick.insert(0, self.username or "Player")

        tk.Button(f1, text="Save", command=self.save_nick).pack(side="left")

        # Version + Loader
        f2 = tk.Frame(self)
        f2.pack(pady=10, padx=20, fill="x")

        tk.Label(f2, text="Version:").pack(side="left")

        self.combo_ver = ttk.Combobox(f2, width=50)
        self.combo_ver.pack(side="left", padx=10)

        tk.Label(f2, text="Loader:").pack(side="left", padx=(20, 0))

        self.combo_loader = ttk.Combobox(
            f2,
            values=["vanilla", "fabric", "quilt", "forge", "neoforge"],
            state="readonly",
            width=20
        )
        self.combo_loader.set("vanilla")
        self.combo_loader.pack(side="left", padx=10)

        # Buttons
        f3 = tk.Frame(self)
        f3.pack(pady=10)

        tk.Button(f3, text="Refresh", command=self.update_versions).pack(side="left", padx=10)
        tk.Button(f3, text="Play", command=self.play, bg="#4CAF50", fg="white", width=12).pack(side="left", padx=10)
        tk.Button(f3, text="Reset", command=self.reset, bg="#d32f2f", fg="white").pack(side="left", padx=10)
        tk.Button(f3, text="Report a Bug", command=self.problem, bg="#d32f2f", fg="white").pack(side="left", padx=10)


        # Progress
        self.prog_var = tk.DoubleVar()
        self.prog = ttk.Progressbar(self, variable=self.prog_var, maximum=100)
        self.prog.pack(fill="x", padx=20, pady=10)

        # Log
        self.log_text = scrolledtext.ScrolledText(self, height=25)
        self.log_text.pack(fill="both", expand=True, padx=20, pady=10)

    def append_log(self, text):
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")

    # ================= ACTIONS =================

    def save_nick(self):
        save_config(self.entry_nick.get(), self.uuid)
        log("Nickname saved")

    def update_versions(self):
        try:
            vers = get_version_list()
            self.combo_ver["values"] = [v["id"] for v in vers]

            if vers:
                self.combo_ver.set(vers[-1]["id"])

            log(f"Loaded versions: {len(vers)}")

        except Exception as e:
            log(f"Version error: {e}")

    def play(self):
        nick = self.entry_nick.get().strip()
        ver = self.combo_ver.get().strip()
        loader = self.combo_loader.get().strip()

        if not nick or not ver:
            messagebox.showerror("Error", "Nick and version required")
            return

        threading.Thread(
            target=self._install_and_launch,
            args=(ver, loader, nick),
            daemon=True
        ).start()

    # ================= INSTALL + RUN =================

    def _install_and_launch(self, version, loader, username):
        dir_game = LAUNCHER_DIR if loader == "vanilla" else os.path.join(INSTANCES_DIR, f"{version}-{loader}")
        os.makedirs(dir_game, exist_ok=True)

        callback = {
            "setStatus": lambda s: self.after(0, lambda: self.append_log(s)),
            "setProgress": lambda p: self.after(0, lambda: self.prog_var.set(min(p, 100))),
            "setMax": lambda m: None
        }

        try:
            log("Installing Minecraft...")

            install_minecraft_version(version, dir_game, callback=callback)

            # Loaders
            if loader == "fabric":
                log("Installing Fabric...")
                install_fabric(version, dir_game, callback=callback)

            elif loader == "quilt":
                log("Installing Quilt...")
                install_quilt(version, dir_game, callback=callback)

            elif loader == "forge":
                log("Installing Forge...")
                install_forge_version(version, dir_game, callback=callback)

            # Launch
            options = {
                "username": username,
                "uuid": self.uuid,
                "token": "0"
            }
            notification.notify(
                title="MKlauncher",
                message="Minecraft installed (updated), launching minecraft...",
                timeout=8
            )
            log("Launching Minecraft...")
            self.after(0, self.withdraw)  # Скрыть лаунчер
            cmd = get_minecraft_command(version, dir_game, options)

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            for line in proc.stdout:
                self.after(0, lambda l=line.strip(): self.append_log(l))
            proc.wait()
            self.after(0, self.deiconify)  # Показать лаунчер снова

        except Exception as e:
            log(f"Error: {e}")
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

    # ================= RESET =================

    def reset(self):
        if messagebox.askyesno("Reset", "Delete all launcher data?"):
            shutil.rmtree(LAUNCHER_DIR, ignore_errors=True)
            os.makedirs(LAUNCHER_DIR, exist_ok=True)
            log("Launcher reset completed")
    def problem(self):
        webbrowser.open("https://github.com/makskolodiy/mklauncher_linux")
        notification.notify(
            title="MKlauncher, report of bug",
            message="Please report this bug on our GitHub page. Thank you for helping improve MKLauncher!",
            timeout=8
        )

# ================= RUN =================

if __name__ == "__main__":
    app = LauncherApp()
    app.mainloop()