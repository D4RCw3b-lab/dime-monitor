from playwright.sync_api import sync_playwright
import requests
import os
from datetime import datetime

# ============ SETTINGS ============
THRESHOLD = 200
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
# ==================================

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        requests.post(url, json=payload, timeout=15)
        print("Telegram message sent")
    except Exception as e:
        print("Error sending Telegram:", e)

def get_hot_deals():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Opening Desidime...")
        page.goto("https://www.desidime.com/hot", wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(8000)

        deals = page.evaluate('''() => {
            const results = [];
            const cards = document.querySelectorAll('.deal-card');

            cards.forEach(card => {
                try {
                    // Find hotness
                    const hotnessEl = card.querySelector('[class*="hotness"]') || card;
                    const text = card.innerText;
                    const match = text.match(/(\\d{2,5})°/);
                    if (!match) return;

                    const hotness = parseInt(match[1]);
                    if (hotness < 180) return;

                    // Find the main deal link
                    const linkEl = card.querySelector('a[href*="/deals/"]');
                    if (!linkEl) return;

                    let link = linkEl.href.split('?')[0];
                    let title = linkEl.innerText.trim() || linkEl.getAttribute('title') || "";

                    // Clean title
                    title = title.replace(/\\s+/g, ' ').substring(0, 110);
                    if (title.length < 10) {
                        // fallback
                        const lines = text.split('\\n').filter(l => l.trim().length > 15);
                        title = lines[0] || "Deal";
                    }

                    results.push({
                        hotness: hotness,
                        title: title,
                        link: link
                    });
                } catch (e) {}
            });

            // Remove duplicates
            const unique = [];
            const seen = new Set();
            for (const d of results) {
                if (!seen.has(d.link)) {
                    seen.add(d.link);
                    unique.push(d);
                }
            }
            return unique;
        }''')

        browser.close()
        return deals

def main():
    print(f"Started at {datetime.now()}")

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Missing Telegram credentials")
        return

    deals = get_hot_deals()
    print(f"Found {len(deals)} deal cards")

    high = [d for d in deals if d["hotness"] >= THRESHOLD]
    high.sort(key=lambda x: x["hotness"], reverse=True)

    if not high:
        print(f"No deals ≥ {THRESHOLD}°")
        return

    msg = f"<b>🔥 Desidime Hot Deals (≥{THRESHOLD}°)</b>\\n\\n"
    for d in high[:8]:
        msg += f"<b>{d['hotness']}°</b> → {d['title']}\\n"
        msg += f"<a href='{d['link']}'>Open Deal</a>\\n\\n"

    msg += f"<i>{datetime.now().strftime('%d %b, %I:%M %p')}</i>"
    send_telegram(msg)
    print("Done")

if __name__ == "__main__":
    main()
