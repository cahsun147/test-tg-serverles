import os
import json
import logging
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from web3 import Web3
from web3.middleware import geth_poa_middleware
from telegram import Bot

# ==============================================================================
# KONFIGURASI & INISIALISASI
# ==============================================================================

# Mengatur logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Inisialisasi aplikasi Flask
app = Flask(__name__)

# Mengambil konfigurasi dari Environment Variables
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHANNEL_ID = os.environ.get('TELEGRAM_CHANNEL_ID')
CRON_SECRET = os.environ.get('VERCEL_CRON_SECRET') # Kunci rahasia untuk mengamankan endpoint

# Pastikan semua variabel penting ada
if not all([TELEGRAM_TOKEN, CHANNEL_ID, CRON_SECRET]):
    raise ValueError("Pastikan TELEGRAM_TOKEN, TELEGRAM_CHANNEL_ID, dan VERCEL_CRON_SECRET sudah diatur di Vercel.")

# Inisialisasi bot Telegram
bot = Bot(token=TELEGRAM_TOKEN)

# Konfigurasi untuk setiap jaringan blockchain
NETWORKS_CONFIG = {
    "ETH": {
        "rpc_url": os.environ.get('RPC_ETH', 'https://ethereum-rpc.publicnode.com'),
        "scan_api_key": os.environ.get('SCAN_KEY_ETH'),
        "scan_base_url": "https://api.etherscan.io/api",
        "explorer_base_url": "https://etherscan.io",
        "currency_symbol": "ETH",
        "poa": False,
        "topic_id": 3 # Ganti dengan ID topic di grup Anda
    },
    "BSC": {
        "rpc_url": os.environ.get('RPC_BSC', 'https://bsc-rpc.publicnode.com'), # RPC Anda sebelumnya salah, ini yang benar
        "scan_api_key": os.environ.get('SCAN_KEY_BSC'),
        "scan_base_url": "https://api.bscscan.com/api",
        "explorer_base_url": "https://bscscan.com",
        "currency_symbol": "BNB",
        "poa": True,
        "topic_id": 1953 # Ganti dengan ID topic di grup Anda
    },
    "BASE": {
        "rpc_url": os.environ.get('RPC_BASE', 'https://base-rpc.publicnode.com'),
        "scan_api_key": os.environ.get('SCAN_KEY_BASE'),
        "scan_base_url": "https://api.basescan.org/api",
        "explorer_base_url": "https://basescan.org",
        "currency_symbol": "ETH",
        "poa": True,
        "topic_id": 304 # Ganti dengan ID topic di grup Anda
    }
}

STATE_FILE = '/tmp/state.json'

# ==============================================================================
# FUNGSI-FUNGSI PEMBANTU (HELPERS)
# ==============================================================================

def load_state():
    """Memuat status terakhir dari file JSON."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_state(state):
    """Menyimpan status ke file JSON."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def get_web3_instance(network_config):
    """Membuat instance Web3 yang sudah dikonfigurasi."""
    w3 = Web3(Web3.HTTPProvider(network_config['rpc_url']))
    if network_config.get('poa', False):
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return w3

def check_is_token(w3, contract_address):
    """Memeriksa apakah sebuah kontrak memiliki fungsi totalSupply (indikator token)."""
    try:
        # Minimal ABI untuk ERC20/ERC721
        abi = [{"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "type": "function"}]
        contract = w3.eth.contract(address=contract_address, abi=abi)
        contract.functions.totalSupply().call()
        return True
    except Exception:
        return False

def get_token_details(w3, contract_address):
    """Mengambil detail dasar token (nama, simbol, supply, desimal)."""
    details = {"name": "Unknown", "symbol": "N/A", "totalSupply": 0, "decimals": 18}
    try:
        abi = [
            {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"}
        ]
        contract = w3.eth.contract(address=contract_address, abi=abi)
        details["name"] = contract.functions.name().call()
        details["symbol"] = contract.functions.symbol().call()
        details["totalSupply"] = contract.functions.totalSupply().call()
        details["decimals"] = contract.functions.decimals().call()
        details["totalSupply"] /= (10 ** details["decimals"])
    except Exception as e:
        logger.warning(f"Could not get full token details for {contract_address}: {e}")
    return details

def get_funder_and_age(deployer_address, network_config):
    """Mengambil alamat funder pertama dan umur deployer dari API scanner."""
    funder = "N/A"
    age_minutes = 0
    try:
        params = {
            "module": "account",
            "action": "txlist",
            "address": deployer_address,
            "startblock": 0,
            "endblock": 99999999,
            "sort": "asc",
            "apikey": network_config['scan_api_key']
        }
        response = requests.get(network_config['scan_base_url'], params=params)
        response.raise_for_status()
        data = response.json()

        if data.get('status') == '1' and data.get('result'):
            first_tx = data['result'][0]
            # Cari transaksi masuk pertama untuk menentukan funder
            for tx in data['result']:
                if tx['to'].lower() == deployer_address.lower():
                    funder = tx['from']
                    break
            
            first_tx_timestamp = int(first_tx['timeStamp'])
            age_seconds = datetime.now().timestamp() - first_tx_timestamp
            age_minutes = int(age_seconds / 60)

    except Exception as e:
        logger.error(f"Error getting funder/age for {deployer_address}: {e}")
    
    return funder, age_minutes

# ==============================================================================
# FUNGSI UTAMA PEMINDAI
# ==============================================================================

def process_new_contract(w3, tx, network_config):
    """Memproses satu transaksi pembuatan kontrak baru."""
    try:
        receipt = w3.eth.get_transaction_receipt(tx['hash'])
        if not receipt or not receipt.get('contractAddress'):
            return

        contract_address = receipt['contractAddress']
        deployer_address = tx['from']
        tx_hash = tx['hash'].hex()

        if not check_is_token(w3, contract_address):
            logger.info(f"Contract {contract_address} is not a token. Skipping.")
            return

        logger.info(f"New token found on {network_config['name']}: {contract_address}")

        # Mengumpulkan semua data
        token_details = get_token_details(w3, contract_address)
        deployer_balance_wei = w3.eth.get_balance(deployer_address)
        deployer_balance = Web3.from_wei(deployer_balance_wei, 'ether')
        funder, deployer_age = get_funder_and_age(deployer_address, network_config)

        # Membuat pesan
        explorer_url = network_config['explorer_base_url']
        message = (
            f"🚀 <b>New {network_config['name']} Token Deployment</b> 🚀\n\n"
            f"<b>{token_details['name']} ({token_details['symbol']})</b>\n"
            f"<code>{contract_address}</code>\n\n"
            f"<b>Token Details:</b>\n"
            f"<b>- Chain:</b> {network_config['name']}\n"
            f"<b>- Contract:</b> <a href='{explorer_url}/token/{contract_address}'>View Contract</a>\n"
            f"<b>- Total Supply:</b> {token_details['totalSupply']:,.2f}\n\n"
            f"<b>Deployer Details:</b>\n"
            f"<b>- Deployer:</b> <a href='{explorer_url}/address/{deployer_address}'>Deployer Address</a>\n"
            f"<b>- Balance:</b> {deployer_balance:.4f} {network_config['currency_symbol']}\n"
            f"<b>- Funded By:</b> <a href='{explorer_url}/address/{funder}'>Funder Address</a>\n"
            f"<b>- Deployer Age:</b> {deployer_age} minutes\n"
            f"<b>- Tx Hash:</b> <a href='{explorer_url}/tx/{tx_hash}'>View Transaction</a>"
        )

        # Mengirim pesan ke Telegram
        bot.send_message(
            chat_id=CHANNEL_ID,
            text=message,
            message_thread_id=network_config.get('topic_id'),
            parse_mode='HTML',
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"Failed to process transaction {tx['hash'].hex()}: {e}")


def scan_network(network_name, network_config):
    """Fungsi utama untuk memindai satu jaringan."""
    logger.info(f"Starting scan for {network_name}...")
    
    state = load_state()
    w3 = get_web3_instance(network_config)
    
    try:
        latest_block_num = w3.eth.block_number
        start_block = state.get(f"{network_name}_last_block", latest_block_num - 5) # Scan 5 blok terakhir jika state tidak ada
        
        logger.info(f"Scanning {network_name} from block {start_block + 1} to {latest_block_num}")

        for block_num in range(start_block + 1, latest_block_num + 1):
            block = w3.eth.get_block(block_num, full_transactions=True)
            for tx in block.transactions:
                if tx.to is None: # Ciri khas transaksi pembuatan kontrak
                    # Menambahkan nama jaringan ke config untuk digunakan di fungsi lain
                    process_new_contract(w3, tx, {"name": network_name, **network_config})
        
        # Update state dengan blok terakhir yang berhasil dipindai
        state[f"{network_name}_last_block"] = latest_block_num
        save_state(state)
        logger.info(f"Finished scan for {network_name}. Last block: {latest_block_num}")

    except Exception as e:
        logger.error(f"An error occurred during {network_name} scan: {e}")


# ==============================================================================
# ENDPOINT FLASK UNTUK CRON JOB
# ==============================================================================

@app.route('/api/cron', methods=['POST'])
def cron_handler():
    # Keamanan: Pastikan request datang dari Vercel Cron
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != f'Bearer {CRON_SECRET}':
        return jsonify({"status": "unauthorized"}), 401
    
    # Jalankan pemindaian untuk semua jaringan
    for name, config in NETWORKS_CONFIG.items():
        scan_network(name, config)
        
    return jsonify({"status": "ok"}), 200

@app.route('/')
def index():
    return 'Cron job handler is running.', 200
