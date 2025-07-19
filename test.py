import time
import logging
import requests
import json
import os

# ==============================================================================
# KODE UTAMA (TIDAK PERLU DIEDIT)
# ==============================================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
CONFIG_FILE = "config.json"

def get_config():
    """Membaca konfigurasi dari file atau memintanya dari pengguna."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                if "VERCEL_HANDLER_URL" in config and "YOUR_SECRET_KEY" in config:
                    return config
        except json.JSONDecodeError:
            logging.error("File config.json rusak. Akan membuat yang baru.")
    
    # Jika file tidak ada atau rusak, minta input dari pengguna
    print("--- Konfigurasi Pertama Kali ---")
    url = input("Masukkan URL Vercel Anda (diakhiri dengan /api/trigger): ")
    secret = input("Masukkan Kunci Rahasia (TRIGGER_SECRET) Anda: ")
    
    config = {
        "VERCEL_HANDLER_URL": url.strip(),
        "YOUR_SECRET_KEY": secret.strip(),
        "CHECK_INTERVAL_SECONDS": 120  # Default 2 menit
    }
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
    
    print(f"Konfigurasi telah disimpan di {CONFIG_FILE}. Anda bisa mengedit file ini nanti jika perlu.")
    return config

def trigger_vercel_function(config):
    """Mengirim request untuk memicu fungsi Vercel."""
    url = config["VERCEL_HANDLER_URL"]
    secret = config["YOUR_SECRET_KEY"]
    headers = {'Authorization': f'Bearer {secret}'}
    
    try:
        logging.info(f"Memicu fungsi di Vercel...")
        response = requests.get(url, headers=headers, timeout=20)
        
        if response.status_code == 200:
            logging.info("Berhasil memicu fungsi. Status: OK.")
        else:
            logging.error(f"Gagal memicu. Status: {response.status_code}, Pesan: {response.text}")
            
    except requests.RequestException as e:
        logging.error(f"Error saat request: {e}")

def main():
    """Loop utama untuk memicu fungsi secara berkala."""
    config = get_config()
    interval = config.get("CHECK_INTERVAL_SECONDS", 120)
    
    logging.info("Skrip pemicu dimulai.")
    while True:
        trigger_vercel_function(config)
        logging.info(f"Menunggu {interval} detik...")
        time.sleep(interval)

if __name__ == "__main__":
    main()
