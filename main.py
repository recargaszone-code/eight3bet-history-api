import time
import random
import threading
import json
import requests
import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

app = FastAPI(title="888Bets Aviator History API")

# ===================== CONFIGURAÇÕES =====================
URL = "https://m.888bets.co.mz/pt/games/jogos/detail/normal/7787"

TELEGRAM_TOKEN = '8583470384:AAF0poQRbfGkmGy7cA604C4b_-MhYj-V7XM'
CHAT_ID = '7427648935'

PHONE = "863584494"
PASSWORD = "0000000000"

# Lista de proxies Senegal (SN) frescos – HTTP elite/anonymous
PROXY_LIST = [
    "http://196.1.97.198:80",     # 1 - checked recently, pode estar morto
    "http://154.65.39.7:80",      # 2 - elite SN
    "http://154.65.39.8:80",      # 3 - elite SN
    "http://196.1.93.16:80",      # 4 - elite SN
]

# Variáveis globais
history_lock = threading.Lock()
current_history = []
history_file = "historico.json"
current_proxy_index = 0  # começa no primeiro

def save_history():
    try:
        with open(history_file, "w") as f:
            json.dump(current_history, f)
    except:
        pass

def load_history():
    global current_history
    try:
        with open(history_file, "r") as f:
            current_history = json.load(f)[-30:]
    except:
        current_history = []

load_history()

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload, timeout=10)
    except:
        pass

def send_telegram_photo(photo_path, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    try:
        with open(photo_path, "rb") as photo:
            files = {"photo": photo}
            data = {"chat_id": CHAT_ID, "caption": caption, "parse_mode": "HTML"}
            requests.post(url, data=data, files=files, timeout=30)
        os.remove(photo_path)
    except Exception as e:
        send_telegram_message(f"Erro ao enviar foto: {str(e)}")

def take_screenshot(page, label):
    try:
        path = f"screenshot_{int(time.time())}_{label.replace(' ', '_')}.png"
        page.screenshot(path=path, full_page=True)
        send_telegram_photo(path, f"📸 {label}")
    except:
        send_telegram_message(f"Não consegui capturar screenshot: {label}")

def get_next_proxy():
    global current_proxy_index
    proxy = PROXY_LIST[current_proxy_index]
    current_proxy_index = (current_proxy_index + 1) % len(PROXY_LIST)
    return proxy

def update_history(new_list):
    global current_history
    with history_lock:
        if not new_list:
            return False
        atual_set = set(current_history)
        novos = [x for x in new_list if x not in atual_set]
        if novos:
            current_history.extend(novos)
            if len(current_history) > 30:
                current_history = current_history[-30:]
            save_history()
            return True
    return False

def get_payouts(frame, page):
    try:
        payouts_block = frame.locator(".payouts-block").first
        elements = payouts_block.locator(".payout").all()
        valores = [el.inner_text().strip() for el in elements if el.inner_text().strip()]

        take_screenshot(page, "Leitura do histórico")
        return valores
    except Exception as e:
        send_telegram_message(f"Erro ao ler payouts: {str(e)}")
        take_screenshot(page, "Erro na leitura de payouts")
        return None

def scraper_worker():
    send_telegram_message("🚀 Scraper iniciado com lista rotativa de proxies Senegal (SN)")

    while True:
        proxy_server = get_next_proxy()
        send_telegram_message(f"🔄 Tentando proxy Senegal: {proxy_server} (índice {current_proxy_index})")

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
                )
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
                    proxy={"server": proxy_server}
                )
                page = context.new_page()

                send_telegram_message("🌐 Acessando página...")
                page.goto(URL, wait_until="networkidle", timeout=90000)  # timeout menor pra falhar rápido
                time.sleep(3)
                take_screenshot(page, f"Página inicial via proxy {proxy_server}")

                # Verifica bloqueio geo
                content = page.content().lower()
                if "location services" in content or "don't have access" in content or "gambling regulations" in content:
                    take_screenshot(page, f"Bloqueio detectado com proxy {proxy_server}")
                    send_telegram_message(f"❌ Geo-block no proxy {proxy_server}. Tentando próximo...")
                    raise Exception("Geo-block detectado – trocando proxy")

                send_telegram_message("🔍 Esperando campo de telefone...")
                page.wait_for_selector('input#phone', timeout=60000)
                take_screenshot(page, "Campo de telefone encontrado")

                send_telegram_message("🔑 Preenchendo telefone...")
                page.fill('input#phone', PHONE, timeout=60000)
                time.sleep(random.uniform(0.8, 1.7))

                send_telegram_message("🔑 Preenchendo senha...")
                page.fill('input[type="password"]', PASSWORD, timeout=60000)
                time.sleep(random.uniform(0.9, 1.8))

                send_telegram_message("🖱️ Clicando em login...")
                page.click('button.login-btn:has-text("Iniciar sessão")', timeout=30000)
                time.sleep(6)
                take_screenshot(page, "Após clique no login")

                send_telegram_message("⏳ Aguardando iframe...")
                page.wait_for_selector('iframe#gm-frm', timeout=90000)
                iframe_locator = page.frame_locator('iframe#gm-frm')
                iframe_locator.locator(".payouts-block").first.wait_for(state="visible", timeout=60000)

                take_screenshot(page, "Iframe + payouts-block carregados")

                send_telegram_message("🎮 <b>Conectado ao jogo! Monitorando...</b>")

                ultimo_set = set()

                while True:
                    try:
                        historico_atual = get_payouts(iframe_locator, page)
                        if historico_atual and update_history(historico_atual):
                            novos = [x for x in historico_atual if x not in ultimo_set]
                            if novos:
                                msg = f"🔔 <b>NOVO HISTÓRICO</b>\n\nÚltimos: {' | '.join(historico_atual[:8])}\nNovos: {' | '.join(novos)}"
                                send_telegram_message(msg)
                            ultimo_set = set(historico_atual)

                        time.sleep(random.uniform(4.2, 6.8))
                    except Exception as inner_e:
                        send_telegram_message(f"Erro no loop: {str(inner_e)}")
                        take_screenshot(page, f"Erro loop – {str(inner_e)[:60]}")
                        time.sleep(8)
        except Exception as e:
            send_telegram_message(f"❌ Erro grave com proxy {proxy_server}: {str(e)}\nTentando próximo em 15s...")
            print(f"Erro grave: {e}")
            time.sleep(15)

# ===================== ENDPOINTS =====================
@app.get("/")
def home():
    return {"status": "online"}

@app.get("/health")
def health():
    with history_lock:
        return {"status": "healthy", "history_count": len(current_history)}

@app.get("/history")
def get_history():
    with history_lock:
        return JSONResponse({
            "history": current_history,
            "count": len(current_history),
            "timestamp": time.time()
        })

# ===================== INICIAR =====================
if __name__ == "__main__":
    send_telegram_message("🔄 Iniciando com rotativo de proxies Senegal...")
    thread = threading.Thread(target=scraper_worker, daemon=True)
    thread.start()

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
