# seed_webhook_tracker.py
import os
import asyncio
import aiohttp
import json
import math
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import logging

# ---------------- CONFIG ----------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
load_dotenv()
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
API_URL = os.getenv("API_URL", "https://gagapi.onrender.com/seeds")
RAW_RESPONSE_FILE = "last_response.json"
# ----------------------------------------

# -------- utility --------
def get_server_value(item: dict):
    """Trova il campo server anche se si chiama in modo diverso."""
    for key in ["server", "server_id", "serverId", "location", "region", "slot", "world", "shard"]:
        if key in item and item[key]:
            return item[key]
    for v in item.values():
        if isinstance(v, dict):
            for key in ["server", "server_id", "serverId", "location", "region", "slot", "world", "shard"]:
                if key in v and v[key]:
                    return v[key]
    return "??"

def format_seed(item: dict) -> str:
    """Crea una stringa leggibile per ogni seme."""
    seed = item.get("seed") or item.get("name") or "Sconosciuto"
    server = get_server_value(item)
    rarity = item.get("rarity") or item.get("rarity_level") or ""
    updated = item.get("updated") or item.get("time") or item.get("timestamp") or ""
    time_str = ""
    if updated:
        try:
            time_str = datetime.fromisoformat(str(updated).replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            time_str = str(updated)
    extras = []
    if item.get("price"):
        extras.append(f"price: {item.get('price')}")
    if item.get("variant"):
        extras.append(f"variant: {item.get('variant')}")
    parts = [f"🌱 **{seed}**", f"Server `{server}`"]
    if rarity:
        parts.append(f"*{rarity}*")
    if time_str:
        parts.append(f"aggiornato