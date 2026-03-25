import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import pandas as pd
import random
import re
import os
import json
import sys

def resource_path(relative_path):
    """Encontra o caminho correto tanto no .py quanto no .exe."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# Garantir que bot_core e updater sejam encontrados no .exe
if hasattr(sys, '_MEIPASS'):
    sys.path.insert(0, sys._MEIPASS)
import bot_core_gemini_PN as bot_core
import updater
from PIL import Image, ImageTk
from bot_core_gemini_PN import (
    log, set_log_callback,
    identificar_layout,
    extrair_dados_inteligente,
    abrir_driver_whatsapp, configurar_gemini_inicial,
    abrir_chat, enviar_fragmentado, processar_spintax,
    pausa_seguranca_com_monitor, salvar_checkpoint,
    ler_checkpoint, resetar_checkpoint,
    marcar_manual, forcar_pulo_atual,
    parar_imediato, resetar_parar,
    PAUSA_MIN, PAUSA_MAX
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ══════════════════════════════════════════════════════
# IDENTIDADE VISUAL — CREDITALL
# Pantone 186C      → #E31937  (vermelho principal)
# Pantone Black 50% → #959595  (cinza)
# Pantone Black 90% → #414141  (cinza escuro)
# Fonte principal: Sansation (instale via fontsquirrel)
# ══════════════════════════════════════════════════════

TEMAS = {
    "escuro": {
        "BG":            "#0d0d0d",
        "BG_CARD":       "#181818",
        "BG_PANEL":      "#181818",
        "BG_HEADER":     "#0a0a0a",
        "BG_INPUT":      "#222222",
        "BG_STATUS":     "#141414",
        "BORDER":        "#3a3a3a",
        "COR_TEXTO":     "#f0f0f0",
        "COR_CINZA":     "#959595",
        "LOG_BG":        "#0d0d0d",
        "SEL_BG":        "#264f78",
        "COR_HDR_TEXTO": "#f0f0f0",   # mesmo que COR_TEXTO no modo escuro
        "COR_HDR_CINZA": "#959595",   # mesmo que COR_CINZA no modo escuro
    },
    "claro": {
        "BG":            "#e8eaed",   # cinza azulado — fundo geral
        "BG_CARD":       "#ffffff",   # branco — cards se destacam
        "BG_PANEL":      "#ffffff",   # branco — painéis se destacam
        "BG_HEADER":     "#1a1a2e",   # azul escuro — header com autoridade
        "BG_INPUT":      "#f1f3f4",   # cinza claro — inputs visíveis
        "BG_STATUS":     "#ffffff",   # branco — barra de status limpa
        "BORDER":        "#b0b8c1",   # cinza médio — bordas visíveis
        "COR_TEXTO":     "#1a1a2e",   # azul escuro — texto principal legível
        "COR_CINZA":     "#555e6b",   # cinza escuro — labels secundários
        "LOG_BG":        "#f8f9fa",   # quase branco — log limpo
        "SEL_BG":        "#b3d4fb",   # azul claro — seleção visível
        "COR_HDR_TEXTO": "#ffffff",   # branco — texto sobre header escuro
        "COR_HDR_CINZA": "#c0c8d8",   # cinza claro — subtítulo sobre header
    },
}

_TEMA_ATUAL = "escuro"

def _t(chave):
    return TEMAS[_TEMA_ATUAL][chave]

# Cores fixas (iguais nos dois temas — identidade Creditall)
COR_VERDE     = "#E31937"
COR_VERDE_BTN = "#A8102B"
COR_VERDE_HVR = "#C41330"
COR_AZUL      = "#E8E8E8"
COR_AMARELO   = "#d29922"
COR_ROXO      = "#bc8cff"
COR_VERMELHO  = "#FF4560"
COR_LARANJA   = "#e3b341"

# Aliases dinâmicos (apontam pro tema ativo)
BG            = _t("BG")
BG_CARD       = _t("BG_CARD")
BG_PANEL      = _t("BG_PANEL")
BG_HEADER     = _t("BG_HEADER")
BG_INPUT      = _t("BG_INPUT")
BG_STATUS     = _t("BG_STATUS")
BORDER        = _t("BORDER")
COR_TEXTO     = _t("COR_TEXTO")
COR_CINZA     = _t("COR_CINZA")

FONTE         = ("Sansation", 10)
FONTE_B       = ("Sansation", 10, "bold")
FONTE_MONO    = ("Consolas", 9)
FONTE_TITULO  = ("Sansation", 11, "bold")


TEMPLATES_FILE = os.path.join("data", "templates_PN.txt")
os.makedirs("data", exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════
# DIALOGO: MAPEAMENTO DE COLUNAS  (entrada de texto livre)
# ═══════════════════════════════════════════════════════════════════════
class DialogColunas(ctk.CTkToplevel):
    def __init__(self, master, colunas: list):
        super().__init__(master)
        self.title("Configurar Campos")
        self.geometry("420x300")
        self.resizable(False, False)
        self.configure(fg_color=BG_PANEL)
        self.grab_set()
        self.lift()
        self.focus_force()
        self.colunas   = colunas
        self.resultado = None
        ctk.CTkLabel(self, text="Identificar Colunas da Planilha",
                     font=FONTE_TITULO, text_color=COR_TEXTO).pack(pady=(18, 4))
        ctk.CTkLabel(self, text="Digite o nome exato como aparece no cabecalho do arquivo.",
                     font=("Segoe UI", 9), text_color=COR_CINZA).pack(pady=(0, 12))
        frm = ctk.CTkFrame(self, fg_color="transparent")
        frm.pack(fill="x", padx=24)
        frm.columnconfigure(1, weight=1)
        def linha(row, texto, cor, placeholder):
            ctk.CTkLabel(frm, text=texto, font=FONTE_B,
                         text_color=cor, anchor="w").grid(row=row, column=0, sticky="w", pady=7)
            e = ctk.CTkEntry(frm, placeholder_text=placeholder,
                             fg_color=BG_INPUT, border_color=BORDER,
                             text_color=COR_TEXTO, font=FONTE, height=30)
            e.grid(row=row, column=1, sticky="ew", padx=(10, 0), pady=7)
            return e
        self.e_empresa = linha(0, "Nome da empresa / CNPJ  *", COR_AMARELO, "Ex: Razao Social")
        self.e_tel     = linha(1, "Telefone para WhatsApp  *", COR_VERDE,   "Ex: SOCIO1Celular1")
        self.e_nome    = linha(2, "Nome do socio (opcional)", COR_AZUL,    "Ex: SOCIO1Nome")
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=24, pady=(12, 0))
        btns.columnconfigure((0, 1), weight=1)
        ctk.CTkButton(btns, text="Seguir sem nome",
                      fg_color=BG_INPUT, hover_color="#30363d",
                      border_color=BORDER, border_width=1,
                      text_color=COR_CINZA, font=FONTE,
                      command=self._sem_nome).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(btns, text="Confirmar e Iniciar",
                      fg_color=COR_VERDE_BTN, hover_color=COR_VERDE_HVR,
                      font=FONTE_B,
                      command=self._confirmar).grid(row=0, column=1, sticky="ew")

    def _sem_nome(self):
        self.e_nome.delete(0, "end")
        self._confirmar(ignorar_nome=True)

    def _confirmar(self, ignorar_nome=False):
        empresa = self.e_empresa.get().strip()
        tel     = self.e_tel.get().strip()
        nome    = "" if ignorar_nome else self.e_nome.get().strip()
        if not empresa:
            messagebox.showwarning("Atencao", "Informe o campo da Empresa/CNPJ!", parent=self)
            return
        if not tel:
            messagebox.showwarning("Atencao", "Informe o campo do Telefone!", parent=self)
            return
        erros = []
        if empresa not in self.colunas:
            erros.append("Empresa: [" + empresa + "] nao encontrado. Verifique o nome exato.")
        if tel not in self.colunas:
            erros.append("Telefone: [" + tel + "] nao encontrado. Verifique o nome exato.")
        if nome and nome not in self.colunas:
            erros.append("Socio: [" + nome + "] nao encontrado. Verifique o nome exato.")
        if erros:
            msg_err = chr(10).join(erros) + chr(10) + chr(10) + "Copie o nome exato do cabecalho da planilha."
            messagebox.showerror("Campo invalido", msg_err, parent=self)
            return
        self.resultado = {
            "col_nome":    nome or None,
            "col_empresa": empresa,
            "col_tel_pri": tel,
            "col_tel_sec": None,
        }
        self.destroy()



# ═══════════════════════════════════════════════════════════════════════
# APP PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════
class CreditallBotPN(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CREDITALL BOT PN")
        self.geometry("1100x700")
        self.minsize(960, 640)
        self.configure(fg_color=BG)
        self.caminho_leads   = ""
        self.mapa_colunas    = None
        self.df_leads        = None
        self.rodando         = False
        self.driver_whats    = None
        self.total_leads     = 0
        self.leads_em_manual = set()
        self._templates      = []
        self._tab_ativa      = 0
        # ── Status inteligente por base ────────────────────────────────
        self.status_leads    = {}   # {telefone: "enviado"|"falha"|"pulado"}
        self.arquivo_status  = ""   # caminho do JSON de status desta base
        self._theme_reg      = []   # registro de widgets para troca de tema
        set_log_callback(self._log_gui)
        self._build_ui()
        self._carregar_templates_salvos()
        self._log("INFO", "Sistema inicializado - CREDITALL BOT PN")
        # ── Verificar atualizações em background ───────────────────────
        self.after(2000, self._checar_atualizacao)

    # ─── BUILD UI ────────────────────────────────────────────────────────
    def _build_ui(self):
        hdr = tk.Frame(self, bg=BG_HEADER, height=50)
        hdr.pack(fill="x", side="top")
        hdr.pack_propagate(False)
        self._R(hdr, bg="BG_HEADER")
        tk.Frame(hdr, bg=COR_VERDE, width=3).pack(side="left", fill="y")
        self._R(tk.Label(hdr, text="  CREDITALL BOT", bg=BG_HEADER, fg=COR_TEXTO,
                 font=("Segoe UI", 13, "bold")), bg="BG_HEADER", fg="COR_HDR_TEXTO").pack(side="left", padx=(10,0))
        tk.Label(hdr, text=" PN ", bg="#E31937", fg="white",
                 font=("Segoe UI", 8, "bold"), padx=4, pady=1).pack(side="left", padx=6, pady=16)
        self._R(tk.Label(hdr, text="Modo Humano Fragmentado", bg=BG_HEADER, fg=COR_CINZA,
                 font=FONTE_MONO), bg="BG_HEADER", fg="COR_HDR_CINZA").pack(side="left")
        # ── Botão toggle Escuro / Claro ────────────────────────────────
        self.btn_tema = ctk.CTkButton(hdr, text="🌙 Escuro", width=90, height=28,
            fg_color=BG_INPUT, hover_color=BORDER,
            text_color=COR_CINZA, font=("Sansation", 8),
            command=self._toggle_tema)
        self._R(self.btn_tema, fg_color="BG_HEADER", hover_color="BG_INPUT", text_color="COR_HDR_CINZA")
        self.btn_tema.pack(side="left", padx=(14, 0), pady=11)
        self.btn_iniciar = ctk.CTkButton(hdr, text="Iniciar Bot", width=130, height=32,
            fg_color=COR_VERDE_BTN, hover_color=COR_VERDE_HVR, font=FONTE_B, command=self._iniciar)
        self.btn_iniciar.pack(side="right", padx=14, pady=9)
        self.btn_parar = ctk.CTkButton(hdr, text="PARAR TUDO", width=110, height=32,
            fg_color="#5a1d1d", hover_color="#7a2020",
            border_color=COR_VERMELHO, border_width=1,
            text_color=COR_VERMELHO, font=FONTE_B, state="disabled", command=self._parar)
        self.btn_parar.pack(side="right", padx=4, pady=9)
        self.btn_pular = ctk.CTkButton(hdr, text="Pular", width=60, height=32,
            fg_color=BG_INPUT, hover_color="#30363d",
            text_color=COR_LARANJA, font=FONTE_B, state="disabled", command=self._pular)
        self._R(self.btn_pular, fg_color="BG_INPUT")
        self.btn_pular.pack(side="right", padx=2, pady=9)

        sbar = tk.Frame(self, bg=BG_STATUS, height=28)
        sbar.pack(fill="x")
        sbar.pack_propagate(False)
        self._R(sbar, bg="BG_STATUS")
        tk.Frame(sbar, bg=COR_AMARELO, width=3).pack(side="left", fill="y")
        self.lbl_status = tk.Label(sbar, text="  Aguardando",
                                    bg=BG_STATUS, fg=COR_AMARELO, font=("Segoe UI", 9, "bold"))
        self._R(self.lbl_status, bg="BG_STATUS")  # só bg — fg amarelo é fixo
        self.lbl_status.pack(side="left", padx=6)
        self.lbl_prog_pct = tk.Label(sbar, text="0/0  (0%)", bg=BG_STATUS, fg=COR_CINZA, font=FONTE_MONO)
        self._R(self.lbl_prog_pct, bg="BG_STATUS", fg="COR_CINZA")
        self.lbl_prog_pct.pack(side="right", padx=14)
        self.progressbar = ctk.CTkProgressBar(sbar, height=4, fg_color=_t("BG_INPUT"), progress_color=COR_VERDE)
        self._R(self.progressbar, fg_color="BG_INPUT")
        self.progressbar.set(0)
        self.progressbar.pack(side="right", fill="x", expand=True, padx=14, pady=6)

        cards = tk.Frame(self, bg=BG, pady=10)
        self._R(cards, bg="BG")
        cards.pack(fill="x", padx=14)
        self.cv_total    = self._card(cards, "TOTAL LEADS", "0", COR_AZUL)
        self.cv_enviados = self._card(cards, "ENVIADOS",    "0", COR_VERDE)
        self.cv_falhas   = self._card(cards, "FALHAS",      "0", COR_VERMELHO)
        self.cv_pend     = self._card(cards, "PENDENTES",   "0", COR_AMARELO)

        corpo = tk.Frame(self, bg=BG)
        self._R(corpo, bg="BG")
        corpo.pack(fill="both", expand=True, padx=14, pady=(0,10))
        corpo.columnconfigure(0, weight=3)
        corpo.columnconfigure(1, weight=2)
        corpo.rowconfigure(0, weight=1)
        esq = tk.Frame(corpo, bg=BG)
        self._R(esq, bg="BG")
        esq.grid(row=0, column=0, sticky="nsew", padx=(0,6))
        esq.rowconfigure(1, weight=1)
        esq.columnconfigure(0, weight=1)
        self._build_leads(esq)
        self._build_templates(esq)
        dir_ = tk.Frame(corpo, bg=BG)
        self._R(dir_, bg="BG")
        dir_.grid(row=0, column=1, sticky="nsew")
        dir_.rowconfigure(1, weight=1)
        dir_.columnconfigure(0, weight=1)
        self._build_configs(dir_)
        self._build_log(dir_)

    # ─── LEADS ───────────────────────────────────────────────────────────
    def _build_leads(self, parent):
        frame = self._painel(parent, "LEADS", badge="0")
        self.lbl_leads_badge = frame._badge
        inner = tk.Frame(frame, bg=BG_PANEL)
        self._R(inner, bg="BG_PANEL")
        inner.pack(fill="x", padx=10, pady=6)
        self.lbl_leads_file = tk.Label(inner,
            text="Importe sua base de leads\nSuporta CSV, TXT e Excel (.xlsx/.xls)\nVoce vai informar qual campo e Nome, Empresa e Telefone",
            bg=BG_PANEL, fg=COR_CINZA, font=FONTE_MONO, justify="center")
        self._R(self.lbl_leads_file, bg="BG_PANEL", fg="COR_CINZA")
        self.lbl_leads_file.pack(pady=10)
        self._R(
            ctk.CTkButton(inner, text="Importar CSV/Excel", height=30,
                      fg_color=BG_INPUT, hover_color="#30363d",
                      border_color=BORDER, border_width=1,
                      text_color=COR_TEXTO, font=FONTE_B,
                      command=self._importar_leads),
            fg_color="BG_INPUT", border_color="BORDER", text_color="COR_TEXTO"
        ).pack(fill="x")
        frame.grid(row=0, column=0, sticky="ew", pady=(0,6))

    # ─── TEMPLATES ───────────────────────────────────────────────────────
    def _build_templates(self, parent):
        frame = self._painel(parent, "TEMPLATES DE MENSAGEM")
        self._R(tk.Label(frame, text="  Use {nome}, {empresa}, {vendedor}. Separe frases com |",
                 bg=BG_PANEL, fg=COR_CINZA, font=("Segoe UI", 8), anchor="w"), bg="BG_PANEL", fg="COR_CINZA").pack(fill="x", padx=8, pady=(0,4))
        self.tpl_tabs_frame = tk.Frame(frame, bg=BG_PANEL)
        self._R(self.tpl_tabs_frame, bg="BG_PANEL")
        self.tpl_tabs_frame.pack(fill="x", padx=8)
        ctk.CTkButton(frame, text="+ Adicionar", height=24, width=90,
                      fg_color=COR_VERDE_BTN, hover_color=COR_VERDE_HVR,
                      font=("Segoe UI", 8, "bold"),
                      command=self._add_template).pack(anchor="e", padx=8, pady=2)
        self.tpl_text = tk.Text(frame, bg=_t("LOG_BG"), fg=COR_TEXTO,
                                font=FONTE_MONO, height=4, relief="flat",
                                padx=8, pady=6, wrap="word",
                                insertbackground=COR_TEXTO, selectbackground=_t("SEL_BG"))
        self._R(self.tpl_text, bg="LOG_BG", fg="COR_TEXTO",
                insertbackground="COR_TEXTO", selectbackground="SEL_BG")
        self.tpl_text.pack(fill="x", padx=8, pady=4)
        self.tpl_text.bind("<KeyRelease>", self._on_template_edit)
        self._R(tk.Label(frame, text="Preview:", bg=BG_PANEL, fg=COR_CINZA,
                 font=("Segoe UI", 8), anchor="w"), bg="BG_PANEL", fg="COR_CINZA").pack(fill="x", padx=8)
        self.prev_frame = tk.Frame(frame, bg=BG_PANEL)
        self._R(self.prev_frame, bg="BG_PANEL")
        self.prev_frame.pack(fill="x", padx=8, pady=(2,8))
        frame.grid(row=1, column=0, sticky="nsew")

    # ─── CONFIGS ─────────────────────────────────────────────────────────
    def _build_configs(self, parent):
        frame = self._painel(parent, "CONFIGURACOES")
        grid = tk.Frame(frame, bg=BG_PANEL)
        self._R(grid, bg="BG_PANEL")
        grid.pack(fill="x", padx=10, pady=6)
        grid.columnconfigure(1, weight=1)
        self._R(tk.Label(grid, text="Nome do Vendedor", bg=BG_PANEL,
                 fg=COR_CINZA, font=FONTE), bg="BG_PANEL", fg="COR_CINZA").grid(row=0, column=0, sticky="w", pady=4)
        self.entry_vendedor = ctk.CTkEntry(grid, placeholder_text="Seu nome...",
                                            fg_color=BG_INPUT, border_color=BORDER,
                                            text_color=COR_TEXTO, font=FONTE, height=28)
        self._R(self.entry_vendedor, fg_color="BG_INPUT", border_color="BORDER", text_color="COR_TEXTO")
        self.entry_vendedor.grid(row=0, column=1, sticky="ew", padx=(8,0), pady=4)
        self._R(tk.Label(grid, text="Link Gemini", bg=BG_PANEL,
                 fg=COR_CINZA, font=FONTE), bg="BG_PANEL", fg="COR_CINZA").grid(row=1, column=0, sticky="w", pady=4)
        self.entry_gemini = ctk.CTkEntry(grid, placeholder_text="https://gemini.google.com/app/...",
                                          fg_color=BG_INPUT, border_color=BORDER,
                                          text_color=COR_TEXTO, font=FONTE, height=28)
        self._R(self.entry_gemini, fg_color="BG_INPUT", border_color="BORDER", text_color="COR_TEXTO")
        self.entry_gemini.grid(row=1, column=1, sticky="ew", padx=(8,0), pady=4)
        pausas = tk.Frame(grid, bg=BG_PANEL)
        self._R(pausas, bg="BG_PANEL")
        pausas.grid(row=2, column=0, columnspan=2, sticky="ew", pady=6)
        pausas.columnconfigure((1,3), weight=1)
        def _campo(p, label, default, row, col):
            self._R(tk.Label(p, text=label, bg=BG_PANEL, fg=COR_CINZA,
                     font=("Segoe UI", 8)), bg="BG_PANEL", fg="COR_CINZA").grid(row=row, column=col, sticky="w")
            e = ctk.CTkEntry(p, width=70, fg_color=BG_INPUT, border_color=BORDER,
                             text_color=COR_TEXTO, font=FONTE, height=28)
            self._R(e, fg_color="BG_INPUT", border_color="BORDER", text_color="COR_TEXTO")
            e.insert(0, default)
            e.grid(row=row, column=col+1, padx=(4,12))
            return e
        self.e_pmin = _campo(pausas, "Pausa Min (s)",  "600",  0, 0)
        self.e_pmax = _campo(pausas, "Pausa Max (s)", "1020",  0, 2)
        self.e_dmin = _campo(pausas, "Digit Min",     "0.04",  1, 0)
        self.e_dmax = _campo(pausas, "Digit Max",     "0.12",  1, 2)
        self._R(tk.Label(grid, text="Assumir Manual", bg=BG_PANEL,
                 fg=COR_CINZA, font=FONTE), bg="BG_PANEL", fg="COR_CINZA").grid(row=3, column=0, sticky="w", pady=4)
        sub = tk.Frame(grid, bg=BG_PANEL)
        self._R(sub, bg="BG_PANEL")
        sub.grid(row=3, column=1, sticky="ew", padx=(8,0))
        sub.columnconfigure(0, weight=1)
        self.entry_manual = ctk.CTkEntry(sub, placeholder_text="Ex: 44999887766",
                                          fg_color=BG_INPUT, border_color=BORDER,
                                          text_color=COR_TEXTO, font=FONTE, height=28)
        self._R(self.entry_manual, fg_color="BG_INPUT", border_color="BORDER", text_color="COR_TEXTO")
        self.entry_manual.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(sub, text="OK", width=32, height=28,
                      fg_color=BG_INPUT, hover_color="#30363d",
                      text_color=COR_LARANJA, font=FONTE_B,
                      command=self._assumir_manual).grid(row=0, column=1, padx=(4,0))
        self._R(
            ctk.CTkButton(frame, text="Resetar Checkpoint",
                      height=26, fg_color=BG_INPUT, hover_color="#30363d",
                      border_color=BORDER, border_width=1,
                      text_color=COR_CINZA, font=("Segoe UI", 8),
                      command=self._resetar_ckpt),
            fg_color="BG_INPUT", border_color="BORDER", text_color="COR_CINZA"
        ).pack(fill="x", padx=10, pady=(0,8))
        frame.grid(row=0, column=0, sticky="ew", pady=(0,6))

    # ─── LOG ─────────────────────────────────────────────────────────────
    def _build_log(self, parent):
        frame = self._painel(parent, "LOG DE ATIVIDADE")
        self.log_box = tk.Text(frame, bg=_t("LOG_BG"), fg=COR_TEXTO,
                               font=FONTE_MONO, state="disabled",
                               relief="flat", padx=8, pady=6, wrap="word",
                               insertbackground=COR_TEXTO, selectbackground=_t("SEL_BG"))
        self._R(self.log_box, bg="LOG_BG", fg="COR_TEXTO",
                insertbackground="COR_TEXTO", selectbackground="SEL_BG")
        self.log_box.pack(fill="both", expand=True, padx=8, pady=(0,4))
        for tag, cor in [("OK",COR_VERDE),("ERRO",COR_VERMELHO),("AVISO",COR_AMARELO),
                          ("INFO",COR_AZUL),("DEBUG",COR_CINZA),("GPT",COR_ROXO),("MONITOR","#c586c0")]:
            self.log_box.tag_config(tag, foreground=cor)
        self._R(
            ctk.CTkButton(frame, text="Limpar log", height=22,
                      fg_color=BG_INPUT, hover_color="#30363d",
                      text_color=COR_CINZA, font=("Segoe UI", 8),
                      command=self._limpar_log),
            fg_color="BG_INPUT", text_color="COR_CINZA"
        ).pack(anchor="e", padx=8, pady=(0,6))
        frame.grid(row=1, column=0, sticky="nsew")

    # ─── HELPERS ─────────────────────────────────────────────────────────
    def _painel(self, parent, titulo, badge=None):
        outer = ctk.CTkFrame(parent, fg_color=BG_PANEL,
                              border_color=BORDER, border_width=1, corner_radius=6)
        self._R(outer, fg_color="BG_PANEL", border_color="BORDER")
        outer.columnconfigure(0, weight=1)
        hdr = tk.Frame(outer, bg=BG_PANEL)
        self._R(hdr, bg="BG_PANEL")
        hdr.pack(fill="x", padx=10, pady=(8,4))
        self._R(tk.Label(hdr, text=titulo, bg=BG_PANEL, fg=COR_TEXTO, font=FONTE_B),
                bg="BG_PANEL", fg="COR_TEXTO").pack(side="left")
        if badge is not None:
            b = tk.Label(hdr, text=f" {badge} ", bg=_t("BG_INPUT"), fg=COR_CINZA,
                         font=("Segoe UI", 8), padx=4)
            self._R(b, bg="BG_INPUT", fg="COR_CINZA")
            b.pack(side="left", padx=6)
            outer._badge = b
        else:
            outer._badge = None
        sep = tk.Frame(outer, bg=BORDER, height=1)
        self._R(sep, bg="BORDER")
        sep.pack(fill="x", padx=10, pady=(0,4))
        return outer

    def _card(self, parent, titulo, valor, cor):
        f = tk.Frame(parent, bg=BG_CARD, relief="flat",
                     highlightbackground=BORDER, highlightthickness=1)
        self._R(f, bg="BG_CARD")
        f.pack(side="left", expand=True, fill="both", padx=4)
        tk.Frame(f, bg=cor, height=2).pack(fill="x")
        lbl = tk.Label(f, text=valor, bg=BG_CARD, fg=cor, font=("Consolas", 24, "bold"))
        self._R(lbl, bg="BG_CARD")
        lbl.pack(pady=(10,2))
        self._R(tk.Label(f, text=titulo, bg=BG_CARD, fg=COR_CINZA,
                font=("Segoe UI", 7)), bg="BG_CARD", fg="COR_CINZA").pack(pady=(0,8))
        return lbl

    # ─── TEMPLATES ───────────────────────────────────────────────────────
    def _carregar_templates_salvos(self):
        if os.path.exists(TEMPLATES_FILE):
            try:
                with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
                    blocos = [b.strip() for b in f.read().split("---") if b.strip()]
                self._templates = blocos if blocos else [""]
            except Exception:
                self._templates = [""]
        else:
            self._templates = [""]
        self._rebuild_tabs()
        self._mostrar_tab(0)

    def _salvar_templates(self):
        os.makedirs("data", exist_ok=True)
        conteudo = "\n---\n".join(t for t in self._templates if t.strip())
        with open(TEMPLATES_FILE, "w", encoding="utf-8") as f:
            f.write(conteudo)

    def _rebuild_tabs(self):
        for widget in self.tpl_tabs_frame.winfo_children():
            widget.destroy()
        for i in range(len(self._templates)):
            ativo = (i == self._tab_ativa)
            # ── Container de cada aba ──────────────────────────────────
            grp = tk.Frame(self.tpl_tabs_frame, bg=BG_PANEL)
            self._R(grp, bg="BG_PANEL")
            grp.pack(side="left", padx=2)
            ctk.CTkButton(grp, text=f"Msg #{i+1}", width=55, height=24,
                fg_color=COR_VERDE if ativo else BG_INPUT, hover_color="#30363d",
                font=("Sansation", 8, "bold"),
                text_color=COR_TEXTO if ativo else COR_CINZA,
                command=lambda idx=i: self._mostrar_tab(idx)).pack(side="left")
            # ── Botão X para deletar ───────────────────────────────────
            if len(self._templates) > 1:
                ctk.CTkButton(grp, text="✕", width=18, height=24,
                    fg_color=BG_INPUT, hover_color="#5a1d1d",
                    text_color=COR_CINZA, font=("Segoe UI", 8),
                    command=lambda idx=i: self._deletar_template(idx)).pack(side="left", padx=(1, 0))

    def _mostrar_tab(self, idx):
        if 0 <= self._tab_ativa < len(self._templates):
            self._templates[self._tab_ativa] = self.tpl_text.get("1.0", "end-1c")
        self._tab_ativa = idx
        self.tpl_text.delete("1.0", "end")
        if idx < len(self._templates):
            self.tpl_text.insert("1.0", self._templates[idx])
        self._rebuild_tabs()
        self._atualizar_preview()

    def _add_template(self):
        if 0 <= self._tab_ativa < len(self._templates):
            self._templates[self._tab_ativa] = self.tpl_text.get("1.0", "end-1c")
        self._templates.append("")
        self._mostrar_tab(len(self._templates) - 1)

    def _deletar_template(self, idx):
        if len(self._templates) <= 1:
            return  # nunca deixar sem nenhum template
        if 0 <= self._tab_ativa < len(self._templates):
            self._templates[self._tab_ativa] = self.tpl_text.get("1.0", "end-1c")
        self._templates.pop(idx)
        nova_aba = max(0, idx - 1)
        self._tab_ativa = nova_aba
        self._rebuild_tabs()
        self._mostrar_tab(self._tab_ativa)
        self._salvar_templates()
        self._log("INFO", f"Template Msg #{idx+1} removido.")

    def _on_template_edit(self, _=None):
        if 0 <= self._tab_ativa < len(self._templates):
            self._templates[self._tab_ativa] = self.tpl_text.get("1.0", "end-1c")
        self._salvar_templates()
        self._atualizar_preview()

    def _atualizar_preview(self):
        for widget in self.prev_frame.winfo_children():
            widget.destroy()
        texto = (self.tpl_text.get("1.0", "end-1c")
                 .replace("{nome}", "Joao")
                 .replace("{empresa}", "Empresa X")
                 .replace("{vendedor}", "Carlos"))
        for frase in texto.split("|"):
            f = frase.strip()
            if f:
                tk.Label(self.prev_frame, text=f, bg="#E31937", fg="white",
                         font=("Segoe UI", 8), padx=8, pady=3).pack(side="left", padx=3, pady=2)

    # ─── IMPORTAR LEADS ──────────────────────────────────────────────────
    def _importar_leads(self):
        p = filedialog.askopenfilename(title="Selecionar planilha",
                                       filetypes=[("Dados", "*.xlsx *.xls *.csv")])
        if not p:
            return
        try:
            df = pd.read_csv(p, encoding="utf-8", dtype=str) if p.lower().endswith(".csv") else pd.read_excel(p, dtype=str)
        except Exception as e:
            messagebox.showerror("Erro", f"Nao foi possivel abrir:\n{e}")
            return
        dlg = DialogColunas(self, list(df.columns))
        self.wait_window(dlg)
        if dlg.resultado is None:
            return
        self.caminho_leads = p
        self.mapa_colunas  = dlg.resultado
        self.df_leads      = df
        self.total_leads   = len(df)
        # ── Checkpoint e status próprios por arquivo ───────────────────
        nome_base = os.path.splitext(os.path.basename(p))[0]
        bot_core.ARQUIVO_CHECKPOINT = os.path.join("data", f"ckpt_{nome_base}.txt")
        self.arquivo_status = os.path.join("data", f"status_{nome_base}.json")
        # ── Carregar histórico de disparos desta base ──────────────────
        self._carregar_status()
        env  = sum(1 for v in self.status_leads.values() if v == "enviado")
        falh = sum(1 for v in self.status_leads.values() if v == "falha")
        pul  = sum(1 for v in self.status_leads.values() if v == "pulado")
        pend = self.total_leads - env - falh - pul
        nome_arq = os.path.basename(p)
        self.lbl_leads_file.config(
            text=(f"{nome_arq}  -  {self.total_leads} leads\n"
                  f"Empresa: {self.mapa_colunas['col_empresa']}  "
                  f"Tel: {self.mapa_colunas['col_tel_pri']}  "
                  f"Nome: {self.mapa_colunas['col_nome'] or '(sem nome)'}"),
            fg=COR_VERDE)
        self.cv_total.config(text=str(self.total_leads))
        self.cv_enviados.config(text=str(env))
        self.cv_falhas.config(text=str(falh))
        self.cv_pend.config(text=str(pend))
        if self.lbl_leads_badge:
            self.lbl_leads_badge.config(text=f" {self.total_leads} ")
        self._log("OK",   f"Planilha: {nome_arq} - {self.total_leads} leads")
        self._log("INFO", f"Empresa={self.mapa_colunas['col_empresa']} | Tel={self.mapa_colunas['col_tel_pri']} | Nome={self.mapa_colunas['col_nome']}")
        if env or falh or pul:
            self._log("INFO", f"Historico carregado — Enviados: {env} | Falhas: {falh} | Pulados: {pul} | Pendentes: {pend}")

    # ─── LOG ─────────────────────────────────────────────────────────────
    def _log(self, nivel, msg):
        simb = {"OK":"OK","ERRO":"ERRO","AVISO":"AVISO","INFO":"INFO",
                "DEBUG":"DEBUG","GPT":"GPT","MONITOR":"MON"}
        ts    = time.strftime("%H:%M:%S")
        linha = f" {ts}  [{simb.get(nivel, nivel)}] {msg}\n"
        self.after(0, self._inserir_log, nivel, linha)

    def _log_gui(self, nivel, msg):
        self._log(nivel, msg)

    def _inserir_log(self, nivel, linha):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", linha, nivel)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _limpar_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    # ─── CONTROLES ───────────────────────────────────────────────────────
    def _resetar_ckpt(self):
        resetar_checkpoint()
        self._log("INFO", "Checkpoint resetado.")

    # ─── STATUS INTELIGENTE ──────────────────────────────────────────────────
    def _carregar_status(self):
        """Lê o JSON de status da base atual do disco."""
        self.status_leads = {}
        if self.arquivo_status and os.path.exists(self.arquivo_status):
            try:
                with open(self.arquivo_status, "r", encoding="utf-8") as f:
                    self.status_leads = json.load(f)
            except Exception:
                self.status_leads = {}

    def _salvar_status_lead(self, telefone, status):
        """Grava status de um lead no JSON e atualiza cards da UI."""
        if not telefone:
            return
        self.status_leads[telefone] = status
        if self.arquivo_status:
            os.makedirs("data", exist_ok=True)
            try:
                with open(self.arquivo_status, "w", encoding="utf-8") as f:
                    json.dump(self.status_leads, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        # ── Recalcular e atualizar cards ──────────────────────────────
        env  = sum(1 for v in self.status_leads.values() if v == "enviado")
        falh = sum(1 for v in self.status_leads.values() if v == "falha")
        pul  = sum(1 for v in self.status_leads.values() if v == "pulado")
        pend = max(0, self.total_leads - env - falh - pul)
        self.after(0, lambda e=env, f=falh, p=pend: (
            self.cv_enviados.config(text=str(e)),
            self.cv_falhas.config(text=str(f)),
            self.cv_pend.config(text=str(p))
        ))

    def _parar(self):
        self._log("AVISO", "PARANDO TUDO agora...")
        self.rodando = False
        parar_imediato()
        forcar_pulo_atual()
        import subprocess
        subprocess.Popen("taskkill /f /im chromedriver.exe /t",
                         shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.Popen("taskkill /f /im chrome.exe /t",
                         shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.btn_parar.configure(state="disabled")
        self.btn_pular.configure(state="disabled")
        self.btn_iniciar.configure(state="normal")
        self.lbl_status.config(text="  Parado — pronto para reiniciar", fg=COR_AMARELO)
        self.driver_whats = None
        self._log("AVISO", "Parado. Checkpoint salvo — retome sem perder leads.")

    def _pular(self):
        self._log("AVISO", "Pulando lead atual...")
        forcar_pulo_atual()

    def _assumir_manual(self):
        num = self.entry_manual.get().strip()
        if num:
            self.leads_em_manual.add(num)
            marcar_manual(num)
            self._log("AVISO", f"Numero {num} assumido manualmente.")
            self.entry_manual.delete(0, "end")

    # ─── INICIAR ─────────────────────────────────────────────────────────
    def _iniciar(self):
        vendedor    = self.entry_vendedor.get().strip()
        gemini_link = self.entry_gemini.get().strip()
        if not vendedor:
            messagebox.showwarning("Atencao", "Informe o nome do vendedor.")
            return
        if self.df_leads is None or self.mapa_colunas is None:
            messagebox.showwarning("Atencao", "Importe a planilha de leads primeiro.")
            return
        self._templates[self._tab_ativa] = self.tpl_text.get("1.0", "end-1c")
        self._salvar_templates()
        pool = [t for t in self._templates if t.strip()]
        if not pool:
            messagebox.showwarning("Atencao", "Adicione pelo menos um template.")
            return
        try:
            bot_core.PAUSA_MIN     = int(float(self.e_pmin.get()))
            bot_core.PAUSA_MAX     = int(float(self.e_pmax.get()))
            bot_core.DIGITACAO_MIN = float(self.e_dmin.get())
            bot_core.DIGITACAO_MAX = float(self.e_dmax.get())
        except ValueError:
            messagebox.showwarning("Atencao", "Valores de pausa/digitacao invalidos.")
            return
        resetar_parar()
        self.rodando = True
        self.btn_iniciar.configure(state="disabled")
        self.btn_parar.configure(state="normal")
        self.btn_pular.configure(state="normal")
        self.lbl_status.config(text="  Rodando...", fg=COR_VERDE)
        threading.Thread(target=self._rodar_campanha,
                         args=(vendedor, gemini_link, pool), daemon=True).start()

    # ─── LOOP DA CAMPANHA ────────────────────────────────────────────────
    def _rodar_campanha(self, vendedor, gemini_link, pool_msgs):
        finalizado_normalmente = False
        try:
            self._log("INFO", "Encerrando Chrome anteriores...")
            os.system("taskkill /f /im chrome.exe /t >nul 2>&1")
            os.system("taskkill /f /im chromedriver.exe /t >nul 2>&1")
            time.sleep(2)
            df     = self.df_leads
            mapa   = identificar_layout(df, mapa_externo=self.mapa_colunas)
            ultimo = ler_checkpoint()
            if ultimo > 0:
                self._log("INFO", f"Retomando do lead #{ultimo + 1}")
            if gemini_link:
                self._log("GPT", f"Abrindo Gemini: {gemini_link[:60]}...")
                pronto = threading.Event()
                def aguardar():
                    self.after(0, lambda: messagebox.showinfo("Gemini",
                        "Chrome do Gemini aberto.\nConfirme a conversa treinada e clique OK."))
                    pronto.set()
                configurar_gemini_inicial(callback_aguardar=lambda: (aguardar(), pronto.wait()),
                                          url=gemini_link)
            else:
                self._log("INFO", "Gemini nao configurado — disparos sem IA.")
            self._log("INFO", "Abrindo WhatsApp Web...")
            self.driver_whats = abrir_driver_whatsapp()
            self.driver_whats.get("https://web.whatsapp.com")
            self._log("INFO", "Escaneie o QR Code no Chrome que abriu.")
            self._log("INFO", "Aguardando sincronizacao do WhatsApp (ate 10 min)...")
            WebDriverWait(self.driver_whats, 600).until(
                lambda d: (
                    d.find_elements(By.XPATH, '//div[@contenteditable="true"]') or
                    d.find_elements(By.XPATH, '//div[@id="side"]')              or
                    d.find_elements(By.CSS_SELECTOR, '#pane-side')              or
                    d.find_elements(By.CSS_SELECTOR, '[data-testid="chat-list"]') or
                    d.find_elements(By.CSS_SELECTOR, '[data-testid="intro-title"]')
                )
            )
            time.sleep(4)
            self._log("OK", "WhatsApp conectado!")
            enviados = falhas = pulados = 0
            for idx, row in df.iterrows():
                if not self.rodando:
                    self._log("AVISO", f"Parado no lead #{idx+1}. Checkpoint mantido.")
                    break
                if idx < ultimo:
                    continue
                nome, empresa, telefone = extrair_dados_inteligente(row, mapa)
                pct = (idx + 1) / self.total_leads
                self.after(0, lambda i=idx, pc=pct: self._atualizar_stats(i, pc))
                if len(telefone) < 10:
                    self._log("AVISO", f"[{idx+1}] Sem telefone - pulando")
                    salvar_checkpoint(idx + 1)
                    pulados += 1
                    self._salvar_status_lead(telefone or f"sem_tel_{idx}", "pulado")
                    continue
                self._log("INFO", f"[{idx+1}/{self.total_leads}] {empresa} | {nome or '(Sem Nome)'} | {telefone}")
                if telefone in self.leads_em_manual:
                    salvar_checkpoint(idx + 1)
                    pulados += 1
                    pausa_seguranca_com_monitor(self.driver_whats, telefone_atual=telefone)
                    continue
                res = abrir_chat(self.driver_whats, telefone)
                if res["status"] != "ok":
                    self._log("AVISO", f"[{idx+1}] Chat nao abriu - pulando")
                    salvar_checkpoint(idx + 1)
                    falhas += 1
                    self._salvar_status_lead(telefone, "falha")
                    continue
                # ── Aplica configs atuais da GUI a cada lead ────────────────
                try:
                    bot_core.PAUSA_MIN      = int(float(self.e_pmin.get()))
                    bot_core.PAUSA_MAX      = int(float(self.e_pmax.get()))
                    bot_core.DIGITACAO_MIN  = float(self.e_dmin.get())
                    bot_core.DIGITACAO_MAX  = float(self.e_dmax.get())
                except ValueError:
                    pass
                tpl = random.choice(pool_msgs)
                msg = (tpl.replace("{vendedor}", vendedor)
                          .replace("{empresa}", empresa)
                          .replace("{nome}", nome))
                msg = processar_spintax(msg)
                msg = re.sub(r' +', ' ', msg).replace(" ,", ",")
                try:
                    enviar_fragmentado(self.driver_whats, res["elemento"], msg)
                    self._log("OK", "Mensagem enviada!")
                    enviados += 1
                    self._salvar_status_lead(telefone, "enviado")
                except InterruptedError:
                    self._log("AVISO", "Envio interrompido. Checkpoint mantido.")
                    salvar_checkpoint(idx)
                    break
                except Exception as e:
                    self._log("ERRO", f"Falha ao enviar: {e}")
                    falhas += 1
                    self._salvar_status_lead(telefone, "falha")
                salvar_checkpoint(idx + 1)
                pausa_seguranca_com_monitor(self.driver_whats, telefone_atual=telefone)
            else:
                finalizado_normalmente = True
            self.after(0, lambda: self._atualizar_stats(
                self.total_leads,
                1.0 if finalizado_normalmente else (enviados + falhas + pulados) / max(self.total_leads, 1)))
            if finalizado_normalmente:
                self._log("OK", f"Campanha finalizada! {enviados} enviados | {falhas} falhas | {pulados} pulados")
                resetar_checkpoint()
            else:
                self._log("AVISO", f"Pausada. {enviados} enviados | {falhas} falhas. Checkpoint mantido.")
        except Exception as e:
            self._log("ERRO", f"Erro: {e}")
        finally:
            self._finalizar_ui()
            try:
                if self.driver_whats:
                    self.driver_whats.quit()
            except Exception:
                pass

    # ─── STATS ───────────────────────────────────────────────────────────
    def _atualizar_stats(self, idx, pct):
        """Atualiza apenas barra de progresso — cards são geridos por _salvar_status_lead."""
        self.progressbar.set(pct)
        self.lbl_prog_pct.config(text=f"{idx} / {self.total_leads}  ({int(pct*100)}%)")

    def _checar_atualizacao(self):
        """Verifica silenciosamente se há versão nova no GitHub."""
        def _ok():
            self._log("INFO", f"Bot atualizado — versão {updater.VERSAO_ATUAL}")

        def _nova(versao, url, notas):
            self._log("AVISO", f"Nova versão disponível: {versao}  |  {notas}")
            from tkinter import messagebox
            resp = messagebox.askyesno(
                "Atualização disponível!",
                f"Nova versão {versao} disponível!\n\n"
                f"{notas}\n\n"
                f"Deseja atualizar agora? (O bot reiniciará automaticamente)"
            )
            if resp:
                updater.baixar_e_instalar(url, versao, self)

        updater.verificar_atualizacao(
            callback_ok=lambda: self.after(0, _ok),
            callback_nova_versao=lambda v, u, n: self.after(0, lambda: _nova(v, u, n))
        )

    def _finalizar_ui(self):
        self.rodando = False
        self.after(0, lambda: self.btn_iniciar.configure(state="normal"))
        self.after(0, lambda: self.btn_parar.configure(state="disabled"))
        self.after(0, lambda: self.btn_pular.configure(state="disabled"))
        self.after(0, lambda: self.lbl_status.config(text="  Aguardando", fg=COR_AMARELO))

    # ─── MODO ESCURO / CLARO ─────────────────────────────────────────────────
    def _R(self, widget, **roles):
        """Registra widget no sistema de temas. roles = {attr: chave_do_tema}"""
        self._theme_reg.append((widget, roles))
        return widget

    def _toggle_tema(self):
        global _TEMA_ATUAL, BG, BG_CARD, BG_PANEL, BG_HEADER, BG_INPUT
        global BG_STATUS, BORDER, COR_TEXTO, COR_CINZA
        _TEMA_ATUAL = "claro" if _TEMA_ATUAL == "escuro" else "escuro"
        BG        = _t("BG");       BG_CARD   = _t("BG_CARD")
        BG_PANEL  = _t("BG_PANEL"); BG_HEADER = _t("BG_HEADER")
        BG_INPUT  = _t("BG_INPUT"); BG_STATUS = _t("BG_STATUS")
        BORDER    = _t("BORDER");   COR_TEXTO = _t("COR_TEXTO")
        COR_CINZA = _t("COR_CINZA")
        ctk.set_appearance_mode("light" if _TEMA_ATUAL == "claro" else "dark")
        self._aplicar_tema()
        self.configure(fg_color=_t("BG"))
        self.btn_tema.configure(
            text="☀️ Claro" if _TEMA_ATUAL == "claro" else "🌙 Escuro",
            fg_color=_t("BG_INPUT"), hover_color=_t("BORDER"),
            text_color=_t("COR_CINZA"))

    def _aplicar_tema(self):
        """Itera o registro e aplica as cores certas a cada widget (tk e CTk)."""
        for widget, roles in self._theme_reg:
            try:
                kwargs = {attr: _t(chave) for attr, chave in roles.items()}
                widget.configure(**kwargs)
            except Exception:
                pass


if __name__ == "__main__":
    app = CreditallBotPN()
    app.mainloop()
