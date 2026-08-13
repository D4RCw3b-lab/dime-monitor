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
        print("Telegram sent successfully")
    except Exception as e:
        print("Telegram error:", e)

def get_hot_deals():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("Loading Desidime Hot page...")
        page.goto("https://www.desidime.com/hot", wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(7000)

        # More accurate extraction
        deals = page.evaluate('''() => {
            const results = [];
            const links = Array.from(document.querySelectorAll('a[href*="/deals/"]'));

            for (const link of links) {
                const href = link.href;
                if (!href || !href.includes('/deals/') || href.includes('ref=')) {
                    // clean the link later
                }

                // Get the card / parent container
                let card = link.closest('div') || link.parentElement;
                if (!card) continue;

                const text = card.innerText || "";
                const match = text.match(/(\\d{2,5})°/);
                if (!match) continue;

                const hotness = parseInt(match[1]);
                if (hotness < 180) continue;

                // Clean title
                let title = link.innerText.trim();
                if (!title || title.length < 10) {
                    title = text.split('\\n').find(line => line.length > 15 && !line.includes('°')) || text.substring(0, 100);
                }
                title = title.replace(/\\s+/g, ' ').trim().substring(0, 100);

                // Clean link (remove query parameters)
                let cleanLink = href.split('?')[0];

                // Avoid duplicates and bad titles
                if (title.toLowerCase().includes('most searched') || 
                    title.toLowerCase().includes('best deals, coupon') ||
                    title.toLowerCase().includes('hottest deals') ||
                    title.length < 12) {
                    continue;
                }

                results.push({
                    hotness: hotness,
                    title: title,
                    link: cleanLink
                });
            }

            // Remove duplicates by link
            const unique = [];
            const seen = new Set();
            for (const item of results) {
                if (!seen.has(item.link)) {
                    seen.add(item.link);
                    unique.push(item);
                }
            }
            return unique;
        }''')

        browser.close()
        return deals

def main():
    print(f"Running at {datetime.now()}")

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Missing Telegram credentials")
        return

    deals = get_hot_deals()
    print(f"Found {len(deals)} potential deals")

    high_deals = [d for d in deals if d["hotness"] >= THRESHOLD]
    high_deals.sort(key=lambda x: x["hotness"], reverse=True)

    if not high_deals:
        print(f"No deals above {THRESHOLD}°")
        return

    message = f"<b>🔥 Desidime Hot Deals (≥{THRESHOLD}°)</b>\\n\\n"

    for deal in high_deals[:8]:
        message += f"<b>{deal['hotness']}°</b> → {deal['title']}\\n"
        message += f"<a href='{deal['link']}'>Open Deal</a>\\n\\n"

    message += f"<i>{datetime.now().strftime('%d %b %Y, %I:%M %p')}</i>"

    send_telegram(message)
    print("Done")

if __name__ == "__main__":
    main()
