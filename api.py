from flask import Flask, request, jsonify
from link_manager import create_code, consume_code, get_link, unlink

app = Flask(__name__)

API_KEY = "VbO+Mv!1bI0q7AVq"


def check_key():
    return request.headers.get("X-API-Key") == API_KEY


@app.before_request
def auth():
    if request.path == "/health":
        return
    if not check_key():
        return jsonify({"ok": False, "error": "Unauthorized"}), 401


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/link-codes")
def create():
    data = request.json or {}
    return create_code(data.get("minecraft_name"), data.get("minecraft_uuid"))


@app.post("/link-codes/consume")
def consume():
    data = request.json or {}
    return consume_code(
        data.get("code"),
        data.get("discord_user_id"),
        data.get("discord_tag")
    )


@app.get("/links/<discord_id>")
def get(discord_id):
    link = get_link(discord_id)
    if not link:
        return {"ok": False}, 404
    return {"ok": True, "link": link}


@app.delete("/links/<discord_id>")
def delete(discord_id):
    removed = unlink(discord_id)
    if not removed:
        return {"ok": False}, 404
    return {"ok": True}
