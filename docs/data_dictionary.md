# 📖 CryptoLake Data Dictionary

## Bronze Layer

### bronze.realtime_prices
Real-time trade data from Binance WebSocket.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| coin_id | STRING | NO | Cryptocurrency identifier (e.g., bitcoin, ethereum) |
| symbol | STRING | NO | Trading pair symbol (e.g., BTCUSDT) |
| price_usd | DOUBLE | NO | Trade price in USD |
| quantity | DOUBLE | YES | Trade quantity |
| trade_time_ms | BIGINT | NO | Trade timestamp in milliseconds (epoch) |
| event_time_ms | BIGINT | YES | Binance event timestamp in milliseconds |
| ingested_at | STRING | NO | ISO timestamp of ingestion |
| source | STRING | NO | Data source identifier |
| is_buyer_maker | BOOLEAN | YES | Whether the buyer was the market maker |

### bronze.historical_prices
Historical daily price data from CoinGecko API.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| coin_id | STRING | NO | Cryptocurrency identifier |
| timestamp_ms | BIGINT | NO | Price date timestamp in milliseconds |
| price_usd | DOUBLE | NO | Price in USD |
| market_cap_usd | DOUBLE | YES | Market capitalization in USD |
| volume_24h_usd | DOUBLE | YES | 24-hour trading volume in USD |
| _ingested_at | STRING | NO | Ingestion timestamp |
| _source | STRING | NO | Data source identifier |

### bronze.fear_greed_index
Crypto Fear & Greed Index from Alternative.me.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| value | INT | NO | Fear & Greed Index value (0-100) |
| classification | STRING | NO | Sentiment classification (Extreme Fear/Fear/Neutral/Greed/Extreme Greed) |
| timestamp | BIGINT | NO | Unix timestamp |
| time_until_update | STRING | YES | Seconds until next update |
| _ingested_at | STRING | NO | Ingestion timestamp |
| _source | STRING | NO | Data source identifier |

## Silver Layer

### silver.daily_prices
Cleaned and deduplicated daily prices.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| coin_id | STRING | NO | Cryptocurrency identifier |
| price_date | DATE | NO | Price date |
| price_usd | DOUBLE | NO | Daily price in USD |
| market_cap_usd | DOUBLE | YES | Market capitalization in USD |
| volume_24h_usd | DOUBLE | YES | 24-hour trading volume in USD |
| _processed_at | TIMESTAMP | NO | Processing timestamp |

### silver.fear_greed
Cleaned Fear & Greed Index data.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| fear_greed_value | INT | NO | Index value (0-100) |
| classification | STRING | NO | Sentiment classification |
| index_date | DATE | NO | Index date |
| _processed_at | TIMESTAMP | NO | Processing timestamp |

## Gold Layer (Star Schema)

### gold.fact_market_daily
Daily crypto market metrics fact table. Grain: 1 row = 1 coin × 1 day.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| coin_id | STRING | NO | Cryptocurrency identifier (FK to dim_coins) |
| price_date | DATE | NO | Price date (FK to dim_dates) |
| price_usd | DOUBLE | NO | Daily price in USD |
| market_cap_usd | DOUBLE | YES | Market capitalization |
| volume_24h_usd | DOUBLE | YES | Trading volume |
| price_change_pct_1d | DOUBLE | YES | Day-over-day price change % |
| moving_avg_7d | DOUBLE | YES | 7-day moving average |
| moving_avg_30d | DOUBLE | YES | 30-day moving average |
| volatility_7d | DOUBLE | YES | 7-day price volatility |
| avg_volume_7d | DOUBLE | YES | 7-day average volume |
| fear_greed_value | INT | YES | Fear & Greed Index |
| market_sentiment | STRING | YES | Sentiment classification |
| sentiment_score | INT | YES | Numeric sentiment (1-5) |
| ma30_signal | STRING | YES | Above/below 30d MA signal |
| _loaded_at | TIMESTAMP | NO | Load timestamp |

### gold.dim_coins
Cryptocurrency dimension with statistics.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| coin_id | STRING | NO | Cryptocurrency identifier (PK) |
| first_tracked_date | DATE | NO | First date tracked |
| last_tracked_date | DATE | NO | Last date tracked |
| total_days_tracked | INT | NO | Total days of data |
| all_time_low | DOUBLE | NO | Lowest price recorded |
| all_time_high | DOUBLE | NO | Highest price recorded |
| avg_price | DOUBLE | NO | Average price |
| avg_daily_volume | DOUBLE | YES | Average daily volume |
| price_range_pct | DOUBLE | NO | Price range as percentage |
| _loaded_at | TIMESTAMP | NO | Load timestamp |

### gold.dim_dates
Calendar dimension.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| date_day | DATE | NO | Calendar date (PK) |
| year | INT | NO | Year |
| month | INT | NO | Month (1-12) |
| day_of_month | INT | NO | Day of month (1-31) |
| day_of_week | INT | NO | Day of week (1-7) |
| week_of_year | INT | NO | ISO week number |
| quarter | INT | NO | Quarter (1-4) |
| is_weekend | BOOLEAN | NO | Weekend flag |
| day_name | STRING | NO | Day name (Monday, etc.) |
| month_name | STRING | NO | Month name (January, etc.) |
