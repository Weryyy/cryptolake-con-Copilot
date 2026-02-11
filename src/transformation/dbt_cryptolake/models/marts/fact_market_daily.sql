-- models/marts/fact_market_daily.sql
-- FACT TABLE: Métricas de mercado diarias por coin.
-- Grain: 1 row = 1 coin × 1 día.

{{ config(
    materialized='incremental',
    unique_key=['coin_id', 'price_date'],
    incremental_strategy='merge'
) }}

WITH prices AS (
    SELECT * FROM {{ ref('stg_prices') }}
    {% if is_incremental() %}
    WHERE price_date > (SELECT MAX(price_date) FROM {{ this }})
    {% endif %}
),

fear_greed AS (
    SELECT * FROM {{ ref('stg_fear_greed') }}
),

enriched AS (
    SELECT
        p.coin_id,
        p.price_date,
        p.price_usd,
        p.market_cap_usd,
        p.volume_24h_usd,
        p.price_change_pct_1d,

        -- Rolling averages (indicadores técnicos básicos)
        AVG(p.price_usd) OVER (
            PARTITION BY p.coin_id
            ORDER BY p.price_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS moving_avg_7d,

        AVG(p.price_usd) OVER (
            PARTITION BY p.coin_id
            ORDER BY p.price_date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) AS moving_avg_30d,

        -- Volatilidad (desviación estándar 7 días)
        STDDEV(p.price_usd) OVER (
            PARTITION BY p.coin_id
            ORDER BY p.price_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS volatility_7d,

        -- Volume trend
        AVG(p.volume_24h_usd) OVER (
            PARTITION BY p.coin_id
            ORDER BY p.price_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS avg_volume_7d,

        -- Fear & Greed del día
        fg.fear_greed_value,
        fg.classification AS market_sentiment,
        fg.sentiment_score,

        -- Signal: ¿está por encima de la media de 30d?
        CASE
            WHEN p.price_usd > AVG(p.price_usd) OVER (
                PARTITION BY p.coin_id
                ORDER BY p.price_date
                ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
            ) THEN 'ABOVE_MA30'
            ELSE 'BELOW_MA30'
        END AS ma30_signal

    FROM prices p
    LEFT JOIN fear_greed fg
        ON p.price_date = fg.index_date
)

SELECT
    coin_id,
    price_date,
    price_usd,
    market_cap_usd,
    volume_24h_usd,
    price_change_pct_1d,
    moving_avg_7d,
    moving_avg_30d,
    volatility_7d,
    avg_volume_7d,
    fear_greed_value,
    market_sentiment,
    sentiment_score,
    ma30_signal,
    CURRENT_TIMESTAMP() AS _loaded_at
FROM enriched
