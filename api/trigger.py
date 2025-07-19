import os
import json
import logging
import asyncio
from http.server import BaseHTTPRequestHandler
from telegram.ext import Application
from telegram.error import BadRequest
from services.api_client import fetch_trending_pairs
from templates.message_formatter import format_top_10_message

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
    CHANNEL_ID = os.environ['TELEGRAM_CHANNEL_ID']
    TRIGGER_SECRET = os.environ['TRIGGER_SECRET']
    
    # Konfigurasi baru yang menggabungkan Topic ID dan Message ID
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
    """Mengambil data, memformat, dan mengedit pesan yang sudah ada."""
    logging.info(f"Memproses rantai: {chain_id}")
    pairs = await fetch_trending_pairs(chain_id)
    if not pairs:
        logging.warning(f"Tidak ada data yang diterima untuk {chain_id}.")
        return

    # Format seluruh 10 token menjadi satu pesan besar
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
            logging.info(f"Pesan untuk {chain_id.upper()} berhasil diedit.")
        except BadRequest as e:
            # Error ini terjadi jika pesan tidak berubah. Ini normal dan bisa diabaikan.
            if "Message is not modified" in e.message:
                logging.info(f"Pesan untuk {chain_id.upper()} tidak berubah, tidak perlu diedit.")
            else:
                logging.error(f"Gagal mengedit pesan untuk {chain_id.upper()}: {e}")
        except Exception as e:
            logging.error(f"Error tidak terduga saat mengedit pesan untuk {chain_id.upper()}: {e}")

async def main_logic():
    """Fungsi async utama untuk menjalankan logika bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Jalankan semua proses secara bersamaan
    tasks = [process_chain(application.bot, chain, config) for chain, config in CHAINS_CONFIG.items()]
    await asyncio.gather(*tasks)

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
            logging.error(f"Error di handler utama: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'Server Error')
