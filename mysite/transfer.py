import pymysql
import sqlite3
from datetime import datetime
from decimal import Decimal

# === 1. Connect to Laragon MySQL ===
mysql_conn = pymysql.connect(
    host="localhost",
    user="root",
    password="",
    database="generalsoft-laragon",
    port=3306,
    cursorclass=pymysql.cursors.DictCursor
)
mysql_cursor = mysql_conn.cursor()

# === 2. Connect to SQLite ===
sqlite_conn = sqlite3.connect('db.sqlite3')
sqlite_cursor = sqlite_conn.cursor()

print("Reading from MySQL...")
mysql_cursor.execute("SELECT * FROM inventory_inventory")
rows = mysql_cursor.fetchall()
print(f"Found {len(rows)} products")

if not rows:
    print("No data!")
    exit()

sqlite_cursor.execute("DELETE FROM inventory_inventory")
sqlite_conn.commit()

columns = list(rows[0].keys())
placeholders = ", ".join(["?"] * len(columns))
col_names = ", ".join([f'"{c}"' for c in columns])

def clean_value(v):
    if isinstance(v, Decimal):
        return float(v) # <-- fix for Decimal
    if isinstance(v, datetime):
        return v.strftime('%Y-%m-%d %H:%M:%S.%f')
    return v

inserted = 0
for row in rows:
    values = [clean_value(v) for v in row.values()]
    try:
        sqlite_cursor.execute(f'INSERT INTO inventory_inventory ({col_names}) VALUES ({placeholders})', values)
        inserted += 1
        if inserted % 500 == 0:
            print(f"Inserted {inserted}...")
            sqlite_conn.commit() # commit every 500
    except Exception as e:
        print(f"Error at {inserted}: {e}")
        print(row)
        break

sqlite_conn.commit()
print(f"DONE! {inserted} products transferred to db.sqlite3")

mysql_cursor.close()
mysql_conn.close()
sqlite_conn.close()