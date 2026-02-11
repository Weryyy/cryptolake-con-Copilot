-- models/staging/stg_fear_greed.sql
WITH source AS (
    SELECT * FROM {{ source('silver', 'fear_greed') }}
)

SELECT
    fear_greed_value,
    classification,
    index_date,
    -- Clasificación numérica para análisis
    CASE classification
        WHEN 'Extreme Fear' THEN 1
        WHEN 'Fear' THEN 2
        WHEN 'Neutral' THEN 3
        WHEN 'Greed' THEN 4
        WHEN 'Extreme Greed' THEN 5
    END AS sentiment_score,
    _processed_at
FROM source
