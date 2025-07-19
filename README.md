# Bot Trending Token Telegram

Bot Telegram ini dirancang untuk memantau token yang sedang trending di berbagai jaringan blockchain melalui API eksternal dan mengirimkan pembaruan secara berkala ke topik spesifik di dalam sebuah grup atau channel Telegram.

---

## Arsitektur

Proyek ini menggunakan arsitektur **Hybrid** untuk menggabungkan keandalan Vercel dengan fleksibilitas pemicu eksternal, sehingga memungkinkan pembaruan yang sering tanpa memerlukan paket berbayar.

- **Vercel (Otak Bot):**  
  Menghosting semua logika utama aplikasi dalam bentuk serverless function. Vercel bertanggung jawab untuk mengambil data dari API, memformat pesan, dan mengirimkannya ke Telegram.

- **Termux (Pemicu Bot):**  
  Sebuah skrip Python ringan dijalankan di perangkat Android menggunakan Termux. Tugasnya hanya satu: memanggil (memicu) serverless function di Vercel pada interval waktu yang ditentukan (misalnya, setiap 2 menit).

---

## Fitur Utama

- **Multi-Jaringan:**  
  Memantau beberapa jaringan sekaligus (Ethereum, Base, Solana, BSC, Tron).

- **Pembaruan Efisien:**  
  Mengedit satu pesan yang sudah ada untuk setiap jaringan, bukan mengirim pesan baru setiap kali, sehingga channel tetap bersih.

- **Topik Spesifik:**  
  Mengirim pembaruan ke topik yang berbeda di dalam satu grup untuk setiap jaringan, menjaga agar informasi tetap terorganisir.

- **Format Pesan Informatif:**  
  Menampilkan 10 token teratas dengan detail penting seperti B/S (Buy/Sell) 24 jam, volume, dan perubahan harga.

- **Gratis & Andal:**  
  Berjalan menggunakan paket gratis Vercel dengan pemicu eksternal yang andal.

---

## Setup & Instalasi

### Prasyarat

- Node.js dan npm (untuk menginstal Vercel CLI)
- Python 3.9+ di komputer Anda
- Akun Vercel
- Akun Telegram
- Aplikasi Termux di Android (diinstal dari F-Droid)

---

### Bagian A: Setup di Vercel

1. **Clone Repositori Ini:**
    ```sh
    git clone https://URL_GITHUB_ANDA.git
    cd NAMA_FOLDER_PROYEK
    ```

2. **Instal Vercel CLI:**
    ```sh
    npm install -g vercel
    ```

3. **Login dan Hubungkan Proyek:**
    ```sh
    vercel login
    vercel link
    ```
    Ikuti instruksi untuk membuat proyek baru di Vercel.

4. **Atur Environment Variables:**  
   Ini adalah langkah paling penting. Gunakan file `.env.example` sebagai panduan. Jalankan perintah berikut untuk setiap variabel di bawah ini:
    ```sh
    vercel env add NAMA_VARIABEL NILAI_VARIABEL
    ```
    **Contoh:**
    ```sh
    vercel env add TELEGRAM_TOKEN "12345:ABCDEFG"
    ```

5. **Deploy Proyek:**
    ```sh
    vercel --prod
    ```
    Setelah selesai, salin URL produksi yang diberikan oleh Vercel (misalnya, `https://nama-proyek-anda.vercel.app`).

6. **Atur Webhook Telegram:**  
   Kunjungi URL berikut di browser Anda (ganti dengan data Anda) untuk mengaktifkan command `/start`:
    ```
    https://api.telegram.org/bot<TOKEN_ANDA>/setWebhook?url=<URL_VERCEL_ANDA>/api/webhook
    ```

---

### Bagian B: Setup Pemicu di Termux

1. **Instalasi di Termux:**
    ```sh
    pkg update && pkg upgrade -y
    pkg install python
    pip install requests
    ```

2. **Konfigurasi Pemicu:**
    - Salin file `trigger.py` dari repositori ini ke perangkat Android Anda.
    - Jalankan untuk pertama kali:
      ```sh
      python trigger.py
      ```
    - Skrip akan meminta Anda memasukkan URL Vercel (diakhiri dengan `/api/trigger`) dan Kunci Rahasia (`TRIGGER_SECRET`).
    - Konfigurasi akan disimpan secara otomatis di `config.json`.

3. **Jalankan di Latar Belakang:**
    ```sh
    termux-wake-lock
    python trigger.py
    ```

---
