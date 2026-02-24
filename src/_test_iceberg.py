"""Test completo de acceso a Iceberg desde la API."""

from datetime import UTC, datetime, timedelta

import pyarrow.compute as pc

from src.serving.api.utils import get_iceberg_catalog, load_fresh_table

now = datetime.now(UTC)
print(f"System UTC: {now}")
print("=" * 60)

# Test 1: Catálogo y tablas disponibles
print("\n[1] Tablas disponibles:")
cat = get_iceberg_catalog()
for ns in cat.list_namespaces():
    ns_name = ns[0]
    for tbl in cat.list_tables(ns_name):
        print(f"  {tbl[0]}.{tbl[1]}")

# Test 2: load_fresh_table + refresh
print("\n[2] load_fresh_table('silver.realtime_vwap'):")
try:
    table = load_fresh_table("silver.realtime_vwap")
    snap = table.current_snapshot()
    print(f"  Snapshot ID: {snap.snapshot_id if snap else 'NONE'}")
    print(f"  Snapshot TS: {snap.timestamp_ms if snap else 'N/A'}")
except Exception as e:
    print(f"  FAIL: {type(e).__name__}: {e}")

# Test 3: row_filter con formato ISO-8601
print("\n[3] Scan con row_filter ISO-8601:")
since_iso = (now - timedelta(hours=4)).isoformat()
print(f"  Filter: window_start >= '{since_iso}'")
try:
    df = table.scan(row_filter=f"window_start >= '{since_iso}'").to_arrow()
    print(f"  Rows: {len(df)}")
    if len(df) > 0:
        max_ts = pc.max(df["window_start"]).as_py()
        print(f"  Max window_start: {max_ts}")
        lag = (now - max_ts).total_seconds()
        print(f"  Lag: {lag:.1f} seconds")
except Exception as e:
    print(f"  FAIL: {type(e).__name__}: {e}")

# Test 4: row_filter con formato simple (el que fallaba antes)
print("\n[4] Scan con row_filter strftime (formato viejo):")
since_old = (now - timedelta(hours=4)).strftime("%Y-%m-%d %H:%M:%S")
print(f"  Filter: window_start >= '{since_old}'")
try:
    df2 = table.scan(row_filter=f"window_start >= '{since_old}'").to_arrow()
    print(f"  Rows: {len(df2)}")
except Exception as e:
    print(f"  FAIL: {type(e).__name__}: {e}")

# Test 5: Scan sin filtro
print("\n[5] Scan sin filtro:")
try:
    df_all = table.scan().to_arrow()
    print(f"  Total rows: {len(df_all)}")
    max_all = pc.max(df_all["window_start"]).as_py()
    print(f"  Max window_start: {max_all}")
    lag_all = (now - max_all).total_seconds()
    print(f"  Lag: {lag_all:.1f} seconds")
except Exception as e:
    print(f"  FAIL: {type(e).__name__}: {e}")

# Test 6: Bronze realtime
print("\n[6] Bronze realtime_prices:")
try:
    b_table = load_fresh_table("bronze.realtime_prices")
    b_df = b_table.scan().to_arrow()
    b_max = pc.max(b_df["_spark_ingested_at"]).as_py()
    print(f"  Rows: {len(b_df)}")
    print(f"  Max _spark_ingested_at: {b_max}")
    print(f"  Lag: {(now - b_max).total_seconds():.1f} seconds")
except Exception as e:
    print(f"  FAIL: {type(e).__name__}: {e}")

# Test 7: Gold fact_market_daily
print("\n[7] Gold fact_market_daily:")
try:
    g_table = load_fresh_table("gold.fact_market_daily")
    g_df = g_table.scan().to_arrow()
    print(f"  Rows: {len(g_df)}")
    coins = set(g_df["coin_id"].to_pylist())
    print(f"  Coins: {coins}")
except Exception as e:
    print(f"  FAIL: {type(e).__name__}: {e}")

# Test 8: Refresh produce datos más frescos?
print("\n[8] Test refresh vs no-refresh:")
try:
    import time

    t1 = cat.load_table("silver.realtime_vwap")
    snap1 = t1.current_snapshot().snapshot_id
    time.sleep(2)
    t1.refresh()
    snap2 = t1.current_snapshot().snapshot_id
    print(f"  Before refresh: {snap1}")
    print(f"  After refresh:  {snap2}")
    print(f"  Changed: {snap1 != snap2}")
except Exception as e:
    print(f"  FAIL: {type(e).__name__}: {e}")

print("\n" + "=" * 60)
print("DONE")
