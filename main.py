import time
import random
import threading
import json
import requests
import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from playwright.sync_api import sync_playwright

app = FastAPI(title="888Bets Aviator History API")

# ===================== CONFIGURAÇÕES =====================
URL = "https://m.888bets.co.mz/pt/games/jogos/detail/normal/7787"

TELEGRAM_TOKEN = '8583470384:AAF0poQRbfGkmGy7cA604C4b_-MhYj-V7XM'
CHAT_ID = '7427648935'

PHONE = "863584494"
PASSWORD = "0000000000"

# Variáveis globais
history_lock = threading.Lock()
current_history = []
history_file = "historico.json"

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
            requests.post(url, data=data, files=files, timeout=20)
        os.remove(photo_path)  # apaga o arquivo temporário
    except Exception as e:
        send_telegram_message(f"Erro ao enviar print: {str(e)}")

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
        
        # Envia print sempre que lê o histórico (para debug)
        screenshot_path = f"screenshot_{int(time.time())}.png"
        page.screenshot(path=screenshot_path)
        send_telegram_photo(
            screenshot_path,
            f"📸 Leitura do histórico ({len(valores)} itens):\n{' | '.join(valores[:8])}"
        )
        
        return valores
    except Exception as e:
        send_telegram_message(f"Erro ao ler payouts: {str(e)}")
        return None

def scraper_worker():
    send_telegram_message("🚀 <b>Scraper iniciado no Render</b> (headless mode)")
    
    while True:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
                )
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36"
                )
                page = context.new_page()

                send_telegram_message("🌐 Acessando URL...")
                page.goto(URL, wait_until="networkidle", timeout=90000)

                send_telegram_message("🔑 Fazendo login...")
                page.fill('input#phone', PHONE)
                time.sleep(random.uniform(0.8, 1.7))
                page.fill('input[type="password"]', PASSWORD)
                time.sleep(random.uniform(0.9, 1.8))
                page.click('button.login-btn:has-text("Iniciar sessão")', timeout=15000)
                time.sleep(5)

                # Print após login
                screenshot_path = f"login_{int(time.time())}.png"
                page.screenshot(path=screenshot_path)
                send_telegram_photo(screenshot_path, "📸 Após login (verifique se está logado)")

                send_telegram_message("⏳ Aguardando iframe do jogo...")
                page.wait_for_selector('iframe#gm-frm', timeout=60000)
                iframe_locator = page.frame_locator('iframe#gm-frm')
                iframe_locator.locator(".payouts-block").first.wait_for(state="visible", timeout=45000)

                # Print quando detecta o iframe e payouts-block
                screenshot_path = f"iframe_carregado_{int(time.time())}.png"
                page.screenshot(path=screenshot_path)
                send_telegram_photo(screenshot_path, "✅ Iframe carregado e payouts-block visível!")

                send_telegram_message("🎮 <b>Conectado ao jogo! Monitorando histórico...</b>")

                ultimo_set = set()

                while True:
                    try:
                        historico_atual = get_payouts(iframe_locator, page)  # passa page para screenshot
                        if historico_atual and update_history(historico_atual):
                            novos = [x for x in historico_atual if x not in ultimo_set]
                            if novos:
                                msg = f"🔔 <b>NOVO HISTÓRICO DETECTADO</b>\n\nÚltimos: {' | '.join(historico_atual[:8])}\nNovos: {' | '.join(novos)}"
                                send_telegram_message(msg)
                                print(f"📨 Telegram enviado → {len(current_history)} itens")
                            ultimo_set = set(historico_atual)

                        time.sleep(random.uniform(4.2, 6.8))
                    except Exception as inner_e:
                        send_telegram_message(f"Erro no loop de leitura: {str(inner_e)}")
                        time.sleep(8)
        except Exception as e:
            send_telegram_message(f"Erro grave no navegador: {str(e)} → reiniciando em 15s")
            print(f"Erro grave: {e} → reiniciando em 15s")
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
    send_telegram_message("🔄 Iniciando thread de monitoramento...")
    thread = threading.Thread(target=scraper_worker, daemon=True)
    thread.start()

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
