-- models/marts/fact_price_hourly.sql
-- FACT TABLE: Hourly price metrics from real-time streaming data

{{ config(
    materialized='incremental',
    unique_key=['coin_id', 'price_hour'],
    incremental_strategy='merge'
) }}

WITH base AS (
    SELECT
        coin_id,
        DATE_TRUNC('hour', from_unixtime(trade_time_ms / 1000)) AS price_hour,
        price_usd,
        quantity,
        trade_time_ms
    FROM {{ source('bronze', 'realtime_prices') }}
    {% if is_incremental() %}
    WHERE from_unixtime(trade_time_ms / 1000) > (SELECT MAX(price_hour) FROM {{ this }})
    {% endif %}
),
hourly_agg AS (
    SELECT
        coin_id,
        price_hour,
        AVG(price_usd) OVER (PARTITION BY coin_id, price_hour) AS avg_price,
        MIN(price_usd) OVER (PARTITION BY coin_id, price_hour) AS min_price,
        MAX(price_usd) OVER (PARTITION BY coin_id, price_hour) AS max_price,
        SUM(quantity) OVER (PARTITION BY coin_id, price_hour) AS total_quantity,
        COUNT(*) OVER (PARTITION BY coin_id, price_hour) AS trade_count,
        FIRST_VALUE(price_usd) OVER (PARTITION BY coin_id, price_hour ORDER BY trade_time_ms) AS open_price,
        LAST_VALUE(price_usd) OVER (PARTITION BY coin_id, price_hour ORDER BY trade_time_ms ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS close_price
    FROM base
)
SELECT DISTINCT
    coin_id,
    price_hour,
    avg_price,
    min_price,
    max_price,
    open_price,
    close_price,
    total_quantity,
    trade_count,
    CURRENT_TIMESTAMP() AS _loaded_at
FROM hourly_agg
