from flask import Flask, render_template_string
from flask_socketio import SocketIO
import requests
from bs4 import BeautifulSoup
import eventlet
import time
import threading

# Needed for WebSockets in Flask-SocketIO on Render
eventlet.monkey_patch()

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# =======================
# Scraper Function
# =======================
def fetch_cashchanger_rates():
    url = "https://www.cashchanger.co/singapore"
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        rates = {}
        rows = soup.select("table.table tbody tr")
        for row in rows[:10]:  # limit to top 10 for demo
            cols = row.find_all("td")
            if len(cols) >= 3:
                currency = cols[0].get_text(strip=True)
                rate = cols[2].get_text(strip=True)
                rates[currency] = rate
        return {"source": "CashChanger", "rates": rates}
    except Exception as e:
        return {"source": "CashChanger", "error": str(e)}

# =======================
# Background Task
# =======================
def background_rate_updater():
    while True:
        data = fetch_cashchanger_rates()
        socketio.emit("rates_update", data)  # broadcast to all clients
        time.sleep(60)  # wait 60s before fetching again

# Start background thread
threading.Thread(target=background_rate_updater, daemon=True).start()

# =======================
# HTML Page with WebSocket
# =======================
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
  <title>Currency Rates</title>
  <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
  <style>
    body { display: flex; justify-content: center; align-items: center; height: 100vh; font-family: Arial; }
    #container { text-align: center; }
    table { margin: auto; border-collapse: collapse; }
    th, td { padding: 8px 12px; border: 1px solid #ccc; }
    th { background-color: #f2f2f2; }
  </style>
</head>
<body>
  <div id="container">
    <h2>💱 Live Currency Rates</h2>
    <p id="status">Waiting for data...</p>
    <table id="rates"></table>
  </div>

  <script>
    const socket = io();

    socket.on("connect", () => {
      document.getElementById("status").innerText = "Connected. Waiting for updates...";
    });

    socket.on("rates_update", (data) => {
      if (data.error) {
        document.getElementById("status").innerText = "[Error] " + data.error;
        return;
      }
      document.getElementById("status").innerText = "Source: " + data.source;
      let table = "<tr><th>Currency</th><th>Rate</th></tr>";
      for (const [cur, rate] of Object.entries(data.rates)) {
        table += `<tr><td>${cur}</td><td>${rate}</td></tr>`;
      }
      document.getElementById("rates").innerHTML = table;
    });
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
