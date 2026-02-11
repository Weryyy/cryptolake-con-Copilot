-- tests/assert_no_future_dates.sql
-- Test custom: Verifica que no hay fechas futuras en la fact table.
SELECT
    coin_id,
    price_date,
    price_usd
FROM {{ ref('fact_market_daily') }}
WHERE price_date > CURRENT_DATE()
