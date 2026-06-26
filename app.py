import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import date

app = Flask(__name__)
app.secret_key = "veterinaria-v1-secret-key"

DB_PATH = os.path.join(os.path.dirname(__file__), "veterinaria.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS duenos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT NOT NULL,
            email TEXT,
            direccion TEXT
        );
        CREATE TABLE IF NOT EXISTS animales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            especie TEXT NOT NULL,
            raza TEXT,
            edad INTEGER,
            peso REAL,
            id_dueno INTEGER NOT NULL,
            FOREIGN KEY (id_dueno) REFERENCES duenos(id)
        );
        CREATE TABLE IF NOT EXISTS citas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_animal INTEGER NOT NULL,
            id_dueno INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            motivo TEXT NOT NULL,
            estado TEXT DEFAULT 'pendiente',
            FOREIGN KEY (id_animal) REFERENCES animales(id),
            FOREIGN KEY (id_dueno) REFERENCES duenos(id)
        );
        CREATE TABLE IF NOT EXISTS registros_medicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_animal INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            diagnostico TEXT NOT NULL,
            tratamiento TEXT NOT NULL,
            observaciones TEXT DEFAULT '',
            FOREIGN KEY (id_animal) REFERENCES animales(id)
        );
    """)
    conn.commit()
    conn.close()


# ---------- INICIO ----------
@app.route("/")
def index():
    conn = get_db()
    total_duenos = conn.execute("SELECT COUNT(*) FROM duenos").fetchone()[0]
    total_animales = conn.execute("SELECT COUNT(*) FROM animales").fetchone()[0]
    citas_hoy = conn.execute(
        "SELECT COUNT(*) FROM citas WHERE fecha = ? AND estado = 'pendiente'",
        (str(date.today()),)
    ).fetchone()[0]
    conn.close()
    return render_template("index.html", total_duenos=total_duenos,
                           total_animales=total_animales, citas_hoy=citas_hoy)


# ---------- DUEÑOS ----------
@app.route("/duenos")
def listar_duenos():
    conn = get_db()
    duenos = conn.execute("SELECT * FROM duenos ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("owners/list.html", duenos=duenos)


@app.route("/duenos/nuevo", methods=["GET", "POST"])
def crear_dueno():
    if request.method == "POST":
        nombre = request.form["nombre"]
        telefono = request.form["telefono"]
        email = request.form["email"]
        direccion = request.form["direccion"]
        conn = get_db()
        conn.execute("INSERT INTO duenos (nombre, telefono, email, direccion) VALUES (?, ?, ?, ?)",
                     (nombre, telefono, email, direccion))
        conn.commit()
        conn.close()
        flash("Dueño registrado exitosamente", "success")
        return redirect(url_for("listar_duenos"))
    return render_template("owners/form.html")


@app.route("/duenos/<int:id>/editar", methods=["GET", "POST"])
def editar_dueno(id):
    conn = get_db()
    if request.method == "POST":
        conn.execute("UPDATE duenos SET nombre=?, telefono=?, email=?, direccion=? WHERE id=?",
                     (request.form["nombre"], request.form["telefono"],
                      request.form["email"], request.form["direccion"], id))
        conn.commit()
        conn.close()
        flash("Dueño actualizado", "success")
        return redirect(url_for("listar_duenos"))
    dueno = conn.execute("SELECT * FROM duenos WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template("owners/form.html", dueno=dueno)


@app.route("/duenos/<int:id>/eliminar")
def eliminar_dueno(id):
    conn = get_db()
    conn.execute("DELETE FROM duenos WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Dueño eliminado", "success")
    return redirect(url_for("listar_duenos"))


# ---------- ANIMALES ----------
@app.route("/animales")
def listar_animales():
    conn = get_db()
    animales = conn.execute("""
        SELECT a.*, d.nombre as dueno_nombre
        FROM animales a JOIN duenos d ON a.id_dueno = d.id
        ORDER BY a.id DESC
    """).fetchall()
    conn.close()
    return render_template("animals/list.html", animales=animales)


@app.route("/animales/nuevo", methods=["GET", "POST"])
def crear_animal():
    conn = get_db()
    if request.method == "POST":
        conn.execute(
            "INSERT INTO animales (nombre, especie, raza, edad, peso, id_dueno) VALUES (?, ?, ?, ?, ?, ?)",
            (request.form["nombre"], request.form["especie"], request.form["raza"],
             int(request.form["edad"]), float(request.form["peso"]), int(request.form["id_dueno"]))
        )
        conn.commit()
        conn.close()
        flash("Animal registrado", "success")
        return redirect(url_for("listar_animales"))
    duenos = conn.execute("SELECT * FROM duenos ORDER BY nombre").fetchall()
    conn.close()
    return render_template("animals/form.html", duenos=duenos)


@app.route("/animales/<int:id>")
def ver_animal(id):
    conn = get_db()
    animal = conn.execute("""
        SELECT a.*, d.nombre as dueno_nombre, d.telefono as dueno_telefono
        FROM animales a JOIN duenos d ON a.id_dueno = d.id
        WHERE a.id=?
    """, (id,)).fetchone()
    historial = conn.execute(
        "SELECT * FROM registros_medicos WHERE id_animal=? ORDER BY fecha DESC", (id,)
    ).fetchall()
    conn.close()
    return render_template("animals/detail.html", animal=animal, historial=historial)


@app.route("/animales/<int:id>/eliminar")
def eliminar_animal(id):
    conn = get_db()
    conn.execute("DELETE FROM animales WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Animal eliminado", "success")
    return redirect(url_for("listar_animales"))


# ---------- CITAS ----------
@app.route("/citas")
def listar_citas():
    conn = get_db()
    citas = conn.execute("""
        SELECT c.*, a.nombre as animal_nombre, d.nombre as dueno_nombre
        FROM citas c
        JOIN animales a ON c.id_animal = a.id
        JOIN duenos d ON c.id_dueno = d.id
        ORDER BY c.fecha DESC, c.id DESC
    """).fetchall()
    conn.close()
    return render_template("appointments/list.html", citas=citas)


@app.route("/citas/nuevo", methods=["GET", "POST"])
def crear_cita():
    conn = get_db()
    if request.method == "POST":
        conn.execute(
            "INSERT INTO citas (id_animal, id_dueno, fecha, motivo) VALUES (?, ?, ?, ?)",
            (request.form["id_animal"], request.form["id_dueno"],
             request.form["fecha"], request.form["motivo"])
        )
        conn.commit()
        conn.close()
        flash("Cita agendada", "success")
        return redirect(url_for("listar_citas"))
    animales = conn.execute("SELECT a.*, d.nombre as dueno_nombre FROM animales a JOIN duenos d ON a.id_dueno = d.id").fetchall()
    conn.close()
    return render_template("appointments/form.html", animales=animales)


@app.route("/citas/<int:id>/completar")
def completar_cita(id):
    conn = get_db()
    conn.execute("UPDATE citas SET estado='completada' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Cita completada", "success")
    return redirect(url_for("listar_citas"))


@app.route("/citas/<int:id>/cancelar")
def cancelar_cita(id):
    conn = get_db()
    conn.execute("UPDATE citas SET estado='cancelada' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Cita cancelada", "success")
    return redirect(url_for("listar_citas"))


# ---------- HISTORIAL MÉDICO ----------
@app.route("/registros/nuevo", methods=["GET", "POST"])
def crear_registro():
    conn = get_db()
    if request.method == "POST":
        conn.execute(
            "INSERT INTO registros_medicos (id_animal, fecha, diagnostico, tratamiento, observaciones) VALUES (?, ?, ?, ?, ?)",
            (request.form["id_animal"], str(date.today()),
             request.form["diagnostico"], request.form["tratamiento"],
             request.form.get("observaciones", ""))
        )
        conn.commit()
        conn.close()
        flash("Registro médico agregado", "success")
        return redirect(url_for("ver_animal", id=request.form["id_animal"]))
    animales = conn.execute("SELECT a.*, d.nombre as dueno_nombre FROM animales a JOIN duenos d ON a.id_dueno = d.id").fetchall()
    conn.close()
    return render_template("medical_records/form.html", animales=animales)


if __name__ == "__main__":
    init_db()
    import socket
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    print(f"\n  Servidor corriendo en http://127.0.0.1:5000\n")
    app.run(host="127.0.0.1", port=5000, debug=True)
