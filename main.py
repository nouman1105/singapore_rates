from flask import Flask, jsonify, render_template_string
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import threading
import time

app = Flask(__name__)

# -----------------------
# Global cache
# -----------------------
CACHE = {"data": None, "last_updated": None}
CACHE_TTL = 60  # seconds

# -----------------------
# Scraper function
# -----------------------
def fetch_cashchanger_rates():
    url = "https://www.cashchanger.co/singapore"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        rates = {}
        rows = soup.select("table.table tbody tr")
        for row in rows[:10]:  # limit to top 10 currencies for demo
            cols = row.find_all("td")
            if len(cols) >= 3:
                currency = cols[0].get_text(strip=True)
                rate = cols[2].get_text(strip=True)
                rates[currency] = rate
        return rates
    except Exception as e:
        return {"error": str(e)}

# -----------------------
# Background updater
# -----------------------
def update_rates():
    while True:
        CACHE["data"] = fetch_cashchanger_rates()
        CACHE["last_updated"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        time.sleep(CACHE_TTL)

# Start background thread
threading.Thread(target=update_rates, daemon=True).start()

# -----------------------
# API endpoint
# -----------------------
@app.route("/api/rates")
def api_rates():
    return jsonify({
        "last_updated": CACHE["last_updated"],
        "rates": CACHE["data"]
    })

# -----------------------
# HTML Page
# -----------------------
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Currency Rates</title>
    <style>
        body { display:flex; justify-content:center; align-items:center; height:100vh; font-family:Arial; background:#f5f5f5; }
        #container { text-align:center; padding:20px; background:white; border-radius:10px; box-shadow:0 0 10px rgba(0,0,0,0.1);}
        table { margin:auto; border-collapse: collapse; }
        th, td { padding:8px 12px; border:1px solid #ccc; }
        th { background-color:#eee; }
        button { margin-top:10px; padding:6px 12px; }
    </style>
</head>
<body>
<div id="container">
    <h2>💱 Currency Rates (SGD)</h2>
    <p id="timestamp">Loading...</p>
    <table id="rates"></table>
    <button onclick="loadRates()">Refresh</button>
</div>

<script>
async function loadRates() {
    const res = await fetch("/api/rates");
    const data = await res.json();
    document.getElementById("timestamp").innerText = "Last updated: " + data.last_updated;
    let table = "<tr><th>Currency</th><th>Rate</th></tr>";
    if(data.rates.error) {
        table += `<tr><td colspan='2'>Error: ${data.rates.error}</td></tr>`;
    } else {
        for (const [cur, rate] of Object.entries(data.rates)) {
            table += `<tr><td>${cur}</td><td>${rate}</td></tr>`;
        }
    }
    document.getElementById("rates").innerHTML = table;
}

// Auto-refresh every 60 seconds
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
    app.run(host="0.0.0.0", port=5000)
