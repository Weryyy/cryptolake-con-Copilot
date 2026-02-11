-- models/marts/dim_dates.sql
-- DIMENSION: Calendario con atributos útiles para análisis.

{{ config(materialized='table') }}

WITH date_spine AS (
    SELECT DISTINCT price_date AS date_day
    FROM {{ ref('stg_prices') }}
)

SELECT
    date_day,
    YEAR(date_day) AS year,
    MONTH(date_day) AS month,
    DAY(date_day) AS day_of_month,
    DAYOFWEEK(date_day) AS day_of_week,
    WEEKOFYEAR(date_day) AS week_of_year,
    QUARTER(date_day) AS quarter,

    -- Flags útiles para análisis
    CASE WHEN DAYOFWEEK(date_day) IN (1, 7) THEN TRUE ELSE FALSE END AS is_weekend,

    -- Formato legible
    DATE_FORMAT(date_day, 'EEEE') AS day_name,
    DATE_FORMAT(date_day, 'MMMM') AS month_name

FROM date_spine
