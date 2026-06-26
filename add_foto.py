import sqlite3
conn = sqlite3.connect("veterinaria.db")
c = conn.cursor()
try:
    c.execute("ALTER TABLE animales ADD COLUMN foto TEXT DEFAULT ''")
    print("Columna foto agregada")
except sqlite3.OperationalError as e:
    print(f"Ya existe o error: {e}")
conn.close()
