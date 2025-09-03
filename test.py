from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
import re
import time


def scrape_superrich_thailand(url="https://www.superrichthailand.com/#!/en/exchange", retries=1):
    """
    Scrape exchange rates (currency name, code, buying, selling) from SuperRich Thailand.
    Filters out menu rows and only keeps rows with numeric rates.
    """
    for attempt in range(1, retries + 1):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=60000)

                # Wait for table content
                page.wait_for_selector("table", timeout=60000)
                page.screenshot(path="example.png")
                html = page.content()
                # page.pause()
                print(html)
                browser.close()
                return

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





def extract_exchange_rates():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Replace with the actual URL
        page.goto("https://www.superrichthailand.com/#!/en/exchange")

        # Step 1: Try table by ID
        table = page.query_selector("#print-table")

        # Step 2: Fallback to parent div by ID
        if not table:
            container = page.query_selector("#table-rate")
            if container:
                table = container.query_selector("table")

        # Step 3: Fallback to div with class 'printSection'
        if not table:
            container = page.query_selector(".printSection")
            if container:
                table = container.query_selector("table")

        if not table:
            raise Exception("Exchange rate table not found.")

        # Step 4: Process each tbody (each represents one currency block)
        tbodies = table.query_selector_all("tbody.ng-scope")
        result = []

        for tbody in tbodies:
            rows = tbody.query_selector_all("tr")
            if not rows:
                continue

            first_row = rows[0]
            country_cell = first_row.query_selector("td.first-col")
            if not country_cell:
                continue

            currency_code = country_cell.query_selector("span").inner_text().strip()
            country_name = country_cell.query_selector(".country-name").inner_text().strip()

            # Handle rowspan to determine how many denominations
            rowspan = int(country_cell.get_attribute("rowspan") or "1")

            for i, row in enumerate(rows):
                cells = row.query_selector_all("td")
                if i == 0:
                    # First row has 4 columns (Currency + Denom + Buy + Sell)
                    denom = cells[1].inner_text().strip()
                    buying = cells[2].inner_text().strip()
                    selling = cells[3].inner_text().strip()
                else:
                    # Other rows have 3 columns (Denom + Buy + Sell)
                    denom = cells[0].inner_text().strip()
                    buying = cells[1].inner_text().strip()
                    selling = cells[2].inner_text().strip()

                result.append({
                    "currency": currency_code if i == 0 else "",
                    "country": country_name if i == 0 else "",
                    "denomination": denom,
                    "buying_rate": buying,
                    "selling_rate": selling
                })

        browser.close()
        return result


# Run it and print nicely
if __name__ == "__main__":
    rates = extract_exchange_rates()
    for row in rates:
        print(row)
