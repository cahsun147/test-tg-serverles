import httpx
import logging
import asyncio
import time

logger = logging.getLogger(__name__)
BASE_API_URL = "https://www.grokonabase.xyz/test/dex"

# --- Konfigurasi untuk Percobaan Ulang Cerdas ---
TOTAL_WAIT_SECONDS = 30  # Total waktu maksimal untuk menunggu API (dalam detik)
RETRY_INTERVAL_SECONDS = 2 # Jeda antar percobaan

async def fetch_trending_pairs(chain_id: str, timeframe: str = "h24"):
    """
    Mengambil data trending dari API dengan logika menunggu dan percobaan ulang.
    Akan terus mencoba selama TOTAL_WAIT_SECONDS.
    """
    params = {"chainId": chain_id, "trendingscore": timeframe}
    start_time = time.time()

    while time.time() < start_time + TOTAL_WAIT_SECONDS:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(BASE_API_URL, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()
                
                # Cek apakah 'pairs' ada, merupakan list, dan tidak kosong
                if "pairs" in data and isinstance(data["pairs"], list) and data["pairs"]:
                    logger.info(f"SUKSES: Berhasil mengambil data untuk {chain_id.upper()}.")
                    return data["pairs"]
                
                # Jika API merespons OK tapi data kosong, tunggu dan coba lagi
                logger.warning(f"INFO: API untuk {chain_id.upper()} merespons OK tapi data belum siap. Mencoba lagi...")

        except (httpx.RequestError, ValueError) as e:
            logger.warning(f"PERINGATAN: Terjadi error sementara saat mengambil data {chain_id.upper()}: {e}. Mencoba lagi...")
        
        # Tunggu sebelum melakukan percobaan berikutnya
        await asyncio.sleep(RETRY_INTERVAL_SECONDS)

    # Jika loop selesai tanpa hasil
    logger.error(f"GAGAL TOTAL: Gagal mendapatkan data untuk {chain_id.upper()} setelah menunggu {TOTAL_WAIT_SECONDS} detik.")
    return []
