import httpx
import logging

logger = logging.getLogger(__name__)
BASE_API_URL = "https://www.grokonabase.xyz/test/dex"

async def fetch_trending_pairs(chain_id: str, timeframe: str = "h24"):
    params = {"chainId": chain_id, "trendingscore": timeframe}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(BASE_API_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            if "pairs" in data and isinstance(data["pairs"], list):
                return data["pairs"]
            return []
    except httpx.RequestError as e:
        logger.error(f"API Error for {chain_id}: {e}")
        return []
    except ValueError:
        logger.error(f"JSON Decode Error for {chain_id}")
        return []
