import os
import json
import logging
import asyncio
from http.server import BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    TOKEN = os.environ['TELEGRAM_TOKEN']
except KeyError:
    raise ValueError("Environment variable TELEGRAM_TOKEN tidak diatur!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('aktif')

application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))

async def main_webhook(update_data):
    async with application:
        await application.process_update(
            Update.de_json(update_data, application.bot)
        )

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_len = int(self.headers.get('Content-Length'))
            body = self.rfile.read(content_len)
            update_json = json.loads(body.decode('utf-8'))
            
            asyncio.run(main_webhook(update_json))
            
            self.send_response(200)
            self.end_headers()
        except Exception as e:
            logging.error(f"Error di webhook handler: {e}")
            self.send_response(500)
            self.end_headers()
