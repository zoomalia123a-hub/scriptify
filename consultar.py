import sqlite3
conn = sqlite3.connect("veterinaria.db")
c = conn.cursor()

c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("=== TABLAS ===")
for t in c.fetchall():
    print(f"  {t[0]}")

print()

c.execute("SELECT * FROM duenos")
print("=== DUENOS ===")
for r in c.fetchall():
    print(f"  {r}")

print()

c.execute("SELECT a.id, a.nombre, a.especie, a.raza, a.edad, a.peso, d.nombre FROM animales a JOIN duenos d ON a.id_dueno = d.id")
print("=== ANIMALES ===")
for r in c.fetchall():
    print(f"  {r}")

print()

c.execute("SELECT c.id, a.nombre, d.nombre, c.fecha, c.motivo, c.estado FROM citas c JOIN animales a ON c.id_animal = a.id JOIN duenos d ON c.id_dueno = d.id")
print("=== CITAS ===")
for r in c.fetchall():
    print(f"  {r}")

print()

c.execute("SELECT rm.id, a.nombre, rm.fecha, rm.diagnostico, rm.tratamiento FROM registros_medicos rm JOIN animales a ON rm.id_animal = a.id")
print("=== REGISTROS MEDICOS ===")
for r in c.fetchall():
    print(f"  {r}")

conn.close()
