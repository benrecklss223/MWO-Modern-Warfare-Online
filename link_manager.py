import json
import time
import secrets
import threading
from pathlib import Path

DATA_DIR = Path("link_api_data")
DATA_DIR.mkdir(exist_ok=True)

PENDING_CODES_FILE = DATA_DIR / "pending_codes.json"
LINKED_ACCOUNTS_FILE = DATA_DIR / "linked_accounts.json"
ROLE_SYNC_CONFIG_FILE = DATA_DIR / "role_rank_sync.json"

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6
CODE_EXPIRY_MINUTES = 10

lock = threading.Lock()


def load_json(path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True))


def cleanup_codes(codes):
    now = int(time.time())
    return {
        c: e for c, e in codes.items()
        if int(e.get("expires_at", 0)) > now
    }


def load_role_rank_sync():
    data = load_json(ROLE_SYNC_CONFIG_FILE)
    role_to_rank = data.get("role_to_rank", {}) if isinstance(data, dict) else {}

    normalized = {}
    for role_id, rank in role_to_rank.items():
        role_id_str = str(role_id).strip()
        rank_str = str(rank).strip()
        if role_id_str and rank_str:
            normalized[role_id_str] = rank_str

    return normalized


def create_code(minecraft_name, minecraft_uuid=""):
    if not minecraft_name:
        return {"ok": False, "error": "minecraft_name is required"}

    with lock:
        codes = cleanup_codes(load_json(PENDING_CODES_FILE))
        links = load_json(LINKED_ACCOUNTS_FILE)

        for v in links.values():
            if v["minecraft_name"].lower() == minecraft_name.lower():
                return {"ok": False, "error": "Already linked"}

        for c, e in list(codes.items()):
            if e["minecraft_name"].lower() == minecraft_name.lower():
                del codes[c]

        code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
        now = int(time.time())

        entry = {
            "minecraft_name": minecraft_name,
            "minecraft_uuid": minecraft_uuid,
            "created_at": now,
            "expires_at": now + CODE_EXPIRY_MINUTES * 60
        }

        codes[code] = entry
        save_json(PENDING_CODES_FILE, codes)

    return {"ok": True, "code": code, "expires_at": entry["expires_at"]}


def consume_code(code, discord_id, tag):
    with lock:
        codes = cleanup_codes(load_json(PENDING_CODES_FILE))
        links = load_json(LINKED_ACCOUNTS_FILE)

        if discord_id in links:
            return {"ok": False, "error": "Already linked"}

        entry = codes.get(code)
        if not entry:
            return {"ok": False, "error": "Invalid code"}

        link = {
            "minecraft_name": entry["minecraft_name"],
            "minecraft_uuid": entry.get("minecraft_uuid", ""),
            "linked_at": int(time.time()),
            "discord_tag": tag,
            "ftb_ranks": []
        }

        links[discord_id] = link
        del codes[code]

        save_json(LINKED_ACCOUNTS_FILE, links)
        save_json(PENDING_CODES_FILE, codes)

    return {"ok": True, "link": link}


def get_link(discord_id):
    links = load_json(LINKED_ACCOUNTS_FILE)
    return links.get(discord_id)


def get_link_by_minecraft_name(minecraft_name):
    links = load_json(LINKED_ACCOUNTS_FILE)
    for discord_id, entry in links.items():
        if entry.get("minecraft_name", "").lower() == minecraft_name.lower():
            return discord_id, entry
    return None, None


def unlink(discord_id):
    links = load_json(LINKED_ACCOUNTS_FILE)
    if discord_id not in links:
        return None

    removed = links.pop(discord_id)
    save_json(LINKED_ACCOUNTS_FILE, links)
    return removed


def update_linked_player_ranks(discord_id, ftb_ranks):
    links = load_json(LINKED_ACCOUNTS_FILE)
    link = links.get(discord_id)
    if not link:
        return None

    unique_ranks = sorted({str(rank).strip() for rank in ftb_ranks if str(rank).strip()})
    link["ftb_ranks"] = unique_ranks
    links[discord_id] = link
    save_json(LINKED_ACCOUNTS_FILE, links)
    return link
