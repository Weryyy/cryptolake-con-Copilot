import sys

from pyhive import hive

try:
    print("Connecting to spark-master:10001 with database='gold'...")
    conn = hive.Connection(host="spark-master", port=10001,
                           username="airflow", database="gold")
    cursor = conn.cursor()

    print("Executing SHOW DATABASES...")
    cursor.execute("SHOW DATABASES")
    databases = cursor.fetchall()
    print(f"Databases found: {databases}")

    # Try to use gold
    print("Attempting to USE gold...")
    cursor.execute("USE gold")
    print("Successfully switched to gold namespace.")

    cursor.close()
    conn.close()
    print("Done.")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
