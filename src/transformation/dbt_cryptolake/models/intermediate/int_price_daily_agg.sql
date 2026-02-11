-- models/intermediate/int_price_daily_agg.sql
-- Intermediate: daily price aggregation with rolling metrics

WITH daily_prices AS (
    SELECT * FROM {{ ref('stg_prices') }}
),

enriched AS (
    SELECT
        coin_id,
        price_date,
        price_usd,
        market_cap_usd,
        volume_24h_usd,
        price_change_pct_1d,

        -- Rolling averages
        AVG(price_usd) OVER (
            PARTITION BY coin_id
            ORDER BY price_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS moving_avg_7d,

        AVG(price_usd) OVER (
            PARTITION BY coin_id
            ORDER BY price_date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) AS moving_avg_30d,

        -- Volatility (7-day standard deviation)
        STDDEV(price_usd) OVER (
            PARTITION BY coin_id
            ORDER BY price_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS volatility_7d,

        -- Average volume 7d
        AVG(volume_24h_usd) OVER (
            PARTITION BY coin_id
            ORDER BY price_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS avg_volume_7d

    FROM daily_prices
)

SELECT * FROM enriched
