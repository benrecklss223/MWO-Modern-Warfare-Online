import threading
from api import app
from bot import run_bot

def run_api():
    app.run(host="0.0.0.0", port=8080)

if __name__ == "__main__":
    threading.Thread(target=run_api, daemon=True).start()
    run_bot()
