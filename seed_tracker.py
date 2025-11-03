# seed_tracker.py
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

# ---------- FUNZIONI DI SUPPORTO ----------
def get_server_value(item: dict):
    """Prova diversi nomi di campo per trovare il 'server'."""
    keys = ["server", "server_id", "serverId", "location", "region", "slot", "world", "shard"]
    for k in keys:
        if k in item and item[k]:
            return item[k]
    for v in item.values():
        if isinstance(v, dict):
            for k in keys:
                if k in v and v[k]:
                    return v[k]
    return "??"

def format_seed(item: dict) -> str:
    """Formatta le informazioni del seme in testo leggibile."""
    name = item.get("seed") or item.get("name") or "Sconosciuto"
    server = get_server_value(item)
    rarity = item.get("rarity") or item.get("rarity_level") or ""
    updated = item.get("updated") or item.get("time") or item.get("timestamp") or ""

    updated_str = ""
    if updated:
        try:
            updated_str = datetime.fromisoformat(str(updated).replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            updated_str = str(updated)

    parts = [f"🌱 **{name}**", f"Server `{server}`"]
    if rarity:
        parts.append(f"*{rarity}*")
    if updated_str:
        parts.append(f"aggiornato: {updated_str}")
    return " — ".join(parts)

# ---------- FETCH API ----------
async def fetch_seeds(session: aiohttp.ClientSession) -> list:
    try:
        async with session.get(API_URL, timeout=15) as resp:
            resp.raise_for_status()
            data = await resp.json()
            # salva la risposta grezza per debug
            with open(RAW_RESPONSE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            if isinstance(data, dict):
                for key in ("data", "seeds", "result", "items"):
                    if key in data and isinstance(data[key], list):
                        return data[key]
                for v in data.values():
                    if isinstance(v, list):
                        return v
                return []
            elif isinstance(data, list):
                return data
            else:
                return []
    except Exception as e:
        logging.error("Errore durante il fetch API: %s", e)
        return []

# ---------- INVIO SU DISCORD ----------
async def send_webhook(session: aiohttp.ClientSession, content: str):
    if not WEBHOOK_URL:
        logging.error("WEBHOOK_URL non impostato!")
        return
    payload = {"content": content}
    try:
        async with session.post(WEBHOOK_URL, json=payload) as resp:
            if resp.status in (200, 204):
                logging.info("✅ Messaggio inviato con successo.")
            else:
                text = await resp.text()
                logging.warning("⚠️ Errore nel webhook (%s): %s", resp.status, text)
    except Exception as e:
        logging.error("Errore invio webhook: %s", e)

# ---------- CALCOLO PROSSIMO CONTROLLO ----------
def seconds_until_next_check(now: datetime) -> int:
    """Prossimo multiplo di 5 minuti + 50 secondi."""
    minute = now.minute
    next_multiple = (math.floor(minute / 5) + 1) * 5
    if next_multiple >= 60:
        next_time = (now + timedelta(hours=1)).replace(minute=0, second=50, microsecond=0)
    else:
        next_time = now.replace(minute=next_multiple, second=50, microsecond=0)
        if next_time <= now:
            next_time = next_time + timedelta(minutes=5)
    return max(1, int((next_time - now).total_seconds()))

# ---------- MAIN LOOP ----------
async def main_loop():
    logging.info("🌿 Avvio tracker Grow a Garden (aggiornamento ogni 5m + 50s).")
    async with aiohttp.ClientSession() as session:
        while True:
            now = datetime.now(timezone.utc)
            wait = seconds_until_next_check(now)
            logging.info("⏳ Prossimo check tra %d secondi (UTC %s)", wait, now.strftime("%H:%M:%S"))
            await asyncio.sleep(wait)

            seeds = await fetch_seeds(session)
            if not seeds:
                logging.info("Nessun seme trovato nell’API.")
                continue

            lines = [format_seed(seed) for seed in seeds]
            max_lines = 25
            for i in range(0, len(lines), max_lines):
                chunk = lines[i:i + max_lines]
                message = "🌻 **Lista semi aggiornata!**\n" + "\n".join(chunk)
                await send_webhook(session, message)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logging.info("Interrotto manualmente.")
