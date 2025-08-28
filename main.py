import asyncio
from flask import Flask, render_template_string, jsonify
from playwright.async_api import async_playwright
import time

app = Flask(__name__)

# cache to avoid hammering sites
CACHE = {"data": None, "timestamp": 0}


async def fetch_cashchanger(page):
    await page.goto("https://cashchanger.co/singapore", timeout=60000)
    await page.wait_for_selector("table")
    rows = await page.query_selector_all("table tr")

    rates = []
    for row in rows[1:]:
        cols = await row.query_selector_all("td")
        if len(cols) >= 3:
            currency = (await cols[0].inner_text()).strip()
            buy = (await cols[1].inner_text()).strip()
            sell = (await cols[2].inner_text()).strip()
            rates.append({"currency": currency, "buy": buy, "sell": sell})
    return {"source": "CashChanger", "rates": rates}


async def fetch_grandsuperrich(page):
    await page.goto("https://www.grandsuperrich.com/exchange", timeout=60000)
    await page.wait_for_selector("table")
    rows = await page.query_selector_all("table tr")

    rates = []
    for row in rows[1:]:
        cols = await row.query_selector_all("td")
        if len(cols) >= 3:
            currency = (await cols[0].inner_text()).strip()
            buy = (await cols[1].inner_text()).strip()
            sell = (await cols[2].inner_text()).strip()
            rates.append({"currency": currency, "buy": buy, "sell": sell})
    return {"source": "GrandSuperrich", "rates": rates}


async def fetch_all():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        results = []
        try:
            results.append(await fetch_cashchanger(page))
        except Exception as e:
            results.append({"source": "CashChanger", "error": str(e)})
        try:
            results.append(await fetch_grandsuperrich(page))
        except Exception as e:
            results.append({"source": "GrandSuperrich", "error": str(e)})
        await browser.close()
        return results


def get_rates():
    now = time.time()
    if CACHE["data"] and now - CACHE["timestamp"] < 60:
        return CACHE["data"]

    data = asyncio.run(fetch_all())
    CACHE["data"] = data
    CACHE["timestamp"] = now
    return data


@app.route("/")
def index():
    return render_template_string("""
    <html>
    <head>
        <title>Exchange Rates</title>
        <style>
            body { font-family: Arial; margin: 20px; }
            table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: center; }
            th { background: #f4f4f4; }
        </style>
    </head>
    <body>
        <h1>Live Exchange Rates</h1>
        <div id="rates"></div>

        <script>
            async function loadRates() {
                const res = await fetch("/rates");
                const data = await res.json();
                let html = "";
                data.forEach(src => {
                    html += `<h2>${src.source}</h2>`;
                    if (src.error) {
                        html += `<p style="color:red">Error: ${src.error}</p>`;
                    } else {
                        html += "<table><tr><th>Currency</th><th>Buy</th><th>Sell</th></tr>";
                        src.rates.forEach(r => {
                            html += `<tr><td>${r.currency}</td><td>${r.buy}</td><td>${r.sell}</td></tr>`;
                        });
                        html += "</table>";
                    }
                });
                document.getElementById("rates").innerHTML = html;
            }
            loadRates();
            setInterval(loadRates, 60000);
        </script>
    </body>
    </html>
    """)


@app.route("/rates")
def rates():
    return jsonify(get_rates())


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)
