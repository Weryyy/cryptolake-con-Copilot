"""
Extractor de datos históricos desde CoinGecko API.

CoinGecko free tier: 30 calls/min, sin API key.
Endpoint: /coins/{id}/market_chart para obtener price, market_cap y volume históricos.

Para ejecutar:
    python -m src.ingestion.batch.coingecko_extractor
"""
import time
from typing import Any, List, Dict

import structlog

from src.config.settings import settings
from src.ingestion.batch.base_extractor import BaseExtractor

logger = structlog.get_logger()


class CoinGeckoExtractor(BaseExtractor):
    """Extrae precios históricos y métricas de mercado de CoinGecko."""

    def __init__(self, days: int = 90):
        super().__init__(source_name="coingecko")
        self.days = days
        self.base_url = settings.coingecko_base_url

    def extract(self) -> List[Dict[str, Any]]:
        """
        Extrae datos históricos de todos los coins configurados.

        Para cada coin obtiene precios, market cap y volumen.
        Respeta rate limiting con sleep entre requests.
        """
        all_records: List[Dict[str, Any]] = []

        for i, coin_id in enumerate(settings.tracked_coins):
            max_retries = 3
            success = False

            for attempt in range(max_retries):
                try:
                    logger.info(
                        "extracting_coin",
                        coin=coin_id,
                        progress=f"{i+1}/{len(settings.tracked_coins)}",
                        attempt=attempt + 1,
                    )

                    # Respetar rate limit de la API gratuita (30 calls/min)
                    import time
                    if attempt == 0:
                        time.sleep(2.0)
                    else:
                        time.sleep(10.0 * attempt)

                    response = self.session.get(
                        f"{self.base_url}/coins/{coin_id}/market_chart",
                        params={
                            "vs_currency": "usd",
                            "days": str(self.days),
                            "interval": "daily",
                        },
                        timeout=30,
                    )

                    if response.status_code == 429:
                        logger.warning("rate_limit_hit",
                                       coin=coin_id, attempt=attempt+1)
                        continue

                    response.raise_for_status()
                    data = response.json()

                    prices = data.get("prices", [])
                    market_caps = data.get("market_caps", [])
                    volumes = data.get("total_volumes", [])

                    for idx, price_point in enumerate(prices):
                        timestamp_ms, price = price_point
                        all_records.append({
                            "coin_id": coin_id,
                            "timestamp_ms": int(timestamp_ms),
                            "price_usd": float(price),
                            "market_cap_usd": float(market_caps[idx][1]) if idx < len(market_caps) else None,
                            "volume_24h_usd": float(volumes[idx][1]) if idx < len(volumes) else None,
                        })

                    logger.info("coin_extracted", coin=coin_id,
                                datapoints=len(prices))
                    success = True
                    break

                except Exception as e:
                    logger.error("extraction_attempt_failed",
                                 coin=coin_id, attempt=attempt+1, error=str(e))
                    if attempt == max_retries - 1:
                        logger.error(
                            "coin_extraction_final_failure", coin=coin_id)

            if not success:
                continue

        return all_records

    def validate(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Valida que los precios sean positivos y los timestamps válidos."""
        valid = []
        invalid_count = 0

        for record in data:
            price = record.get("price_usd")
            timestamp = record.get("timestamp_ms")
            coin = record.get("coin_id")

            if (
                coin
                and price is not None
                and price > 0
                and timestamp is not None
                and timestamp > 0
            ):
                valid.append(record)
            else:
                invalid_count += 1
                if invalid_count <= 3:
                    logger.warning("invalid_record_dropped", record=record)

        if invalid_count > 3:
            logger.warning(
                "additional_invalid_records",
                count=invalid_count - 3,
            )

        return valid


if __name__ == "__main__":
    extractor = CoinGeckoExtractor(days=90)
    records = extractor.run()

    if records:
        coins = set(r["coin_id"] for r in records)
        print(f"\n📊 Resumen de extracción:")
        print(f"   Total registros: {len(records)}")
        print(f"   Coins extraídos: {len(coins)}")
        for coin in sorted(coins):
            coin_records = [r for r in records if r["coin_id"] == coin]
            print(f"   - {coin}: {len(coin_records)} datapoints")
    else:
        print("⚠️  No se extrajeron datos")
