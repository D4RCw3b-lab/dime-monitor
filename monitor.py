from playwright.sync_api import sync_playwright
import requests
import os
import re
from datetime import datetime

# ============ SETTINGS ============
THRESHOLD = 200          # Change this if you want (150, 250, 300 etc.)
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
        print("Telegram error:", e)

def get_hot_deals():
    deals = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("Opening Desidime...")
        page.goto("https://www.desidime.com/hot", wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(6000)

        # Better extraction using JavaScript
        extracted = page.evaluate('''() => {
            const results = [];
            const allLinks = document.querySelectorAll('a[href*="/deals/"]');

            allLinks.forEach(link => {
                try {
                    const href = link.href;
                    if (!href.includes('/deals/')) return;

                    // Look for hotness near this link
                    let container = link.closest('div') || link.parentElement;
                    let text = container ? container.innerText : link.innerText;
                    
                    const match = text.match(/(\\d{2,5})°/);
                    if (!match) return;

                    const hotness = parseInt(match[1]);
                    if (hotness < 150) return;

                    // Get clean title
                    let title = link.innerText.trim() || text.replace(/\\d+°/g, "").trim();
                    title = title.replace(/\\s+/g, " ").substring(0, 110);

                    if (title.length < 12) return;

                    results.push({
                        hotness: hotness,
                        title: title,
                        link: href.split('?')[0]   // remove tracking parameters
                    });
                } catch (e) {}
            });

            // Remove duplicates
            const unique = [];
            const seen = new Set();
            for (let r of results) {
                const key = r.link;
                if (!seen.has(key)) {
                    seen.add(key);
                    unique.push(r);
                }
            }
            return unique;
        }''')

        browser.close()
        return extracted

def main():
    print(f"Checking Desidime at {datetime.now()}")

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: Telegram credentials missing")
        return

    deals = get_hot_deals()
    print(f"Total deals found: {len(deals)}")

    high_deals = [d for d in deals if d["hotness"] >= THRESHOLD]
    high_deals.sort(key=lambda x: x["hotness"], reverse=True)

    if not high_deals:
        print(f"No deals above {THRESHOLD}° right now.")
        return

    message = f"<b>🔥 Desidime Hot Deals (≥{THRESHOLD}°)</b>\n\n"

    for deal in high_deals[:10]:
        title = deal["title"]
        hot = deal["hotness"]
        link = deal["link"]

        message += f"<b>{hot}°</b>  →  {title}\n"
        message += f"<a href='{link}'>Open Deal</a>\n\n"

    message += f"<i>Checked at {datetime.now().strftime('%d %b %Y, %I:%M %p')}</i>"

    send_telegram(message)
    print("Notification sent!")

if __name__ == "__main__":
    main()
