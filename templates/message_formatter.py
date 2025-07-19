import logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

def format_top_10_message(pairs: list, chain_name: str):
    """Memformat daftar 10 token teratas menjadi satu pesan besar."""
    if not pairs:
        return None

    # Mengatur zona waktu ke Waktu Indonesia Barat (WIB)
    tz_wib = pytz.timezone('Asia/Jakarta')
    now_wib = datetime.now(tz_wib)
    timestamp = now_wib.strftime("%d %B %Y, %H:%M:%S WIB")

    header = f"🏆 <b>Top 10 Trending - {chain_name.upper()}</b> 🏆\n"
    header += f"<i>Last Updated: {timestamp}</i>\n\n"

    message_parts = [header]

    for i, pair in enumerate(pairs[:10], 1):
        try:
            base_token = pair.get("baseToken", {})
            txns_24h = pair.get("txns", {}).get("h24", {})
            volume = pair.get("volume", {})
            price_change = pair.get("priceChange", {})

            name = base_token.get("name", "N/A")
            symbol = base_token.get("symbol", "N/A")
            address = base_token.get("address", "")
            
            buys = txns_24h.get("buys", 0)
            sells = txns_24h.get("sells", 0)
            
            volume_24h = volume.get("h24", 0)
            price_change_24h = price_change.get("h24", 0)
            dex_url = pair.get("url", "#")

            change_emoji = "📈" if price_change_24h >= 0 else "📉"
            
            part = (
                f"<b>{i}. {name} (${symbol})</b>\n"
                f"<code>{address}</code>\n"
                f"  • B/S (24h): {buys}/{sells}\n"
                f"  • Vol (24h): ${volume_24h:,.2f}\n"
                f"  • Change (24h): {change_emoji} {price_change_24h:.2f}%\n"
                f"  <a href='{dex_url}'>Lihat di DexScreener</a>\n"
            )
            message_parts.append(part)
        except Exception as e:
            logger.error(f"Error formatting part for {pair.get('pairAddress')}: {e}")
            continue
            
    return "\n".join(message_parts)

