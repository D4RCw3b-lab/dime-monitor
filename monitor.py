from playwright.sync_api import sync_playwright
import requests
import os
import re
import json
from datetime import datetime

# ============ SETTINGS ============
THRESHOLD = 200          # Change this number if you want (e.g. 150 or 300)
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
    except Exception as e:
        print("Telegram error:", e)

def get_hot_deals():
    deals = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.desidime.com/hot", wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(5000)  # wait extra for deals to load

        # Get all text content
        content = page.content()

        # Find all hotness numbers like 247°
        matches = re.findall(r'(\d{2,5})°', content)

        # Also try to extract title + link using JavaScript
        extracted = page.evaluate('''() => {
            const results = [];
            const elements = document.querySelectorAll('a, div, span');
            for (let el of elements) {
                const text = el.innerText || "";
                const match = text.match(/(\d{2,5})°/);
                if (match) {
                    const hotness = parseInt(match[1]);
                    if (hotness >= 150) {
                        let title = text.replace(/\\d+°/, "").trim().substring(0, 120);
                        let link = "";
                        if (el.tagName === "A" && el.href) {
                            link = el.href;
                        } else {
                            const parentLink = el.closest("a");
                            if (parentLink) link = parentLink.href;
                        }
                        if (title.length > 15) {
                            results.push({
                                hotness: hotness,
                                title: title,
                                link: link
                            });
                        }
                    }
                }
            }
            // Remove duplicates
            const unique = [];
            const seen = new Set();
            for (let r of results) {
                const key = r.title.substring(0, 40);
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
    print(f"Found {len(deals)} deals with decent hotness")

    high_deals = [d for d in deals if d["hotness"] >= THRESHOLD]

    if not high_deals:
        print("No deals crossed the threshold.")
        return

    # Sort by highest hotness
    high_deals.sort(key=lambda x: x["hotness"], reverse=True)

    message = f"<b>🔥 Desidime Hot Deals Alert (≥{THRESHOLD}°)</b>\n\n"
    
    for deal in high_deals[:8]:  # send max 8 deals
        title = deal["title"][:90]
        hot = deal["hotness"]
        link = deal["link"] if deal["link"] else "https://www.desidime.com/hot"
        
        message += f"<b>{hot}°</b> → {title}\n"
        message += f"<a href='{link}'>Open Deal</a>\n\n"

    message += f"<i>Checked at {datetime.now().strftime('%d %b %Y %I:%M %p')}</i>"
    
    send_telegram(message)
    print("Notification sent successfully!")

if __name__ == "__main__":
    main()
