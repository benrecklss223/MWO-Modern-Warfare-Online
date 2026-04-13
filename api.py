from flask import Flask, request, jsonify
from link_manager import (
    create_code,
    consume_code,
    get_link,
    get_link_by_minecraft_name,
    unlink,
)

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
        data.get("discord_tag"),
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


@app.get("/minecraft/<minecraft_name>/status")
def minecraft_status(minecraft_name):
    discord_id, link = get_link_by_minecraft_name(minecraft_name)
    if not link:
        return {"ok": True, "linked": False, "minecraft_name": minecraft_name}

    return {
        "ok": True,
        "linked": True,
        "discord_user_id": discord_id,
        "minecraft_name": link.get("minecraft_name", minecraft_name),
        "minecraft_uuid": link.get("minecraft_uuid", ""),
        "ftb_ranks": link.get("ftb_ranks", []),
    }
