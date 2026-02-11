-- models/marts/dim_coins.sql
-- DIMENSION: Información estática de cada criptomoneda.
-- Type 1 SCD (se sobrescribe con nuevos datos).

{{ config(
    materialized='table',
    unique_key='coin_id'
) }}

WITH coin_stats AS (
    SELECT
        coin_id,
        MIN(price_date) AS first_tracked_date,
        MAX(price_date) AS last_tracked_date,
        COUNT(DISTINCT price_date) AS total_days_tracked,
        MIN(price_usd) AS all_time_low,
        MAX(price_usd) AS all_time_high,
        AVG(price_usd) AS avg_price,
        AVG(volume_24h_usd) AS avg_daily_volume
    FROM {{ ref('stg_prices') }}
    GROUP BY coin_id
)

SELECT
    coin_id,
    -- Metadata de tracking
    first_tracked_date,
    last_tracked_date,
    total_days_tracked,
    -- Price stats
    all_time_low,
    all_time_high,
    avg_price,
    avg_daily_volume,
    -- Calculated
    ROUND(((all_time_high - all_time_low) / all_time_low) * 100, 2) AS price_range_pct,
    CURRENT_TIMESTAMP() AS _loaded_at
FROM coin_stats
