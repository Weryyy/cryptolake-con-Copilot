-- tests/assert_positive_prices.sql
-- Test custom: Verifica que no hay precios negativos en la fact table.
SELECT
    coin_id,
    price_date,
    price_usd
FROM {{ ref('fact_market_daily') }}
WHERE price_usd <= 0
