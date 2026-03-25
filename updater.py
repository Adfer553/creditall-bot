"""
Módulo de auto-atualização — Creditall Bot PN
Verifica versão no GitHub e baixa o novo .exe se houver atualização.
"""
import os, sys, json, subprocess, threading
import urllib.request
import tkinter as tk
from tkinter import ttk

# ── URL do version.json no seu GitHub ──────────────────────────────────────
VERSION_URL = "https://raw.githubusercontent.com/Adfer553/creditall-bot/main/version.json"
VERSAO_ATUAL = "1.0.0"


def verificar_atualizacao(callback_ok, callback_nova_versao):
    """
    Verifica em background se há versão nova.
    callback_ok()             → chamado se está na versão mais recente
    callback_nova_versao(url) → chamado se há versão nova, recebe URL de download
    """
    def _checar():
        try:
            req = urllib.request.Request(VERSION_URL,
                headers={"User-Agent": "CreditallBot-Updater/1.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                dados = json.loads(r.read().decode())
            versao_nova = dados.get("versao", "0.0.0")
            if _versao_maior(versao_nova, VERSAO_ATUAL):
                url = dados.get("download_url", "")
                callback_nova_versao(versao_nova, url, dados.get("notas", ""))
            else:
                callback_ok()
        except Exception:
            callback_ok()   # Se não conseguir verificar, abre normalmente

    threading.Thread(target=_checar, daemon=True).start()


def _versao_maior(nova, atual):
    """Compara versões no formato X.Y.Z"""
    try:
        n = [int(x) for x in nova.split(".")]
        a = [int(x) for x in atual.split(".")]
        return n > a
    except Exception:
        return False


def baixar_e_instalar(url, versao, janela_pai):
    """Mostra janela de progresso, baixa o novo .exe e reinicia."""
    win = tk.Toplevel(janela_pai)
    win.title("Atualizando Creditall Bot")
    win.geometry("420x160")
    win.resizable(False, False)
    win.grab_set()
    win.configure(bg="#0d0d0d")

    tk.Label(win, text=f"  Baixando versão {versao}...",
             bg="#0d0d0d", fg="#f0f0f0",
             font=("Segoe UI", 11, "bold")).pack(pady=(18, 6), anchor="w", padx=20)

    lbl_pct = tk.Label(win, text="0%", bg="#0d0d0d", fg="#959595",
                       font=("Consolas", 9))
    lbl_pct.pack(anchor="w", padx=20)

    bar = ttk.Progressbar(win, length=380, mode="determinate")
    bar.pack(padx=20, pady=8)

    tk.Label(win, text="Não feche esta janela.", bg="#0d0d0d",
             fg="#555555", font=("Segoe UI", 8)).pack()

    def _download():
        try:
            exe_atual = sys.executable if getattr(sys, "frozen", False) else sys.argv[0]
            exe_novo  = exe_atual + ".novo"

            def _progresso(count, block, total):
                if total > 0:
                    pct = int(count * block * 100 / total)
                    pct = min(pct, 100)
                    win.after(0, lambda p=pct: (
                        bar.configure(value=p),
                        lbl_pct.configure(text=f"{p}%")
                    ))

            urllib.request.urlretrieve(url, exe_novo, reporthook=_progresso)

            # Script .bat que substitui o .exe e reinicia
            bat = exe_atual + "_update.bat"
            with open(bat, "w") as f:
                f.write(f'''@echo off
timeout /t 2 /nobreak >nul
move /y "{exe_novo}" "{exe_atual}"
start "" "{exe_atual}"
del "%~f0"
''')
            subprocess.Popen(bat, shell=True,
                             creationflags=subprocess.CREATE_NO_WINDOW)
            win.after(0, win.destroy)
            janela_pai.after(100, janela_pai.destroy)

        except Exception as e:
            win.after(0, lambda: (
                lbl_pct.configure(text=f"Erro: {e}", fg="#FF4560"),
                bar.configure(value=0)
            ))

    threading.Thread(target=_download, daemon=True).start()
