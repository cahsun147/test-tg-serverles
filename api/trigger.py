import os
import json
import logging
import asyncio
from http.server import BaseHTTPRequestHandler
from telegram.ext import Application
from telegram.error import BadRequest
from services.api_client import fetch_trending_pairs
from templates.message_formatter import format_top_10_message

# Mengatur format logging yang lebih bersih
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Mengatur level log untuk library lain agar tidak terlalu "berisik"
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

try:
    TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
    CHANNEL_ID = os.environ['TELEGRAM_CHANNEL_ID']
    TRIGGER_SECRET = os.environ['TRIGGER_SECRET']
    
    CHAINS_CONFIG = {
        "ethereum": {"topic_id": int(os.environ['TOPIC_ID_ETHEREUM']), "msg_id": int(os.environ['MSG_ID_ETHEREUM'])},
        "base":     {"topic_id": int(os.environ['TOPIC_ID_BASE']),     "msg_id": int(os.environ['MSG_ID_BASE'])},
        "solana":   {"topic_id": int(os.environ['TOPIC_ID_SOLANA']),   "msg_id": int(os.environ['MSG_ID_SOLANA'])},
        "bsc":      {"topic_id": int(os.environ['TOPIC_ID_BSC']),      "msg_id": int(os.environ['MSG_ID_BSC'])},
        "tron":     {"topic_id": int(os.environ['TOPIC_ID_TRON']),      "msg_id": int(os.environ['MSG_ID_TRON'])},
    }
except KeyError as e:
    raise ValueError(f"Environment variable {e} tidak diatur!")

async def process_chain(bot, chain_id, config):
    """
    Memproses satu rantai secara independen.
    Kegagalan di sini tidak akan menghentikan rantai lain.
    """
    try:
        pairs = await fetch_trending_pairs(chain_id)
        if not pairs:
            # Pesan error sudah ditangani oleh api_client, jadi cukup keluar
            return

        new_message_text = format_top_10_message(pairs, chain_id)
        
        if new_message_text:
            try:
                await bot.edit_message_text(
                    chat_id=CHANNEL_ID,
                    message_id=config["msg_id"],
                    text=new_message_text,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
                logger.info(f"SUKSES: Pesan untuk {chain_id.upper()} berhasil diedit.")
            except BadRequest as e:
                if "Message is not modified" in e.message:
                    logger.info(f"INFO: Pesan untuk {chain_id.upper()} tidak berubah, tidak perlu diedit.")
                else:
                    logger.error(f"GAGAL: Gagal mengedit pesan untuk {chain_id.upper()} karena BadRequest: {e}")
    except Exception as e:
        logger.error(f"FATAL: Terjadi error tak terduga saat memproses rantai {chain_id.upper()}: {e}")


async def main_logic():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Jalankan semua proses secara bersamaan. `return_exceptions=True` memastikan
    # bahwa kegagalan di satu tugas tidak akan menghentikan yang lain.
    tasks = [process_chain(application.bot, chain, config) for chain, config in CHAINS_CONFIG.items()]
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("--- Siklus pembaruan selesai ---")


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        auth_header = self.headers.get('Authorization')
        if not auth_header or auth_header != f'Bearer {TRIGGER_SECRET}':
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'Unauthorized')
            return

        try:
            asyncio.run(main_logic())
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'OK')
        except Exception as e:
            logger.error(f"FATAL: Error di handler utama: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'Server Error')
