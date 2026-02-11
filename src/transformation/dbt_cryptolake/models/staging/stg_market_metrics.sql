-- models/staging/stg_market_metrics.sql
-- Staging model for market metrics data

WITH source AS (
    SELECT * FROM {{ ref('stg_prices') }}
)

SELECT
    coin_id,
    price_date,
    price_usd,
    market_cap_usd,
    volume_24h_usd,
    price_change_pct_1d,

    -- Volume to market cap ratio (liquidity indicator)
    CASE
        WHEN market_cap_usd > 0
        THEN ROUND(volume_24h_usd / market_cap_usd * 100, 4)
        ELSE NULL
    END AS volume_to_mcap_pct

FROM source
WHERE market_cap_usd IS NOT NULL
