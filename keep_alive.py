from flask import Flask
from threading import Thread
import os

app = Flask('')

@app.route('/')
def home():
    return "Bot attivo ✅"

def run():
    port = int(os.environ.get("PORT", 8080))  # Prende la porta da Render o usa 8080 di default
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
