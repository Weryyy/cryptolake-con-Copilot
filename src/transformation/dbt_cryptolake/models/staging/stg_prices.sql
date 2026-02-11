-- models/staging/stg_prices.sql
-- Staging layer: interfaz limpia sobre la capa Silver.

WITH source AS (
    SELECT * FROM {{ source('silver', 'daily_prices') }}
),

renamed AS (
    SELECT
        coin_id,
        price_date,
        price_usd,
        market_cap_usd,
        volume_24h_usd,
        _processed_at,

        -- Calculated fields
        LAG(price_usd) OVER (
            PARTITION BY coin_id ORDER BY price_date
        ) AS prev_day_price,

        ROW_NUMBER() OVER (
            PARTITION BY coin_id ORDER BY price_date DESC
        ) AS recency_rank

    FROM source
    WHERE price_usd > 0
)

SELECT
    *,
    CASE
        WHEN prev_day_price IS NOT NULL AND prev_day_price > 0
        THEN ROUND(((price_usd - prev_day_price) / prev_day_price) * 100, 4)
        ELSE NULL
    END AS price_change_pct_1d
FROM renamed
