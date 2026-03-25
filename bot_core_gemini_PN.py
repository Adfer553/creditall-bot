import pandas as pd
import random
import time
import sys
import re
import os
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import threading

# ─── GARANTIR PASTA DATA ────────────────────────────────────────────────────────
os.makedirs("data", exist_ok=True)

# ─── CONSTANTES ────────────────────────────────────────────────────────────────
PAUSA_MIN            = 600
PAUSA_MAX            = 1020
PAUSA_FRASE_MIN      = 3
PAUSA_FRASE_MAX      = 7
DIGITACAO_MIN        = 0.04
DIGITACAO_MAX        = 0.12
AGRUPAMENTO_SEGUNDOS = 40
PERFIL_CHROME_WHATS  = r"C:\temp\perfil_whats_sdr"
PERFIL_CHROME_GEMINI = r"C:\temp\perfil_gemini_PN"
ARQUIVO_CHECKPOINT   = "ultimo_lead.txt"
ARQUIVO_CONVERSA     = "url_conversa_gemini.txt"
URL_GEMINI_GLOBAL    = None
DRIVER_GEMINI_GLOBAL = None

_pular_atual_flag = False
_parar_agora   = False   # flag para parada imediata
_log_callback     = None

# ─── POOL DE USER-AGENTS ────────────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
]

STEALTH_JS = """
(function() {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins', {
        get: () => [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
            { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' }
        ]
    });
    Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters)
    );
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Intel Inc.';
        if (parameter === 37446) return 'Intel Iris OpenGL Engine';
        return getParameter.call(this, parameter);
    };
    if (!window.chrome) { window.chrome = {}; }
    if (!window.chrome.runtime) {
        window.chrome.runtime = {
            onConnect: null, onMessage: null, connect: () => {}, sendMessage: () => {},
        };
    }
})();
"""

JS_HISTORICO = r"""
    var linhas = [];
    var msgs = document.querySelectorAll('.copyable-text[data-pre-plain-text]');
    var re = new RegExp('\\[([^\\]]+)\\]\\s*([^:]+):');
    for (var i = 0; i < msgs.length; i++) {
        var msg      = msgs[i];
        var pre      = msg.getAttribute('data-pre-plain-text') || '';
        var conteudo = (msg.innerText || '').trim();
        if (!conteudo) continue;
        var match = pre.match(re);
        if (match) {
            linhas.push('[' + match[1].trim() + '] ' + match[2].trim() + ': ' + conteudo);
        } else {
            linhas.push(pre.trim() + ' ' + conteudo);
        }
    }
    return linhas.join('\n');
"""

JS_ULTIMA_RECEBIDA = r"""
    var msgs = document.querySelectorAll('.copyable-text[data-pre-plain-text]');
    for (var i = msgs.length - 1; i >= 0; i--) {
        var el = msgs[i].parentElement;
        var depth = 0;
        while (el && depth < 20) {
            if ((el.className || '').indexOf('message-in') !== -1) {
                return (msgs[i].innerText || '').trim();
            }
            el = el.parentElement;
            depth++;
        }
    }
    return '';
"""

# ── Set de leads em atendimento manual e Flag de Pulo ─────────────────────────
_leads_em_manual = set()

def marcar_manual(numero):
    _leads_em_manual.add(numero)

def forcar_pulo_atual():
    global _pular_atual_flag
    _pular_atual_flag = True

def parar_imediato():
    """Seta flag para parar digitação imediatamente."""
    global _parar_agora
    _parar_agora = True

def resetar_parar():
    """Limpa a flag antes de iniciar nova campanha."""
    global _parar_agora
    _parar_agora = False


def set_log_callback(fn):
    global _log_callback
    _log_callback = fn

# ─── LOG ────────────────────────────────────────────────────────────────────────
def log(nivel, msg):
    simbolos = {
        "OK": "✅", "ERRO": "❌", "AVISO": "⚠️", "INFO": "ℹ️",
        "DEBUG": "🔍", "GPT": "🤖", "MONITOR": "📡"
    }
    linha = f" {simbolos.get(nivel, '•')} [{nivel}] {msg}"
    print(linha)
    if _log_callback:
        _log_callback(nivel, msg)

# ─── SISTEMA ────────────────────────────────────────────────────────────────────
def matar_chrome_gemini():
    try:
        subprocess.run(
            'wmic process where "name=\'chrome.exe\' and commandline like \'%perfil_gemini_sdr%\'" delete',
            shell=True, capture_output=True
        )
        time.sleep(2)
        log("INFO", "Chrome Gemini órfão encerrado (se havia).")
    except Exception as e:
        log("DEBUG", f"matar_chrome_gemini: {e}")

def matar_chromedriver():
    global DRIVER_GEMINI_GLOBAL
    if DRIVER_GEMINI_GLOBAL:
        log("DEBUG", "Gemini aberto - bloqueando taskkill")
        return
    os.system("taskkill /f /im chromedriver.exe /t >nul 2>&1")
    time.sleep(1)

def ler_checkpoint():
    if os.path.exists(ARQUIVO_CHECKPOINT):
        try:
            with open(ARQUIVO_CHECKPOINT, "r") as f:
                return int(f.read().strip())
        except:
            return 0
    return 0

def salvar_checkpoint(indice):
    with open(ARQUIVO_CHECKPOINT, "w") as f:
        f.write(str(indice))

def resetar_checkpoint():
    if os.path.exists(ARQUIVO_CHECKPOINT):
        os.remove(ARQUIVO_CHECKPOINT)
        log("INFO", "Checkpoint resetado.")

def ler_url_gemini():
    if os.path.exists(ARQUIVO_CONVERSA):
        try:
            with open(ARQUIVO_CONVERSA, "r") as f:
                return f.read().strip()
        except:
            return None
    return None

def salvar_url_gemini(url):
    with open(ARQUIVO_CONVERSA, "w") as f:
        f.write(url)

# ─── ARQUIVOS ───────────────────────────────────────────────────────────────────
def carregar_mensagens_txt(caminho):
    conteudo = ""
    for enc in ("utf-8", "latin-1"):
        try:
            with open(caminho, "r", encoding=enc) as f:
                conteudo = f.read()
            break
        except UnicodeDecodeError:
            continue
    blocos = [msg.strip() for msg in conteudo.split("---") if msg.strip()]
    if not blocos:
        log("ERRO", "Arquivo de mensagens vazio.")
        sys.exit()
    return blocos

# ─── TELEFONE E SPINTAX ─────────────────────────────────────────────────────────
def normalizar_telefone(telefone):
    nums = ''.join(filter(str.isdigit, str(telefone)))
    if len(nums) not in range(10, 14):
        return ""
    if not nums.startswith("55"):
        nums = "55" + nums
    return nums

def processar_spintax(texto):
    while '{' in texto and '}' in texto:
        resultado = re.sub(
            r'\{([^{}]+)\}',
            lambda m: random.choice(m.group(1).split('|')),
            texto
        )
        if resultado == texto:
            break
        texto = resultado
    return texto

# ─── LAYOUT DA PLANILHA ─────────────────────────────────────────────────────────
def identificar_layout(df, mapa_externo=None):
    """
    Se mapa_externo for passado pela GUI, usa ele diretamente.
    Caso contrário, tenta auto-detectar layouts conhecidos.
    """
    if mapa_externo:
        log("INFO", f"Layout via dialog: empresa={mapa_externo.get('col_empresa')} "
                    f"tel={mapa_externo.get('col_tel_pri')} nome={mapa_externo.get('col_nome')}")
        return {
            'tipo': 'manual',
            'col_nome':    mapa_externo.get('col_nome'),
            'col_empresa': mapa_externo.get('col_empresa'),
            'col_tel_pri': mapa_externo.get('col_tel_pri'),
            'col_tel_sec': mapa_externo.get('col_tel_sec'),
        }
    cols = [c.strip() for c in df.columns]
    cols = [c.strip() for c in df.columns]
    if 'SOCIO1Nome' in cols and 'SOCIO1Celular1' in cols:
        log("INFO", "Layout: Completo (Sócios).")
        return {
            'tipo':        'completo',
            'col_nome':    'SOCIO1Nome',
            'col_empresa': 'Razao' if 'Razao' in cols else cols[2],
            'col_tel_pri': 'SOCIO1Celular1',
            'col_tel_sec': 'SOCIO1Celular2' if 'SOCIO1Celular2' in cols else None
        }
    if 'Razão Social' in cols and 'Telefone' in cols:
        log("INFO", "Layout: Simples (Sem Nome).")
        return {
            'tipo':        'simples',
            'col_nome':    None,
            'col_empresa': 'Razão Social',
            'col_tel_pri': 'Telefone',
            'col_tel_sec': None
        }
    col_empresa = input("Nome coluna EMPRESA: ").strip()
    col_tel     = input("Nome coluna TELEFONE: ").strip()
    col_nome    = input("Nome coluna NOME (Enter se não tiver): ").strip()
    return {
        'tipo':        'manual',
        'col_nome':    col_nome or None,
        'col_empresa': col_empresa,
        'col_tel_pri': col_tel,
        'col_tel_sec': None
    }

def extrair_dados_inteligente(row, mapa):
    empresa = str(row.get(mapa['col_empresa'], '')).strip()
    nome    = ""
    if mapa['col_nome']:
        bruto = str(row.get(mapa['col_nome'], '')).strip()
        if bruto and bruto.lower() not in ('nan', 'none', ''):
            nome = re.split(r'\*|;|,', bruto)[0].split()[0].capitalize()
    tel_raw = str(row.get(mapa['col_tel_pri'], '')).strip()
    if (not tel_raw or tel_raw.lower() in ('nan', 'none', '')) and mapa['col_tel_sec']:
        tel_raw = str(row.get(mapa['col_tel_sec'], '')).strip()
    telefone = normalizar_telefone(tel_raw)
    return nome, empresa, telefone

# ─── DRIVERS CHROME ANTI-DETECÇÃO ───────────────────────────────────────────────
def abrir_driver_whatsapp():
    opts = Options()
    opts.add_argument(f"--user-data-dir={PERFIL_CHROME_WHATS}")
    opts.add_argument("--profile-directory=Default")
    user_agent = random.choice(USER_AGENTS)
    opts.add_argument(f"--user-agent={user_agent}")
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-software-rasterizer")
    opts.add_argument("--disable-accelerated-2d-canvas")
    opts.add_argument("--disable-background-timer-throttling")
    opts.add_argument("--disable-renderer-backgrounding")
    s = Service(ChromeDriverManager().install(), log_output=os.devnull)
    driver = webdriver.Chrome(service=s, options=opts)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": STEALTH_JS})
    log("INFO", f"Driver camuflado iniciado. User-Agent: {user_agent[:60]}...")
    return driver

def abrir_driver_gemini():
    opts = Options()
    opts.add_argument(f"--user-data-dir={PERFIL_CHROME_GEMINI}")
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-notifications")
    user_agent = random.choice(USER_AGENTS)
    opts.add_argument(f"--user-agent={user_agent}")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-software-rasterizer")
    opts.add_argument("--disable-background-timer-throttling")
    opts.add_argument("--disable-renderer-backgrounding")
    s = Service(ChromeDriverManager().install(), log_output=os.devnull)
    driver = webdriver.Chrome(service=s, options=opts)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": STEALTH_JS})
    log("INFO", f"Driver Gemini iniciado. User-Agent: {user_agent[:60]}...")
    return driver

# ─── WHATSAPP ───────────────────────────────────────────────────────────────────
def abrir_chat(driver, telefone):
    driver.get(f"https://web.whatsapp.com/send?phone={telefone}")
    time.sleep(4)
    try:
        restaurar = driver.find_element(
            By.XPATH,
            '//button[contains(text(),"Restaurar") or contains(text(),"Restore")]'
        )
        restaurar.click()
        time.sleep(5)
    except:
        pass
    try:
        driver.maximize_window()
    except:
        pass
    for _ in range(15):
        try:
            el = driver.find_element(By.XPATH, '//footer//div[@contenteditable="true"]')
            if el.is_displayed():
                return {"status": "ok", "elemento": el}
        except:
            pass
        time.sleep(1)
    return {"status": "timeout", "elemento": None}

def digitar_humanizado(elemento, texto):
    texto = ''.join(c for c in texto if ord(c) <= 0xFFFF)
    elemento.click()
    time.sleep(random.uniform(0.3, 0.7))
    for char in texto:
        if _parar_agora:
            raise InterruptedError("Parada imediata acionada.")
        elemento.send_keys(char)
        time.sleep(random.uniform(DIGITACAO_MIN, DIGITACAO_MAX))

def enviar_fragmentado(driver, elemento, mensagem_completa):
    frases = mensagem_completa.split("|")
    for i, frase in enumerate(frases):
        if _parar_agora:
            raise InterruptedError("Parada imediata acionada.")
        frase_limpa = frase.strip()
        if not frase_limpa:
            continue
        digitar_humanizado(elemento, frase_limpa)
        elemento.send_keys(Keys.ENTER)
        if i < len(frases) - 1:
            time.sleep(random.uniform(PAUSA_FRASE_MIN, PAUSA_FRASE_MAX))
            try:
                elemento.click()
            except:
                pass

# ─── GEMINI: ENVIAR E RESPONDER ─────────────────────────────────────────────────
def _injetar_texto_quill(driver, editor_el, texto):
    """execCommand — compatível com Trusted Types (Chrome 145+), seguro em threads."""
    driver.execute_script("""
        var ed  = arguments[0];
        var txt = arguments[1];
        ed.focus();
        document.execCommand('selectAll', false, null);
        document.execCommand('insertText', false, txt);
    """, editor_el, texto)

def _contar_msgs_gemini(driver):
    try:
        return driver.execute_script(
            "return document.querySelectorAll('message-content').length;"
        ) or 0
    except:
        return 0

def enviar_para_gemini_e_responder(driver_whats, telefone, mensagem_cliente):
    global DRIVER_GEMINI_GLOBAL, URL_GEMINI_GLOBAL
    try:
        log("GPT", f"Enviando para Gemini: {mensagem_cliente[:60]}...")
        if not DRIVER_GEMINI_GLOBAL or not URL_GEMINI_GLOBAL:
            log("ERRO", "Gemini não configurado.")
            return False

        DRIVER_GEMINI_GLOBAL.get(URL_GEMINI_GLOBAL)
        time.sleep(5)

        SELETOR_INPUT = 'div.ql-editor[aria-label="Insira um comando para o Gemini"]'
        try:
            input_gemini = WebDriverWait(DRIVER_GEMINI_GLOBAL, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, SELETOR_INPUT))
            )
        except Exception:
            log("ERRO", "Input do Gemini não encontrado — verifique o link.")
            return False

        qtd_antes = _contar_msgs_gemini(DRIVER_GEMINI_GLOBAL)
        log("DEBUG", f"Mensagens Gemini antes: {qtd_antes}")

        _injetar_texto_quill(DRIVER_GEMINI_GLOBAL, input_gemini, mensagem_cliente)
        time.sleep(1.2)
        log("DEBUG", "Texto injetado no Quill.")

        enviado = False
        for sel in ["button.send-button",
                    "button[aria-label*='Enviar']",
                    "button[aria-label*='Send']"]:
            try:
                btn = WebDriverWait(DRIVER_GEMINI_GLOBAL, 4).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                )
                btn.click()
                enviado = True
                log("DEBUG", f"Enviado via botão ({sel}).")
                break
            except:
                pass
        if not enviado:
            input_gemini.send_keys(Keys.ENTER)
            log("DEBUG", "Enviado via ENTER (fallback).")

        log("GPT", "Aguardando resposta do Gemini...")
        time.sleep(4)

        resposta      = ""
        texto_estavel = ""
        estavel_count = 0

        for tentativa in range(150):
            qtd_agora = _contar_msgs_gemini(DRIVER_GEMINI_GLOBAL)
            if qtd_agora > qtd_antes:
                texto_atual = DRIVER_GEMINI_GLOBAL.execute_script("""
                    var els = document.querySelectorAll('message-content');
                    if (!els.length) return '';
                    var last = els[els.length - 1];
                    var sels = ['.model-response-text','structured-content-container',
                                '.response-content','div.markdown','model-response'];
                    for (var i = 0; i < sels.length; i++) {
                        var el = last.querySelector(sels[i]);
                        if (el && el.innerText.trim()) return el.innerText.trim();
                    }
                    return last.innerText.trim();
                """) or ""
                ainda_gerando = DRIVER_GEMINI_GLOBAL.execute_script("""
                    return document.querySelectorAll(
                        'button[aria-label*="Interromper"],button[aria-label*="Stop"]'
                    ).length > 0;
                """)
                log("DEBUG", f"[{tentativa+1}] msgs={qtd_agora} gerando={ainda_gerando} chars={len(texto_atual)}")
                if texto_atual and not ainda_gerando:
                    if texto_atual == texto_estavel:
                        estavel_count += 1
                        if estavel_count >= 2:
                            resposta = texto_atual
                            log("GPT", f"Resposta estável capturada na iteração {tentativa+1}.")
                            break
                    else:
                        texto_estavel = texto_atual
                        estavel_count = 0
            else:
                if tentativa % 10 == 0:
                    log("DEBUG", f"[{tentativa+1}] Aguardando nova msg... (antes={qtd_antes})")
            time.sleep(1)
        else:
            if texto_estavel:
                resposta = texto_estavel
                log("AVISO", "Timeout — usando última resposta detectada.")
            else:
                log("ERRO", "Gemini não respondeu no tempo limite.")
                return False

        for prefixo in ["Mostrar raciocínio\n", "O Gemini disse\n", "O Gemini disse"]:
            if resposta.startswith(prefixo):
                resposta = resposta[len(prefixo):].strip()

        if not resposta:
            log("ERRO", "Resposta ficou vazia após limpeza.")
            return False

        log("GPT", f"Resposta capturada ({len(resposta)} chars): {resposta[:80]}...")

        # Sempre reabre o chat do telefone correto antes de enviar
        if telefone:
            res = abrir_chat(driver_whats, telefone)
            if res["status"] != "ok":
                log("ERRO", f"Chat WhatsApp {telefone} não abriu para enviar resposta.")
                return False
            chat_input = res["elemento"]
        else:
            try:
                chat_input = driver_whats.find_element(
                    By.XPATH, '//footer//div[@contenteditable="true"]'
                )
            except:
                log("ERRO", "Input do WhatsApp não encontrado.")
                return False

        resposta_fmt = resposta.replace("\n\n", "|").replace("\n", " ")
        enviar_fragmentado(driver_whats, chat_input, resposta_fmt)
        log("OK", "Resposta do Gemini enviada ao lead!")
        return True

    except Exception as e:
        log("ERRO", f"Erro crítico no Gemini: {str(e)[:120]}")
        return False

# ─── MONITOR INTERNO (thread) ───────────────────────────────────────────────────
# CORREÇÃO RACE CONDITION:
# pending_text e last_message_time agora são locais a cada chamada de
# pausa_seguranca_com_monitor, passados via dicionário 'state'.
# Múltiplas threads de monitor não compartilham mais estado entre si.

def _monitor_com_silencio(driver_whats, state, telefone_atual=None):
    """
    state = {
        'pending':    str   — histórico pendente para enviar ao Gemini
        'last_time':  float — timestamp da última msg recebida
        'pausa_alvo': int   — segundos alvo do anti-ban (lido pelo loop principal)
        'ativo':      bool  — False = encerrar esta thread imediatamente
    }
    """
    log("MONITOR", "Monitor ativo...")
    ultima_msg_recebida = ""

    while state['ativo']:
        if telefone_atual and telefone_atual in _leads_em_manual:
            log("MONITOR", f"Lead {telefone_atual} assumido manualmente — monitor encerrado.")
            break

        agora = time.time()

        if agora - state['last_time'] > AGRUPAMENTO_SEGUNDOS and state['pending']:
            log("MONITOR", "40s sem novas → enviando histórico para Gemini")
            texto_para_enviar  = state['pending']
            state['pending']   = ""
            state['last_time'] = time.time()
            enviar_para_gemini_e_responder(driver_whats, telefone_atual, texto_para_enviar)
            state['last_time']   = time.time()
            state['pausa_alvo']  = random.randint(PAUSA_MIN, PAUSA_MAX)
            log("MONITOR", f"Bot respondeu — anti-ban resetado para "
                           f"{state['pausa_alvo']//60}m {state['pausa_alvo']%60}s.")

        try:
            time.sleep(15)
            if not state['ativo']:
                break

            historico = driver_whats.execute_script(JS_HISTORICO)
            if not historico or len(historico.strip()) < 5:
                continue

            ultima_recebida = driver_whats.execute_script(JS_ULTIMA_RECEBIDA)
            if ultima_recebida and ultima_recebida != ultima_msg_recebida:
                ultima_msg_recebida  = ultima_recebida
                state['last_time']   = time.time()
                state['pending']     = historico
                state['pausa_alvo']  = random.randint(PAUSA_MIN, PAUSA_MAX)
                log("MONITOR", f"Cliente respondeu — anti-ban resetado para "
                               f"{state['pausa_alvo']//60}m {state['pausa_alvo']%60}s.")
                log("MONITOR", f"Nova msg: {ultima_recebida[:50]}...")

        except Exception as e:
            log("ERRO", f"Monitor exception: {e}")
            time.sleep(5)

    # Envia o que ficou pendente antes de morrer
    if state['pending']:
        texto_para_enviar = state['pending']
        state['pending']  = ""
        enviar_para_gemini_e_responder(driver_whats, telefone_atual, texto_para_enviar)

    log("MONITOR", "Monitor finalizado.")

# ─── PAUSA ANTI-BAN + SILÊNCIO UNIFICADOS ───────────────────────────────────────
def pausa_seguranca_com_monitor(driver_whats, telefone_atual=None):
    global _pular_atual_flag

    # Estado ISOLADO por chamada — sem compartilhamento entre threads de leads diferentes
    state = {
        'pending':    "",
        'last_time':  time.time() - AGRUPAMENTO_SEGUNDOS - 1,
        'pausa_alvo': random.randint(PAUSA_MIN, PAUSA_MAX),
        'ativo':      True,
    }

    log("INFO", f"Anti-ban iniciado: {state['pausa_alvo']//60}m {state['pausa_alvo']%60}s "
                f"— reseta se cliente responder.")

    t = threading.Thread(
        target=_monitor_com_silencio,
        args=(driver_whats, state, telefone_atual),
        daemon=True
    )
    t.start()

    ultimo_log   = 0
    tempo_inicio = time.time()

    while True:
        if _pular_atual_flag:
            log("AVISO", "⏭️ Pulo forçado — avançando para o próximo lead imediatamente.")
            _pular_atual_flag  = False
            state['ativo']     = False
            break

        if telefone_atual and telefone_atual in _leads_em_manual:
            log("AVISO", f"📲 {telefone_atual} assumido — saindo do anti-ban imediatamente.")
            state['ativo'] = False
            break

        agora    = time.time()
        silencio = agora - state['last_time']

        if silencio >= state['pausa_alvo']:
            log("INFO", f"Anti-ban de {state['pausa_alvo']//60}m {state['pausa_alvo']%60}s "
                        f"sem atividade → próximo lead.")
            state['ativo'] = False
            break

        tempo_total = agora - tempo_inicio
        if int(tempo_total) - ultimo_log >= 60:
            ultimo_log = int(tempo_total)
            falta = max(0, state['pausa_alvo'] - int(silencio))
            log("INFO", f"Silêncio: {int(silencio)}s | "
                        f"faltam ~{falta}s para próximo lead "
                        f"(alvo atual: {state['pausa_alvo']//60}m {state['pausa_alvo']%60}s)")

        time.sleep(1)

# ─── GEMINI: SETUP INICIAL ───────────────────────────────────────────────────────
def configurar_gemini_inicial(callback_aguardar=None, url=None):
    global URL_GEMINI_GLOBAL, DRIVER_GEMINI_GLOBAL
    log("GPT", "Abrindo Gemini treinado...")

    matar_chrome_gemini()
    DRIVER_GEMINI_GLOBAL = abrir_driver_gemini()

    if url:
        URL_GEMINI_GLOBAL = url
        log("GPT", f"Usando link da GUI: {url[:60]}...")
    else:
        URL_GEMINI_GLOBAL = ler_url_gemini() or "https://gemini.google.com"
        log("GPT", f"Usando link salvo/padrão: {URL_GEMINI_GLOBAL[:60]}...")

    DRIVER_GEMINI_GLOBAL.get(URL_GEMINI_GLOBAL)
    time.sleep(3)

    if callback_aguardar:
        callback_aguardar()
    else:
        input("\n[Gemini] Confirme que a conversa carregou e pressione ENTER...\n")

    salvar_url_gemini(URL_GEMINI_GLOBAL)
    log("GPT", f"Gemini configurado e pronto: {URL_GEMINI_GLOBAL[:60]}...")
    return URL_GEMINI_GLOBAL
