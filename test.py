from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
import re
import time


def scrape_superrich_thailand(url="https://www.superrichthailand.com", retries=3):
    """
    Scrape exchange rates (currency name, code, buying, selling) from SuperRich Thailand.
    Filters out menu rows and only keeps rows with numeric rates.
    """
    for attempt in range(1, retries + 1):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=60000)

                # Wait for table content
                page.wait_for_selector("table", timeout=60000)
                page.screenshot(path="example.png")
                html = page.content()
                print(html)
                # browser.close()

            soup = BeautifulSoup(html, "html.parser")

            data = []
            for row in soup.find_all("tr"):
                cols = [c.get_text(strip=True) for c in row.find_all("td")]
                if len(cols) >= 4:
                    currency_name, currency_code, buying_rate, selling_rate = cols[:4]

                    # ✅ keep only rows with numbers in buy/sell
                    if re.search(r"\d", buying_rate) and re.search(r"\d", selling_rate):
                        data.append({
                            "currency_name": currency_name,
                            "currency_code": currency_code,
                            "buying_rate": buying_rate,
                            "selling_rate": selling_rate
                        })

            if not data:
                raise ValueError("No valid exchange rate rows found")

            return data

        except Exception as e:
            print(f"[Attempt {attempt}] Error: {e}")
            time.sleep(3)

    return []


if __name__ == "__main__":
    rates = scrape_superrich_thailand()

    if rates:
        print(f"\n✅ Extracted {len(rates)} rates from SuperRich Thailand\n")
        print(f"{'Name':<25} {'Code':<6} {'Buy':<12} {'Sell':<12}")
        print("-" * 60)
        for r in rates:
            print(f"{r['currency_name']:<25} {r['currency_code']:<6} {r['buying_rate']:<12} {r['selling_rate']:<12}")

        # Save to CSV + JSON
        df = pd.DataFrame(rates)
        df.to_csv("superrich_thailand_rates.csv", index=False, encoding="utf-8")
        df.to_json("superrich_thailand_rates.json", orient="records", force_ascii=False)

        print("\n💾 Saved superrich_thailand_rates.csv and superrich_thailand_rates.json")

    else:
        print("❌ Failed to scrape rates from SuperRich Thailand after retries.")
