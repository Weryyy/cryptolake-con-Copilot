-- models/intermediate/int_market_enriched.sql
-- Intermediate: market data enriched with Fear & Greed sentiment

WITH prices AS (
    SELECT * FROM {{ ref('int_price_daily_agg') }}
),

fear_greed AS (
    SELECT * FROM {{ ref('stg_fear_greed') }}
)

SELECT
    p.*,
    fg.fear_greed_value,
    fg.classification AS market_sentiment,
    fg.sentiment_score
FROM prices p
LEFT JOIN fear_greed fg
    ON p.price_date = fg.index_date
