import os
import logging
from flask import Flask, request
from telegram import Bot, Update, ParseMode
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

# Mengatur logging untuk mempermudah debugging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Mengambil token bot dari Vercel Environment Variables
TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("Pastikan Anda sudah mengatur TELEGRAM_TOKEN di Vercel Environment Variables!")

# Inisialisasi Bot dan Dispatcher
# Dispatcher adalah komponen utama yang akan menerima update dan mengarahkannya ke handler yang sesuai
bot = Bot(token=TOKEN)
dispatcher = Dispatcher(bot, None, use_context=True)

# Inisialisasi aplikasi web Flask
# Ini akan bertindak sebagai "pintu gerbang" untuk menerima webhook dari Telegram
app = Flask(__name__)

# === DEFINISI FUNGSI-FUNGSI COMMAND ===

def start_command(update: Update, context):
    """Fungsi ini dipanggil ketika pengguna mengirim command /start."""
    user = update.effective_user
    # 'reply_html' memungkinkan kita menggunakan format HTML sederhana seperti <b> untuk tebal
    update.message.reply_html(
        rf'Halo {user.mention_html()}! 👋',
        reply_markup=None,
    )
    update.message.reply_text(
        "Saya adalah bot contoh yang berjalan di Vercel Serverless. Coba kirim saya pesan apa saja!"
    )

def help_command(update: Update, context):
    """Fungsi ini dipanggil ketika pengguna mengirim command /help."""
    update.message.reply_text(
        "Berikut adalah perintah yang tersedia:\n"
        "/start - Memulai percakapan\n"
        "/help - Menampilkan pesan bantuan ini\n"
        "Kirim pesan apapun dan saya akan mengulanginya."
    )

def echo_message(update: Update, context):
    """Fungsi ini akan mengulang (echo) pesan teks yang dikirim oleh pengguna."""
    user_message = update.message.text
    update.message.reply_text(f"Anda berkata: {user_message}")

def unknown_command(update: Update, context):
    """Fungsi untuk menangani perintah yang tidak dikenal."""
    update.message.reply_text("Maaf, saya tidak mengerti perintah itu. Coba /help.")


# === PENDAFTARAN HANDLER KE DISPATCHER ===

# Menambahkan handler untuk setiap command
dispatcher.add_handler(CommandHandler("start", start_command))
dispatcher.add_handler(CommandHandler("help", help_command))

# Menambahkan handler untuk pesan teks biasa (bukan command)
# Filters.text memastikan handler ini hanya merespons pesan teks
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo_message))

# Menambahkan handler untuk command yang tidak dikenal
dispatcher.add_handler(MessageHandler(Filters.command, unknown_command))


# === ROUTE UNTUK FLASK APP ===

@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """Endpoint utama yang menerima update dari Telegram melalui metode POST."""
    if request.method == "POST":
        # Mengambil data JSON dari request yang dikirim Telegram
        json_data = request.get_json(force=True)
        
        # Membuat objek Update dari data JSON
        update = Update.de_json(json_data, bot)
        
        # Memproses update untuk memicu handler yang sesuai
        dispatcher.process_update(update)
        
    return 'ok', 200 # Memberi respons 'ok' ke Telegram

@app.route('/')
def index():
    """Halaman depan sederhana untuk memastikan server berjalan saat diakses via browser."""
    return 'Server bot aktif dan berjalan!'

# Catatan: Kode ini tidak akan berjalan jika dieksekusi langsung dengan `python api/index.py`
# karena Vercel akan mengelolanya sebagai serverless function.
