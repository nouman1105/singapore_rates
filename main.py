from flask import Flask, jsonify, render_template_string
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import threading
import time
import os

app = Flask(__name__)

CACHE = {"data": None, "last_updated": None, "error": None}
CACHE_TTL = 60  # seconds

def fetch_cashchanger():
    url = "https://www.cashchanger.co/singapore"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        rates = {}
        rows = soup.select("table.table tbody tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 3:
                code = cols[0].get_text(strip=True)
                rate_text = cols[2].get_text(strip=True).replace(",", "")
                try:
                    rate = float(rate_text)
                    rates[code] = rate
                except ValueError:
                    continue

        if not rates:
            raise ValueError("No rates found on CashChanger")
        return rates, None
    except Exception as e:
        return None, f"CashChanger fetch failed: {e}"

def fetch_grandsuperrich():
    url = "https://www.grandsuperrich.com/exchange"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        rate_tag = soup.find("td", string="SGD 100")
        if rate_tag:
            rate_text = rate_tag.find_next("td").get_text(strip=True).replace(",", "")
            return float(rate_text), None
        return 1.0, "GrandSuperrich: SGD 100 rate not found, using 1.0"
    except Exception as e:
        return 1.0, f"GrandSuperrich fetch failed: {e}"

def update_rates():
    while True:
        cashchanger_rates, cash_err = fetch_cashchanger()
        grandsuperrich_rate, grand_err = fetch_grandsuperrich()

        if cash_err:
            CACHE["error"] = cash_err
            CACHE["data"] = None
        else:
            estimated_rates = {code: round(rate * grandsuperrich_rate, 6)
                               for code, rate in cashchanger_rates.items()}
            CACHE["data"] = estimated_rates
            CACHE["error"] = grand_err

        CACHE["last_updated"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        time.sleep(CACHE_TTL)

threading.Thread(target=update_rates, daemon=True).start()

@app.route("/api/estimated")
def api_estimated():
    return jsonify({
        "last_updated": CACHE["last_updated"],
        "rates": CACHE["data"],
        "error": CACHE["error"]
    })

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Estimated Currency Rates</title>
    <style>
        body { display:flex; justify-content:center; align-items:center; height:100vh; font-family:Arial; background:#f5f5f5; }
        #container { text-align:center; padding:20px; background:white; border-radius:10px; box-shadow:0 0 10px rgba(0,0,0,0.1);}
        table { margin:auto; border-collapse: collapse; }
        th, td { padding:8px 12px; border:1px solid #ccc; }
        th { background-color:#eee; }
        button { margin-top:10px; padding:6px 12px; }
        #error { color:red; font-weight:bold; }
    </style>
</head>
<body>
<div id="container">
    <h2>💱 Estimated Currency Rates (SGD)</h2>
    <p id="timestamp">Loading...</p>
    <p id="error"></p>
    <table id="rates"></table>
    <button onclick="loadRates()">Refresh</button>
</div>

<script>
async function loadRates() {
    const res = await fetch("/api/estimated");
    const data = await res.json();

    document.getElementById("timestamp").innerText = "Last updated: " + data.last_updated;

    const errorElem = document.getElementById("error");
    if(data.error){
        errorElem.innerText = data.error;
    } else {
        errorElem.innerText = "";
    }

    let table = "<tr><th>Currency</th><th>Rate (SGD)</th></tr>";
    if(data.rates){
        for (const [cur, rate] of Object.entries(data.rates)) {
            table += `<tr><td>${cur}</td><td>${rate}</td></tr>`;
        }
    } else if(data.error){
        table += `<tr><td colspan='2'>${data.error}</td></tr>`;
    } else {
        table += `<tr><td colspan='2'>No data available</td></tr>`;
    }

    document.getElementById("rates").innerHTML = table;
}

loadRates();
setInterval(loadRates, 60000);
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_PAGE)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
