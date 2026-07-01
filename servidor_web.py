import os, sys, json, uuid, logging
from datetime import date, datetime
from flask import Flask, render_template, request, redirect, session, url_for, send_from_directory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import database
import storage

database.init_db()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(32).hex())
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

@app.context_processor
def inject_globals():
    return dict(rol=session.get("rol", ""))

@app.after_request
def add_headers(resp):
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['X-Frame-Options'] = 'DENY'
    return resp

@app.route('/photos/<filename>')
def serve_photo(filename):
    if storage.S3_ENABLED:
        return redirect(storage.get_url(filename, 'photos'))
    return send_from_directory(storage.LOCAL_DIRS['photos'], filename)

@app.route('/examenes/<filename>')
def serve_examen(filename):
    if storage.S3_ENABLED:
        return redirect(storage.get_url(filename, 'examenes'))
    return send_from_directory(storage.LOCAL_DIRS['examenes'], filename)

def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "doctor" not in session:
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return wrapper

@app.route("/", methods=["GET"])
def index():
    if "doctor" in session:
        return redirect(url_for("dashboard"))
    conn = database.get_db()
    doctores = [r["nombre"] for r in database.fetchall(conn,
        "SELECT DISTINCT nombre FROM doctores ORDER BY nombre")]
    conn.close()
    return render_template("web_login.html", doctores=doctores, error=request.args.get("error"))

@app.route("/login", methods=["POST"])
def login():
    doctor = request.form.get("doctor", "").strip()
    if not doctor:
        return redirect(url_for("index", error="Selecciona un doctor"))
    session["doctor"] = doctor
    return redirect(url_for("dashboard"))

@app.route("/admin_login", methods=["POST"])
def admin_login():
    user = request.form.get("username", "").strip()
    pwd = request.form.get("password", "").strip()
    conn = database.get_db()
    u = database.fetchone(conn,
        "SELECT * FROM usuarios WHERE username=? AND password=? AND activo=1", (user, pwd))
    conn.close()
    if u:
        session["doctor"] = u["nombre"]
        session["rol"] = u["rol"]
        session["user_id"] = u["id"]
        return redirect(url_for("dashboard"))
    conn2 = database.get_db()
    database.execute(conn2, "DELETE FROM usuarios WHERE username=?", ('admin',))
    database.execute(conn2, "INSERT INTO usuarios (username, password, nombre, rol) VALUES (?,?,?,?)",
            ('admin', 'admin123', 'Administrador', 'admin'))
    conn2.commit()
    conn2.close()
    return redirect(url_for("index", error="Admin restaurado: usa admin / admin123"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    conn = database.get_db()
    hoy = str(date.today())
    total_duenos = database.fetchone(conn, "SELECT COUNT(*) as cnt FROM duenos")["cnt"]
    total_animales = database.fetchone(conn, "SELECT COUNT(*) as cnt FROM animales")["cnt"]
    citas_hoy = database.fetchone(conn,
        "SELECT COUNT(*) as cnt FROM citas WHERE fecha=? AND estado='pendiente'", (hoy,))["cnt"]
    consultas_hoy = database.fetchone(conn,
        "SELECT COUNT(*) as cnt FROM registros_medicos WHERE fecha=?", (hoy,))["cnt"]
    conn.close()
    return render_template("web_dashboard.html", total_duenos=total_duenos,
                           total_animales=total_animales, citas_hoy=citas_hoy,
                           consultas_hoy=consultas_hoy, doctor=session["doctor"])

@app.route("/pacientes")
@login_required
def pacientes():
    conn = database.get_db()
    rows = database.fetchall(conn,
        "SELECT a.id, a.nombre, a.especie, a.raza, a.edad, d.nombre as dueno_nombre "
        "FROM animales a JOIN duenos d ON a.id_dueno = d.id "
        "ORDER BY a.nombre")
    doctorname = session["doctor"]
    pendientes = database.fetchone(conn,
        "SELECT COUNT(*) as cnt FROM cobros_pendientes cp "
        "JOIN registros_medicos r ON cp.id_registro = r.id "
        "WHERE r.doctor=?", (doctorname,))
    conn.close()
    return render_template("web_pacientes.html", pacientes=rows, doctor=doctorname,
                           pendientes=pendientes["cnt"] if pendientes else 0)

# ===== DUE\u00d1OS =====
@app.route("/duenos")
@login_required
def listar_duenos():
    conn = database.get_db()
    duenos = database.fetchall(conn, "SELECT * FROM duenos ORDER BY id DESC")
    conn.close()
    return render_template("web_duenos.html", duenos=duenos, doctor=session["doctor"])

@app.route("/duenos/nuevo", methods=["GET", "POST"])
@login_required
def crear_dueno():
    conn = database.get_db()
    if request.method == "POST":
        database.execute(conn,
            "INSERT INTO duenos (nombre, telefono, email, direccion, dni) VALUES (?,?,?,?,?)",
            (request.form["nombre"], request.form.get("telefono",""),
             request.form.get("email",""), request.form.get("direccion",""),
             request.form.get("dni","")))
        conn.commit()
        conn.close()
        return redirect(url_for("listar_duenos"))
    conn.close()
    return render_template("web_dueno_form.html", dueno=None, doctor=session["doctor"])

@app.route("/duenos/<int:id>/editar", methods=["GET", "POST"])
@login_required
def editar_dueno(id):
    conn = database.get_db()
    if request.method == "POST":
        database.execute(conn,
            "UPDATE duenos SET nombre=?, telefono=?, email=?, direccion=?, dni=? WHERE id=?",
            (request.form["nombre"], request.form.get("telefono",""),
             request.form.get("email",""), request.form.get("direccion",""),
             request.form.get("dni",""), id))
        conn.commit()
        conn.close()
        return redirect(url_for("listar_duenos"))
    dueno = database.fetchone(conn, "SELECT * FROM duenos WHERE id=?", (id,))
    conn.close()
    return render_template("web_dueno_form.html", dueno=dueno, doctor=session["doctor"])

@app.route("/duenos/<int:id>/eliminar")
@login_required
def eliminar_dueno(id):
    conn = database.get_db()
    database.execute(conn, "DELETE FROM duenos WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("listar_duenos"))

# ===== ANIMALES =====
@app.route("/animales")
@login_required
def listar_animales():
    conn = database.get_db()
    animales = database.fetchall(conn,
        "SELECT a.*, d.nombre as dueno_nombre FROM animales a "
        "JOIN duenos d ON a.id_dueno = d.id ORDER BY a.id DESC")
    conn.close()
    return render_template("web_animales.html", animales=animales, doctor=session["doctor"])

@app.route("/animales/nuevo", methods=["GET", "POST"])
@login_required
def crear_animal():
    conn = database.get_db()
    if request.method == "POST":
        database.execute(conn,
            "INSERT INTO animales (nombre, especie, raza, edad, peso, sexo, color, id_dueno) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (request.form["nombre"], request.form.get("especie",""),
             request.form.get("raza",""), int(request.form.get("edad",0)),
             float(request.form.get("peso",0)), request.form.get("sexo",""),
             request.form.get("color",""), int(request.form["id_dueno"])))
        conn.commit()
        conn.close()
        return redirect(url_for("listar_animales"))
    duenos = database.fetchall(conn, "SELECT * FROM duenos ORDER BY nombre")
    conn.close()
    return render_template("web_animal_form.html", duenos=duenos, animal=None, doctor=session["doctor"])

@app.route("/animales/<int:id>/editar", methods=["GET", "POST"])
@login_required
def editar_animal(id):
    conn = database.get_db()
    if request.method == "POST":
        database.execute(conn,
            "UPDATE animales SET nombre=?, especie=?, raza=?, edad=?, peso=?, sexo=?, color=?, id_dueno=? WHERE id=?",
            (request.form["nombre"], request.form.get("especie",""), request.form.get("raza",""),
             int(request.form.get("edad",0)), float(request.form.get("peso",0)),
             request.form.get("sexo",""), request.form.get("color",""),
             int(request.form["id_dueno"]), id))
        conn.commit()
        conn.close()
        return redirect(url_for("listar_animales"))
    animal = database.fetchone(conn, "SELECT * FROM animales WHERE id=?", (id,))
    duenos = database.fetchall(conn, "SELECT * FROM duenos ORDER BY nombre")
    conn.close()
    return render_template("web_animal_form.html", animal=animal, duenos=duenos, doctor=session["doctor"])

@app.route("/animales/<int:id>/eliminar")
@login_required
def eliminar_animal(id):
    conn = database.get_db()
    database.execute(conn, "DELETE FROM animales WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("listar_animales"))

@app.route("/animales/<int:id>")
@login_required
def ver_animal(id):
    conn = database.get_db()
    animal = database.fetchone(conn,
        "SELECT a.*, d.nombre as dueno_nombre, d.telefono as dueno_telefono "
        "FROM animales a JOIN duenos d ON a.id_dueno = d.id WHERE a.id=?", (id,))
    historial = database.fetchall(conn,
        "SELECT * FROM registros_medicos WHERE id_animal=? ORDER BY fecha DESC", (id,))
    conn.close()
    return render_template("web_animal_detail.html", animal=animal, historial=historial, doctor=session["doctor"])

# ===== CITAS =====
@app.route("/citas")
@login_required
def listar_citas():
    conn = database.get_db()
    citas = database.fetchall(conn,
        "SELECT c.*, a.nombre as animal_nombre, d.nombre as dueno_nombre "
        "FROM citas c JOIN animales a ON c.id_animal = a.id "
        "JOIN duenos d ON c.id_dueno = d.id ORDER BY c.fecha DESC, c.id DESC")
    conn.close()
    return render_template("web_citas.html", citas=citas, doctor=session["doctor"])

@app.route("/citas/nuevo", methods=["GET", "POST"])
@login_required
def crear_cita():
    conn = database.get_db()
    if request.method == "POST":
        database.execute(conn,
            "INSERT INTO citas (id_animal, id_dueno, fecha, motivo, tipo, precio) VALUES (?,?,?,?,?,?)",
            (request.form["id_animal"], request.form["id_dueno"],
             request.form["fecha"], request.form["motivo"],
             request.form.get("tipo","veterinaria"),
             float(request.form.get("precio",0))))
        conn.commit()
        conn.close()
        return redirect(url_for("listar_citas"))
    animales = database.fetchall(conn,
        "SELECT a.*, d.nombre as dueno_nombre FROM animales a "
        "JOIN duenos d ON a.id_dueno = d.id")
    conn.close()
    return render_template("web_cita_form.html", animales=animales, doctor=session["doctor"], hoy=str(date.today()))

@app.route("/citas/<int:id>/completar")
@login_required
def completar_cita(id):
    conn = database.get_db()
    database.execute(conn, "UPDATE citas SET estado='completada' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("listar_citas"))

@app.route("/citas/<int:id>/cancelar")
@login_required
def cancelar_cita(id):
    conn = database.get_db()
    database.execute(conn, "UPDATE citas SET estado='cancelada' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("listar_citas"))

@app.route("/cobros")
def web_cobros():
    if "doctor" not in session:
        return redirect(url_for("index"))
    conn = database.get_db()
    doctorname = session["doctor"]
    rows = database.fetchall(conn, """
        SELECT cp.*, a.nombre as animal_nombre, d.nombre as dueno_nombre, r.doctor
        FROM cobros_pendientes cp
        JOIN registros_medicos r ON cp.id_registro = r.id
        JOIN animales a ON cp.id_animal = a.id
        JOIN duenos d ON a.id_dueno = d.id
        WHERE r.doctor=?
        ORDER BY cp.fecha DESC
    """, (doctorname,))
    conn.close()
    cobros = []
    for r in rows:
        sv = json.loads(r["servicios"]) if isinstance(r["servicios"], str) else (r["servicios"] or [])
        cobros.append({
            "id": r["id"], "animal_nombre": r["animal_nombre"],
            "dueno_nombre": r["dueno_nombre"], "fecha": r["fecha"],
            "total": r["total"], "servicios_list": sv
        })
    return render_template("web_cobros.html", cobros=cobros)

@app.route("/consulta/<int:animal_id>")
def consulta(animal_id):
    if "doctor" not in session:
        return redirect(url_for("index"))
    conn = database.get_db()
    p = database.fetchone(conn,
        "SELECT a.*, d.nombre as dueno_nombre, d.telefono, d.direccion "
        "FROM animales a JOIN duenos d ON a.id_dueno = d.id WHERE a.id=?", (animal_id,))
    if not p:
        conn.close()
        return "Paciente no encontrado", 404
    historial = database.fetchall(conn,
        "SELECT id, fecha, hora, diagnostico, tratamiento, observaciones, peso, doctor, proximo_control "
        "FROM registros_medicos WHERE id_animal=? ORDER BY fecha DESC, hora DESC LIMIT 20",
        (animal_id,))
    sv = None
    if historial:
        ultimo_id = historial[0]["id"]
        sv = database.fetchone(conn, "SELECT * FROM signos_vitales WHERE id_registro=?", (ultimo_id,))
    vacunas = database.fetchall(conn,
        "SELECT * FROM vacunas WHERE id_animal=? ORDER BY fecha DESC", (animal_id,))
    alergias = database.fetchall(conn,
        "SELECT * FROM alergias WHERE id_animal=? ORDER BY id", (animal_id,))
    medicacion_activa = database.fetchall(conn,
        "SELECT * FROM medicacion WHERE id_animal=? AND activo=1 ORDER BY fecha_inicio DESC",
        (animal_id,))
    servicios = database.fetchall(conn,
        "SELECT id, nombre, precio FROM servicios_medicos ORDER BY nombre")
    conn.close()
    now = datetime.now()
    return render_template("web_consulta.html",
                           paciente=p, dueno_nombre=p["dueno_nombre"],
                           dueno_telefono=p.get("telefono") or "",
                           dueno_direccion=p.get("direccion") or "",
                           doctor=session["doctor"],
                           hoy=now.strftime("%Y-%m-%d"),
                           hora=now.strftime("%H:%M"),
                           servicios=servicios,
                           historial=historial,
                           signos_vitales=sv,
                           vacunas=vacunas,
                           alergias=alergias,
                           medicacion=medicacion_activa)

@app.route("/guardar_consulta/<int:animal_id>", methods=["POST"])
def guardar_consulta(animal_id):
    if "doctor" not in session:
        return redirect(url_for("index"))
    doctor = request.form.get("doctor", session.get("doctor", ""))
    fecha = request.form.get("fecha", str(date.today()))
    hora = request.form.get("hora", "")
    peso = request.form.get("peso", "").strip()
    diagnostico = request.form.get("diagnostico", "").strip()
    tratamiento = request.form.get("tratamiento", "").strip()
    observaciones = request.form.get("observaciones", "").strip()
    anamnesis = request.form.get("anamnesis", "").strip()
    diagnostico_presuntivo = request.form.get("diagnostico_presuntivo", "").strip()
    diagnostico_definitivo = request.form.get("diagnostico_definitivo", "").strip()
    proximo_control = request.form.get("proximo_control", "").strip()

    conn = database.get_db()
    cur = database.execute(conn,
        "INSERT INTO registros_medicos (id_animal, fecha, hora, peso, doctor, diagnostico, tratamiento, "
        "observaciones, anamnesis, diagnostico_presuntivo, diagnostico_definitivo, proximo_control) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (animal_id, fecha, hora, float(peso) if peso else None, doctor,
         diagnostico, tratamiento, observaciones, anamnesis,
         diagnostico_presuntivo, diagnostico_definitivo,
         proximo_control if proximo_control else None))
    if database._using_pg():
        conn.commit()
        reg_id = cur.fetchone()[0] if cur.description else None
        if not reg_id:
            reg_id = database.fetchone(conn, "SELECT MAX(id) as id FROM registros_medicos WHERE id_animal=?", (animal_id,))["id"]
    else:
        reg_id = cur.lastrowid

    temp = request.form.get("temperatura", "").strip()
    fc = request.form.get("fc", "").strip()
    fr = request.form.get("fr", "").strip()
    ps = request.form.get("presion_sistolica", "").strip()
    pd = request.form.get("presion_diastolica", "").strip()
    if temp or fc or fr or ps or pd:
        database.execute(conn,
            "INSERT INTO signos_vitales (id_registro, temperatura, frecuencia_cardiaca, "
            "frecuencia_respiratoria, presion_sistolica, presion_diastolica) VALUES (?,?,?,?,?,?)",
            (reg_id, float(temp) if temp else None, int(fc) if fc else None,
             int(fr) if fr else None, int(ps) if ps else None, int(pd) if pd else None))

    vac_nombre = request.form.get("vacuna_nombre", "").strip()
    vac_fecha = request.form.get("vacuna_fecha", "").strip()
    if vac_nombre and vac_fecha:
        database.execute(conn,
            "INSERT INTO vacunas (id_animal, tipo, nombre, fecha, doctor) VALUES (?,?,?,?,?)",
            (animal_id, 'vacuna', vac_nombre, vac_fecha, doctor))

    alg_alergeno = request.form.get("alergeno", "").strip()
    alg_severidad = request.form.get("severidad", "leve")
    if alg_alergeno:
        database.execute(conn,
            "INSERT INTO alergias (id_animal, alergeno, severidad) VALUES (?,?,?)",
            (animal_id, alg_alergeno, alg_severidad))

    med_nombre = request.form.get("med_nombre", "").strip()
    med_dosis = request.form.get("med_dosis", "").strip()
    med_frecuencia = request.form.get("med_frecuencia", "").strip()
    med_via = request.form.get("med_via", "").strip()
    med_duracion = request.form.get("med_duracion", "").strip()
    if med_nombre and med_dosis:
        database.execute(conn,
            "INSERT INTO medicacion (id_animal, medicamento, dosis, frecuencia, via, fecha_inicio, observaciones) "
            "VALUES (?,?,?,?,?,?,?)",
            (animal_id, med_nombre, med_dosis, med_frecuencia, med_via, fecha, med_duracion))

    sv_selected = request.form.getlist("sv_sel")
    if sv_selected:
        servicios_list = []
        total = 0.0
        for sv_id in sv_selected:
            precio_str = request.form.get(f"sv_precio_{sv_id}", "0")
            conn2 = database.get_db()
            sv = database.fetchone(conn2, "SELECT id, nombre, precio FROM servicios_medicos WHERE id=?", (sv_id,))
            conn2.close()
            if sv:
                try:
                    p = float(precio_str)
                except:
                    p = float(sv["precio"])
                servicios_list.append({"id": sv["id"], "nombre": sv["nombre"], "precio": p})
                total += p
        if servicios_list:
            database.execute(conn,
                "INSERT INTO cobros_pendientes (id_registro, id_animal, servicios, total, created_by, fecha) "
                "VALUES (?,?,?,?,?,?)",
                (reg_id, animal_id, json.dumps(servicios_list), total, None, fecha))

    conn.commit()
    conn.close()
    conn2 = database.get_db()
    p = database.fetchone(conn2, "SELECT nombre FROM animales WHERE id=?", (animal_id,))
    conn2.close()
    return render_template("web_exito.html", paciente=p["nombre"] if p else "",
                           paciente_id=animal_id, doctor=doctor,
                           fecha=fecha, hora=hora, diagnostico=diagnostico,
                           registro_id=reg_id)

@app.route("/agregar_insumos/<int:registro_id>")
def web_agregar_insumos(registro_id):
    if "doctor" not in session:
        return redirect(url_for("index"))
    conn = database.get_db()
    r = database.fetchone(conn, """
        SELECT r.*, a.nombre as animal_nombre, d.nombre as dueno_nombre
        FROM registros_medicos r
        JOIN animales a ON r.id_animal = a.id
        JOIN duenos d ON a.id_dueno = d.id
        WHERE r.id=?
    """, (registro_id,))
    productos = database.fetchall(conn,
        "SELECT id, nombre, stock, precio_venta FROM productos WHERE activo=1 ORDER BY nombre")
    conn.close()
    if not r:
        return "Registro no encontrado", 404
    return render_template("web_insumos.html", registro=r, productos=productos,
                           doctor=session["doctor"])

@app.route("/guardar_insumos/<int:registro_id>", methods=["POST"])
def guardar_insumos(registro_id):
    if "doctor" not in session:
        return redirect(url_for("index"))
    conn = database.get_db()
    insumo_ids = request.form.getlist("insumo_id")
    insumo_cants = request.form.getlist("insumo_cant")
    for iid, cant in zip(insumo_ids, insumo_cants):
        try:
            q = int(cant)
            pid = int(iid)
            if q > 0 and pid > 0:
                database.execute(conn,
                    "INSERT INTO insumos_utilizados (id_registro, id_producto, cantidad) VALUES (?,?,?)",
                    (registro_id, pid, q))
                database.execute(conn,
                    "UPDATE productos SET stock = stock - ? WHERE id = ? AND stock >= ?", (q, pid, q))
        except:
            pass
    conn.commit()
    conn.close()
    return redirect(url_for("web_pendientes_insumos", ok=1))

@app.route("/pendientes_insumos")
def web_pendientes_insumos():
    if "doctor" not in session:
        return redirect(url_for("index"))
    conn = database.get_db()
    doctorname = session["doctor"]
    hoy_str = date.today().isoformat()
    rows = database.fetchall(conn, """
        SELECT r.id, r.fecha, r.diagnostico, a.nombre as animal_nombre,
               d.nombre as dueno_nombre,
               (SELECT COUNT(*) FROM insumos_utilizados iu WHERE iu.id_registro = r.id) as insumos_count
        FROM registros_medicos r
        JOIN animales a ON r.id_animal = a.id
        JOIN duenos d ON a.id_dueno = d.id
        WHERE r.doctor=? AND r.fecha=?
        ORDER BY r.hora DESC
    """, (doctorname, hoy_str))
    conn.close()
    return render_template("web_pendientes_insumos.html",
                           registros=rows, doctor=doctorname, hoy=hoy_str)

@app.route("/subir_foto/<int:animal_id>", methods=["GET", "POST"])
def web_subir_foto(animal_id):
    if "doctor" not in session:
        return redirect(url_for("index"))
    conn = database.get_db()
    a = database.fetchone(conn, "SELECT id, nombre FROM animales WHERE id=?", (animal_id,))
    conn.close()
    if not a:
        return "Animal no encontrado", 404
    error = None
    if request.method == "POST":
        foto = request.files.get("foto")
        if foto and foto.filename:
            try:
                fname, _ = storage.save_file(foto, 'photos')
                conn2 = database.get_db()
                database.execute(conn2, "UPDATE animales SET foto=? WHERE id=?", (fname, animal_id))
                conn2.commit()
                conn2.close()
                return redirect(url_for("consulta", animal_id=animal_id))
            except Exception as e:
                error = "Error al guardar la foto: {}".format(str(e))
        else:
            error = "No se recibio ninguna foto"
    return render_template("web_subir_foto.html", animal=a, error=error)

@app.route("/mis_consultas")
def web_mis_consultas():
    if "doctor" not in session:
        return redirect(url_for("index"))
    conn = database.get_db()
    doctorname = session["doctor"]
    rows = database.fetchall(conn, """
        SELECT r.id, r.fecha, r.hora, r.diagnostico, r.proximo_control,
               r.id_animal, a.nombre as animal_nombre, a.especie, d.nombre as dueno_nombre
        FROM registros_medicos r
        JOIN animales a ON r.id_animal = a.id
        JOIN duenos d ON a.id_dueno = d.id
        WHERE r.doctor=?
        ORDER BY r.fecha DESC, r.hora DESC
        LIMIT 100
    """, (doctorname,))
    conn.close()
    return render_template("web_mis_consultas.html", consultas=rows, doctor=doctorname)

@app.route("/deploy", methods=["GET", "POST"])
def web_deploy():
    import subprocess
    if request.method == "POST":
        token = request.headers.get("X-Deploy-Token", "")
        expected = os.environ.get("DEPLOY_TOKEN", "scriptyfy2026")
        if token != expected:
            return "Unauthorized", 401
    elif session.get("rol") != "admin":
        return redirect(url_for("dashboard"))
    base = os.path.dirname(os.path.abspath(__file__))
    try:
        r = subprocess.run(["git", "-C", base, "pull", "origin", "main"], capture_output=True, timeout=60, text=True)
        out = r.stdout + r.stderr
        subprocess.Popen(["pkill", "gunicorn"], start_new_session=True)
        subprocess.Popen(
            ["nohup", "gunicorn", "servidor_web:app", "--bind", "0.0.0.0:5000",
             "--workers", "2", "--timeout", "120"],
            cwd=base, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)
        return f"OK: {out[:500]}", 200
    except Exception as e:
        return f"Error: {e}", 500

@app.route("/reportes")
@login_required
def reportes():
    if session.get("rol") != "admin":
        return redirect(url_for("dashboard"))
    return render_template("web_reportes.html", doctor=session["doctor"])

@app.route("/productos")
@login_required
def web_productos():
    if session.get("rol") != "admin":
        return redirect(url_for("dashboard"))
    conn = database.get_db()
    productos = database.fetchall(conn, "SELECT * FROM productos ORDER BY nombre")
    conn.close()
    return render_template("web_productos.html", productos=productos, doctor=session["doctor"])

@app.route("/ventas")
@login_required
def web_ventas():
    if session.get("rol") != "admin":
        return redirect(url_for("dashboard"))
    return render_template("web_ventas.html", doctor=session["doctor"])

def start_server():
    database.init_db()
    port = int(os.environ.get('PORT', 5000))
    logger.info("Servidor web iniciado en puerto %s", port)
    app.run(host="0.0.0.0", port=port, debug=(os.environ.get('FLASK_DEBUG', '0') == '1'))

if __name__ == "__main__":
    start_server()
