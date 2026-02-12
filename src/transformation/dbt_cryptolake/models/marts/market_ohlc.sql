-- Market OHLC (Open, High, Low, Close) aggregations
{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key=['coin_id', 'bucket_start', 'timeframe'],
    partition_by=['timeframe'],
    cluster_by=['coin_id']
) }}

WITH base_prices AS (
    SELECT 
        coin_id,
        price_usd,
        volume_24h_usd,
        _spark_ingested_at as processed_at
    FROM {{ source('bronze', 'realtime_prices') }}
    {% if is_incremental() %}
        WHERE _spark_ingested_at > (SELECT max(processed_at) FROM {{ this }})
    {% endif %}
),

timeframes AS (
    SELECT 
        coin_id,
        price_usd,
        volume_24h_usd,
        processed_at,
        -- Generate buckets for different timeframes
        date_trunc('hour', processed_at) as hour_bucket,
        date_trunc('day', processed_at) as day_bucket
    FROM base_prices
),

hourly_ohlc AS (
    SELECT
        coin_id,
        hour_bucket as bucket_start,
        '1h' as timeframe,
        FIRST_VALUE(price_usd) OVER (PARTITION BY coin_id, hour_bucket ORDER BY processed_at) as open,
        MAX(price_usd) OVER (PARTITION BY coin_id, hour_bucket) as high,
        MIN(price_usd) OVER (PARTITION BY coin_id, hour_bucket) as low,
        LAST_VALUE(price_usd) OVER (PARTITION BY coin_id, hour_bucket ORDER BY processed_at ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as close,
        SUM(volume_24h_usd) OVER (PARTITION BY coin_id, hour_bucket) as volume,
        MAX(processed_at) as processed_at
    FROM timeframes
    GROUP BY 1, 2, 3, price_usd, volume_24h_usd, processed_at
)

SELECT DISTINCT * FROM hourly_ohlc
