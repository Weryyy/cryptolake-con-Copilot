import json
import os
import time

import great_expectations as gx

from src.serving.api.utils import get_iceberg_catalog, get_redis_client


def validate_table(table_name, suite_name):
    """
    Ejecuta validaciones de Great Expectations sobre una tabla de Iceberg.
    """
    print(f"🔍 Iniciando validación de DQ para: {table_name}")
    catalog = get_iceberg_catalog()
    redis = get_redis_client()

    try:
        # 1. Cargar datos de la tabla (usamos una muestra para validación rápida)
        table = catalog.load_table(table_name)
        df = table.scan().to_arrow().to_pandas()

        if df.empty:
            print(f"⚠️ Tabla {table_name} vacía. Saltando validación.")
            return False

        # 2. Configurar GX
        context = gx.get_context()

        # Cargar la suite de expectativas
        suite_path = f"src/quality/expectations/{suite_name}.json"
        if not os.path.exists(suite_path):
            print(f"❌ No se encontró la suite: {suite_path}")
            return False

        with open(suite_path) as f:
            suite_dict = json.load(f)
            # Simplificamos para el PoC: Usamos Pandas para validar rápido
            # En producción usaríamos el RuntimeBatchRequest con Spark

        # 3. Ejecutar validación (Compatibilidad con GX 1.x)
        datasource = context.data_sources.add_pandas(
            name=f"ds_{int(time.time())}")
        asset = datasource.add_dataframe_asset(name="manual_asset")

        # En GX 1.x necesitamos definir un batch
        batch_def = asset.add_batch_definition_whole_dataframe("all_data")
        batch = batch_def.get_batch(batch_parameters={"dataframe": df})
        validator = context.get_validator(batch=batch)

        results = []
        for exp in suite_dict["expectations"]:
            exp_type = exp["expectation_type"]
            kwargs = exp["kwargs"]

            try:
                # Ejecutar via Validator de GX (más robusto que manual)
                method = getattr(validator, exp_type)
                val_res = method(**kwargs)
                results.append({
                    "expectation": exp_type,
                    "column": kwargs.get("column", "N/A"),
                    "success": val_res.success
                })
            except Exception as e:
                print(f"⚠️ Error ejecutando expectativa {exp_type}: {e}")

        # 4. Reportar resultados a Redis para el Dashboard
        if not results:
            print("⚠️ No hay resultados de validación.")
            return False

        success_rate = sum(1 for r in results if r["success"]) / len(results)
        dq_report = {
            "table": table_name,
            "timestamp": time.time(),
            "results": results,
            "success_rate": success_rate,
            "status": "PASS" if success_rate > 0.8 else "FAIL"
        }

        redis.set(f"dq_report:{table_name}", json.dumps(dq_report))
        print(
            f"✅ Validación completada: {dq_report['status']} ({success_rate*100:.1f}%)")
        return dq_report["status"] == "PASS"

    except Exception as e:
        print(f"❌ Error en el motor de DQ: {e}")
        return False


if __name__ == "__main__":
    import sys
    tbl = sys.argv[1] if len(sys.argv) > 1 else "silver.daily_prices"
    suite = sys.argv[2] if len(sys.argv) > 2 else "silver_prices_suite"
    validate_table(tbl, suite)
