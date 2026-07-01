import os, re, json, hashlib
from datetime import date, datetime

DB_URL = os.environ.get('DATABASE_URL')

def _using_pg():
    return DB_URL is not None and DB_URL.startswith('postgres')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if _using_pg():
    DB_PATH = DB_URL
    PHOTOS_DIR = os.environ.get('PHOTOS_DIR', os.path.join(BASE_DIR, 'photos'))
    EXAMENES_DIR = os.environ.get('EXAMENES_DIR', os.path.join(BASE_DIR, 'examenes'))
    DOCS_DIR = os.environ.get('DOCS_DIR', os.path.join(BASE_DIR, 'documentos'))
else:
    DB_PATH = os.path.join(BASE_DIR, 'veterinaria.db')
    PHOTOS_DIR = os.path.join(BASE_DIR, 'photos')
    EXAMENES_DIR = os.path.join(BASE_DIR, 'examenes')
    DOCS_DIR = os.path.join(BASE_DIR, 'documentos')

def _fix_sql(sql):
    if _using_pg():
        sql = sql.replace('?', '%s')
        sql = sql.replace('AUTOINCREMENT', '')
        sql = sql.replace('INTEGER PRIMARY KEY', 'SERIAL PRIMARY KEY')
        sql = sql.replace('TEXT DEFAULT', 'TEXT DEFAULT')
        sql = re.sub(r"INSERT OR IGNORE", "INSERT INTO", sql, flags=re.IGNORECASE)
    return sql

_PSYCOPG2 = None

def _get_psyco():
    global _PSYCOPG2
    if _PSYCOPG2 is None:
        import psycopg2
        _PSYCOPG2 = psycopg2
    return _PSYCOPG2

def get_db():
    if _using_pg():
        pg = _get_psyco()
        from psycopg2.extras import RealDictCursor
        conn = pg.connect(DB_URL)
        return conn
    import sqlite3
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    return conn

def _exec(conn, sql, params=None):
    sql = _fix_sql(sql)
    if params:
        if _using_pg() and isinstance(params, (list, tuple)):
            params = tuple(p if p is not None else None for p in params)
        return conn.execute(sql, params)
    return conn.execute(sql)

def _exec_script(conn, sql):
    if _using_pg():
        statements = re.split(r';\s*\n', sql)
        for stmt in statements:
            stmt = stmt.strip()
            if stmt:
                try:
                    conn.execute(_fix_sql(stmt))
                except Exception as e:
                    if 'already exists' not in str(e).lower():
                        raise
        return
    conn.executescript(sql)

def _last_id(cur):
    if _using_pg():
        return cur.fetchone()[0] if cur.rowcount > 0 else None
    return cur.lastrowid

def fetchone(conn, sql, params=None):
    cur = _exec(conn, sql, params)
    row = cur.fetchone()
    return dict(row) if row else None

def fetchall(conn, sql, params=None):
    cur = _exec(conn, sql, params)
    rows = cur.fetchall()
    return [dict(r) for r in rows]

def execute(conn, sql, params=None):
    return _exec(conn, sql, params)

def init_db():
    conn = get_db()
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    schema = '''
        CREATE TABLE IF NOT EXISTS doctores (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE);
        CREATE TABLE IF NOT EXISTS duenos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dni TEXT,
            nombre TEXT NOT NULL,
            telefono TEXT DEFAULT '',
            email TEXT DEFAULT '',
            direccion TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS animales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            especie TEXT DEFAULT '',
            raza TEXT DEFAULT '',
            edad INTEGER DEFAULT 0,
            peso REAL DEFAULT 0,
            sexo TEXT DEFAULT '',
            color TEXT DEFAULT '',
            fecha_nacimiento TEXT,
            esterilizado INTEGER DEFAULT 0,
            foto TEXT DEFAULT '',
            id_dueno INTEGER NOT NULL,
            FOREIGN KEY (id_dueno) REFERENCES duenos(id)
        );
        CREATE TABLE IF NOT EXISTS citas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_animal INTEGER NOT NULL,
            id_dueno INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT DEFAULT '',
            motivo TEXT DEFAULT '',
            tipo TEXT DEFAULT 'veterinaria',
            precio REAL DEFAULT 0,
            estado TEXT DEFAULT 'pendiente',
            FOREIGN KEY (id_animal) REFERENCES animales(id),
            FOREIGN KEY (id_dueno) REFERENCES duenos(id)
        );
        CREATE TABLE IF NOT EXISTS registros_medicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_animal INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT, peso REAL, doctor TEXT,
            diagnostico TEXT, tratamiento TEXT, observaciones TEXT,
            anamnesis TEXT DEFAULT '', diagnostico_presuntivo TEXT DEFAULT '',
            diagnostico_definitivo TEXT DEFAULT '',
            exam_ecografia TEXT DEFAULT '', exam_radiografia TEXT DEFAULT '',
            exam_hemograma TEXT DEFAULT '', exam_bioquimico TEXT DEFAULT '',
            exam_orina TEXT DEFAULT '', exam_otros TEXT DEFAULT '',
            facturado INTEGER DEFAULT 0, pendiente_cobro INTEGER DEFAULT 0,
            cobrado_por INTEGER DEFAULT NULL, id_venta INTEGER DEFAULT NULL,
            proximo_control TEXT,
            FOREIGN KEY (id_animal) REFERENCES animales(id));
        CREATE TABLE IF NOT EXISTS signos_vitales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_registro INTEGER NOT NULL,
            temperatura REAL, frecuencia_cardiaca INTEGER,
            frecuencia_respiratoria INTEGER, presion_sistolica INTEGER, presion_diastolica INTEGER,
            FOREIGN KEY (id_registro) REFERENCES registros_medicos(id));
        CREATE TABLE IF NOT EXISTS vacunas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, id_animal INTEGER NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'vacuna', nombre TEXT NOT NULL, fecha TEXT NOT NULL,
            lote TEXT DEFAULT '', dosis TEXT DEFAULT '', proxima_dosis TEXT,
            doctor TEXT DEFAULT '', observaciones TEXT DEFAULT '',
            FOREIGN KEY (id_animal) REFERENCES animales(id));
        CREATE TABLE IF NOT EXISTS alergias (
            id INTEGER PRIMARY KEY AUTOINCREMENT, id_animal INTEGER NOT NULL,
            alergeno TEXT NOT NULL, tipo TEXT DEFAULT '', severidad TEXT DEFAULT 'leve',
            observaciones TEXT DEFAULT '', FOREIGN KEY (id_animal) REFERENCES animales(id));
        CREATE TABLE IF NOT EXISTS examenes_auxiliares (
            id INTEGER PRIMARY KEY AUTOINCREMENT, id_animal INTEGER NOT NULL,
            tipo TEXT NOT NULL, nombre TEXT NOT NULL, fecha TEXT NOT NULL,
            archivo TEXT DEFAULT '', resultados TEXT DEFAULT '', observaciones TEXT DEFAULT '',
            FOREIGN KEY (id_animal) REFERENCES animales(id));
        CREATE TABLE IF NOT EXISTS medicacion (
            id INTEGER PRIMARY KEY AUTOINCREMENT, id_animal INTEGER NOT NULL,
            medicamento TEXT NOT NULL, dosis TEXT NOT NULL, frecuencia TEXT NOT NULL,
            via TEXT DEFAULT '', fecha_inicio TEXT NOT NULL, fecha_fin TEXT,
            activo INTEGER DEFAULT 1, observaciones TEXT DEFAULT '',
            FOREIGN KEY (id_animal) REFERENCES animales(id));
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL, descripcion TEXT DEFAULT '',
            precio_compra REAL NOT NULL DEFAULT 0, precio_venta REAL NOT NULL DEFAULT 0,
            stock INTEGER NOT NULL DEFAULT 0, categoria TEXT DEFAULT 'General', activo INTEGER DEFAULT 1,
            en_catalogo INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS servicios_grooming (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, descripcion TEXT DEFAULT '',
            precio REAL NOT NULL DEFAULT 0, duracion_minutos INTEGER DEFAULT 30, tipo TEXT DEFAULT 'Ba\u00f1o'
        );
        CREATE TABLE IF NOT EXISTS historial_grooming (
            id INTEGER PRIMARY KEY AUTOINCREMENT, id_animal INTEGER NOT NULL, id_servicio INTEGER,
            fecha TEXT NOT NULL, observaciones TEXT DEFAULT '', precio REAL NOT NULL DEFAULT 0,
            estilista TEXT DEFAULT '',
            FOREIGN KEY (id_animal) REFERENCES animales(id),
            FOREIGN KEY (id_servicio) REFERENCES servicios_grooming(id)
        );
        CREATE TABLE IF NOT EXISTS servicios_medicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL, descripcion TEXT DEFAULT '',
            precio REAL NOT NULL DEFAULT 0, tipo TEXT DEFAULT 'consulta'
        );
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, id_cliente INTEGER, id_animal INTEGER,
            fecha TEXT NOT NULL, total REAL NOT NULL DEFAULT 0, tipo TEXT DEFAULT 'producto',
            estado TEXT DEFAULT 'completada'
        );
        CREATE TABLE IF NOT EXISTS venta_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, id_venta INTEGER NOT NULL,
            tipo_item TEXT NOT NULL, referencia_id INTEGER, nombre TEXT NOT NULL,
            cantidad INTEGER NOT NULL DEFAULT 1, precio_unitario REAL NOT NULL, subtotal REAL NOT NULL,
            FOREIGN KEY (id_venta) REFERENCES ventas(id)
        );
        CREATE TABLE IF NOT EXISTS caja (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL, tipo TEXT NOT NULL, concepto TEXT,
            monto REAL NOT NULL, referencia_tipo TEXT, referencia_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_venta INTEGER NOT NULL, monto REAL NOT NULL,
            metodo TEXT DEFAULT 'efectivo', fecha TEXT NOT NULL,
            FOREIGN KEY (id_venta) REFERENCES ventas(id)
        );
        CREATE TABLE IF NOT EXISTS creditos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_venta INTEGER NOT NULL, id_cliente INTEGER,
            total REAL NOT NULL, saldo REAL NOT NULL,
            fecha_venta TEXT NOT NULL, fecha_vencimiento TEXT,
            estado TEXT DEFAULT 'pendiente', notas TEXT DEFAULT '',
            FOREIGN KEY (id_venta) REFERENCES ventas(id)
        );
        CREATE TABLE IF NOT EXISTS pagos_credito (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_credito INTEGER NOT NULL, monto REAL NOT NULL,
            fecha TEXT NOT NULL, metodo TEXT DEFAULT 'efectivo', observaciones TEXT DEFAULT '',
            FOREIGN KEY (id_credito) REFERENCES creditos(id)
        );
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
            nombre TEXT NOT NULL, rol TEXT DEFAULT 'empleado', activo INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS documentos_adjuntos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_animal INTEGER NOT NULL, nombre TEXT NOT NULL, tipo TEXT DEFAULT 'otro',
            fecha TEXT NOT NULL, archivo TEXT DEFAULT '', observaciones TEXT DEFAULT '',
            FOREIGN KEY (id_animal) REFERENCES animales(id));
        CREATE TABLE IF NOT EXISTS notas_rapidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_animal INTEGER NOT NULL, contenido TEXT DEFAULT '', fecha_actualizacion TEXT NOT NULL,
            FOREIGN KEY (id_animal) REFERENCES animales(id));
        CREATE TABLE IF NOT EXISTS cobros_pendientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_registro INTEGER NOT NULL, id_animal INTEGER NOT NULL,
            servicios TEXT DEFAULT '[]', total REAL DEFAULT 0,
            created_by INTEGER, fecha TEXT NOT NULL,
            FOREIGN KEY (id_registro) REFERENCES registros_medicos(id),
            FOREIGN KEY (id_animal) REFERENCES animales(id)
        );
        CREATE TABLE IF NOT EXISTS insumos_utilizados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_registro INTEGER NOT NULL, id_producto INTEGER NOT NULL,
            cantidad INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (id_registro) REFERENCES registros_medicos(id),
            FOREIGN KEY (id_producto) REFERENCES productos(id)
        );
        CREATE TABLE IF NOT EXISTS stock_movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_producto INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            stock_anterior INTEGER NOT NULL DEFAULT 0,
            stock_nuevo INTEGER NOT NULL DEFAULT 0,
            referencia_tipo TEXT DEFAULT '',
            referencia_id INTEGER DEFAULT NULL,
            descripcion TEXT DEFAULT '',
            fecha TEXT NOT NULL,
            FOREIGN KEY (id_producto) REFERENCES productos(id)
        );
        CREATE TABLE IF NOT EXISTS servicio_insumos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_servicio INTEGER NOT NULL,
            id_producto INTEGER NOT NULL,
            cantidad INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (id_servicio) REFERENCES servicios_medicos(id),
            FOREIGN KEY (id_producto) REFERENCES productos(id)
        );
        CREATE TABLE IF NOT EXISTS combos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL, descripcion TEXT DEFAULT '',
            precio_total REAL NOT NULL DEFAULT 0, activo INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS combo_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_combo INTEGER NOT NULL,
            tipo_item TEXT NOT NULL,
            referencia_id INTEGER,
            nombre TEXT NOT NULL,
            cantidad INTEGER NOT NULL DEFAULT 1,
            precio_unitario REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (id_combo) REFERENCES combos(id)
        );
        CREATE TABLE IF NOT EXISTS proveedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL, contacto TEXT DEFAULT '',
            telefono TEXT DEFAULT '', email TEXT DEFAULT '',
            direccion TEXT DEFAULT '', ruc TEXT DEFAULT '', activo INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS ordenes_compra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_proveedor INTEGER NOT NULL,
            fecha TEXT NOT NULL, estado TEXT DEFAULT 'pendiente',
            total REAL NOT NULL DEFAULT 0, observaciones TEXT DEFAULT '',
            FOREIGN KEY (id_proveedor) REFERENCES proveedores(id)
        );
        CREATE TABLE IF NOT EXISTS orden_compra_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_orden INTEGER NOT NULL,
            id_producto INTEGER NOT NULL,
            cantidad INTEGER NOT NULL DEFAULT 1,
            precio_unitario REAL NOT NULL DEFAULT 0,
            subtotal REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (id_orden) REFERENCES ordenes_compra(id),
            FOREIGN KEY (id_producto) REFERENCES productos(id)
        );
        CREATE TABLE IF NOT EXISTS categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notas_credito (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_venta INTEGER NOT NULL,
            serie TEXT NOT NULL DEFAULT 'NC01',
            numero INTEGER NOT NULL DEFAULT 0,
            fecha TEXT NOT NULL,
            subtotal REAL NOT NULL DEFAULT 0,
            igv REAL NOT NULL DEFAULT 0,
            total REAL NOT NULL DEFAULT 0,
            motivo TEXT DEFAULT '',
            estado TEXT DEFAULT 'emitida',
            FOREIGN KEY (id_venta) REFERENCES ventas(id)
        );
        CREATE TABLE IF NOT EXISTS suscripcion_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estado TEXT DEFAULT 'inactivo',
            plan TEXT DEFAULT 'mensual',
            precio REAL DEFAULT 99,
            fecha_creacion TEXT,
            fecha_inicio TEXT,
            fecha_vencimiento TEXT,
            notas TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS suscripcion_pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            monto REAL NOT NULL,
            fecha_pago TEXT NOT NULL,
            metodo TEXT DEFAULT 'manual',
            comprobante TEXT DEFAULT '',
            notas TEXT DEFAULT '',
            registrado_por TEXT DEFAULT ''
        );
    '''
    _exec_script(conn, schema)
    conn.commit()

    admin = fetchone(conn, "SELECT id FROM usuarios WHERE username=?", ('admin',))
    if not admin:
        execute(conn, "INSERT INTO usuarios (username, password, nombre, rol) VALUES (?,?,?,?)",
                ('admin', hashlib.sha256(b'admin123').hexdigest(), 'Administrador', 'admin'))
    conn.commit()
    # Migrate plaintext passwords to hashed
    for u in fetchall(conn, "SELECT id, password FROM usuarios"):
        if u["password"] and len(u["password"]) != 64:
            execute(conn, "UPDATE usuarios SET password=? WHERE id=?",
                    (hashlib.sha256(u["password"].encode()).hexdigest(), u["id"]))
    conn.commit()

    if not _using_pg():
        migrations = [
            "ALTER TABLE duenos ADD COLUMN dni TEXT",
            "ALTER TABLE animales ADD COLUMN sexo TEXT DEFAULT ''",
            "ALTER TABLE animales ADD COLUMN color TEXT DEFAULT ''",
            "ALTER TABLE animales ADD COLUMN fecha_nacimiento TEXT",
            "ALTER TABLE animales ADD COLUMN esterilizado INTEGER DEFAULT 0",
            "ALTER TABLE citas ADD COLUMN tipo TEXT DEFAULT 'veterinaria'",
            "ALTER TABLE citas ADD COLUMN precio REAL DEFAULT 0",
            "ALTER TABLE ventas ADD COLUMN tipo_comprobante TEXT DEFAULT 'Boleta'",
            "ALTER TABLE ventas ADD COLUMN tipo_pago TEXT DEFAULT 'contado'",
            "ALTER TABLE ventas ADD COLUMN metodo_pago TEXT DEFAULT 'efectivo'",
            "ALTER TABLE registros_medicos ADD COLUMN anamnesis TEXT DEFAULT ''",
            "ALTER TABLE registros_medicos ADD COLUMN diagnostico_presuntivo TEXT DEFAULT ''",
            "ALTER TABLE registros_medicos ADD COLUMN diagnostico_definitivo TEXT DEFAULT ''",
            "ALTER TABLE registros_medicos ADD COLUMN exam_ecografia TEXT DEFAULT ''",
            "ALTER TABLE registros_medicos ADD COLUMN exam_radiografia TEXT DEFAULT ''",
            "ALTER TABLE registros_medicos ADD COLUMN exam_hemograma TEXT DEFAULT ''",
            "ALTER TABLE registros_medicos ADD COLUMN exam_bioquimico TEXT DEFAULT ''",
            "ALTER TABLE registros_medicos ADD COLUMN exam_orina TEXT DEFAULT ''",
            "ALTER TABLE registros_medicos ADD COLUMN exam_otros TEXT DEFAULT ''",
            "ALTER TABLE registros_medicos ADD COLUMN facturado INTEGER DEFAULT 0",
            "ALTER TABLE registros_medicos ADD COLUMN pendiente_cobro INTEGER DEFAULT 0",
            "ALTER TABLE registros_medicos ADD COLUMN cobrado_por INTEGER DEFAULT NULL",
            "ALTER TABLE registros_medicos ADD COLUMN id_venta INTEGER DEFAULT NULL",
            "ALTER TABLE registros_medicos ADD COLUMN proximo_control TEXT",
            "ALTER TABLE productos ADD COLUMN fecha_vencimiento TEXT",
            "ALTER TABLE ventas ADD COLUMN cliente_dni TEXT DEFAULT ''",
            "ALTER TABLE ventas ADD COLUMN cliente_nombre TEXT DEFAULT ''",
            "ALTER TABLE ventas ADD COLUMN cliente_telefono TEXT DEFAULT ''",
            "ALTER TABLE ventas ADD COLUMN descuento REAL DEFAULT 0",
            "ALTER TABLE ventas ADD COLUMN igv REAL DEFAULT 0",
            "ALTER TABLE ventas ADD COLUMN subtotal REAL DEFAULT 0",
            "ALTER TABLE ventas ADD COLUMN saldo_pendiente REAL DEFAULT 0",
            "ALTER TABLE ventas ADD COLUMN estado_pago TEXT DEFAULT 'pagado'",
            "ALTER TABLE venta_items ADD COLUMN descuento REAL DEFAULT 0",
            "ALTER TABLE venta_items ADD COLUMN descuento_tipo TEXT DEFAULT 'soles'",
            "ALTER TABLE citas ADD COLUMN hora TEXT DEFAULT ''",
            "ALTER TABLE productos ADD COLUMN stock_minimo INTEGER DEFAULT 5",
            "ALTER TABLE venta_items ADD COLUMN id_producto INTEGER DEFAULT NULL",
            "ALTER TABLE productos ADD COLUMN codigo_barras TEXT DEFAULT ''",
            "ALTER TABLE productos ADD COLUMN foto TEXT DEFAULT ''",
            "ALTER TABLE productos ADD COLUMN por_mayor INTEGER DEFAULT 0",
            "ALTER TABLE productos ADD COLUMN descuento_mayorista REAL DEFAULT 0",
            "ALTER TABLE productos ADD COLUMN colores TEXT DEFAULT ''",
            "ALTER TABLE productos ADD COLUMN en_catalogo INTEGER DEFAULT 1",
            "ALTER TABLE ventas ADD COLUMN serie TEXT DEFAULT 'B001'",
            "ALTER TABLE ventas ADD COLUMN numero INTEGER DEFAULT 0",
            "ALTER TABLE caja ADD COLUMN metodo_pago TEXT DEFAULT 'efectivo'",
            "ALTER TABLE caja ADD COLUMN observacion TEXT DEFAULT ''",
            "ALTER TABLE caja ADD COLUMN comprobante TEXT DEFAULT ''",
            "ALTER TABLE productos ADD COLUMN vende_por_kilo INTEGER DEFAULT 0",
            "ALTER TABLE productos ADD COLUMN precio_kilo REAL DEFAULT 0",
            "ALTER TABLE cobros_pendientes ADD COLUMN cobrado INTEGER DEFAULT 0",
            "ALTER TABLE cobros_pendientes ADD COLUMN cobrado_en TEXT DEFAULT ''",
            "ALTER TABLE cobros_pendientes ADD COLUMN metodo_pago TEXT DEFAULT 'efectivo'",
            "ALTER TABLE cobros_pendientes ADD COLUMN observacion TEXT DEFAULT ''",
            "ALTER TABLE cobros_pendientes ADD COLUMN comprobante TEXT DEFAULT ''",

        "ALTER TABLE ventas ADD COLUMN sunat_estado TEXT DEFAULT 'pendiente'",
        "ALTER TABLE ventas ADD COLUMN sunat_ticket TEXT DEFAULT ''",
        "ALTER TABLE ventas ADD COLUMN sunat_cdr_xml TEXT DEFAULT ''",
        "ALTER TABLE ventas ADD COLUMN sunat_hash TEXT DEFAULT ''",
        "ALTER TABLE ventas ADD COLUMN sunat_fecha_envio TEXT DEFAULT ''",
        "ALTER TABLE ventas ADD COLUMN cliente_direccion TEXT DEFAULT ''",
        "ALTER TABLE duenos ADD COLUMN ruc TEXT DEFAULT ''",
            "CREATE TABLE IF NOT EXISTS series (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT UNIQUE NOT NULL, serie TEXT NOT NULL, ultimo_numero INTEGER DEFAULT 0)",
        ]
        for m in migrations:
            try:
                conn.execute(m)
                conn.commit()
            except:
                pass

    conn.close()
    init_doctores_data()
    init_productos_default()
    init_servicios_grooming_default()
    init_servicios_medicos_default()
    init_combos_default()
    init_categorias_data()
    init_series_default()

def init_categorias_data():
    conn = get_db()
    existing = fetchone(conn, 'SELECT COUNT(*) as cnt FROM categorias')
    cnt = existing['cnt'] if existing else 0
    if cnt == 0:
        for name in ['General','Medicamentos','Alimentos','Accesorios','Higiene','Laboratorio','Cirug\u00eda']:
            try:
                execute(conn, "INSERT INTO categorias (nombre) VALUES (?)", (name,))
            except:
                pass
        conn.commit()
    conn.close()

def init_doctores_data():
    conn = get_db()
    existing = fetchone(conn, 'SELECT COUNT(*) as cnt FROM doctores')
    cnt = existing['cnt'] if existing else 0
    if cnt == 0:
        for name in ['Carlos Mijica', 'Teresa Buendia']:
            try:
                execute(conn, "INSERT INTO doctores (nombre) VALUES (?)", (name,))
            except:
                pass
        conn.commit()
    conn.close()

def init_productos_default():
    conn = get_db()
    existing = fetchone(conn, 'SELECT COUNT(*) as cnt FROM productos')
    cnt = existing['cnt'] if existing else 0
    if cnt == 0:
        defaults = [
            ('Alimento Premium Perro 15kg', 'Alimento balanceado', 85, 150, 10, 'Alimentos'),
            ('Alimento Premium Gato 7kg', 'Alimento balanceado', 60, 110, 10, 'Alimentos'),
            ('Antipulgas Frontline', 'Antipulgas', 35, 65, 20, 'Farmacia'),
            ('Desparasitante Interno', 'Desparasitante oral', 15, 30, 30, 'Farmacia'),
            ('Shampoo Medicado', 'Shampoo dermatologico', 22, 45, 15, 'Higiene'),
            ('Collar Isabelino', 'Collar de proteccion', 18, 35, 8, 'Accesorios'),
            ('Juguete Pelota', 'Juguete resistente', 10, 22, 25, 'Juguetes'),
            ('Cama para Perro M', 'Cama acolchonada', 55, 100, 5, 'Accesorios'),
            ('Correa Ajustable', 'Correa de paseo', 12, 28, 20, 'Accesorios'),
            ('Plato Doble Acero', 'Plato de acero', 15, 30, 12, 'Accesorios'),
        ]
        for p in defaults:
            execute(conn, 'INSERT INTO productos (nombre, descripcion, precio_compra, precio_venta, stock, categoria) VALUES (?,?,?,?,?,?)', p)
        conn.commit()
    conn.close()

def init_servicios_grooming_default():
    conn = get_db()
    existing = fetchone(conn, 'SELECT COUNT(*) as cnt FROM servicios_grooming')
    cnt = existing['cnt'] if existing else 0
    if cnt == 0:
        defaults = [
            ('Ba\u00f1o General', 'Ba\u00f1o con shampoo neutro', 25, 'Ba\u00f1o'),
            ('Ba\u00f1o Medicado', 'Ba\u00f1o con shampoo medicado', 35, 'Ba\u00f1o'),
            ('Corte Higienico', 'Corte areas sanitarias', 15, 'Corte'),
            ('Corte Completo', 'Corte completo segun raza', 45, 'Corte'),
            ('Ba\u00f1o + Corte', 'Ba\u00f1o general + corte completo', 55, 'Combo'),
            ('Cepillado Dental', 'Limpieza dental', 20, 'Higiene'),
            ('Limpieza de Oidos', 'Limpieza y revision', 15, 'Higiene'),
            ('Corte de Unas', 'Corte y limado', 10, 'Higiene'),
            ('Deslanado', 'Eliminacion pelo muerto', 20, 'Ba\u00f1o'),
        ]
        for s in defaults:
            execute(conn, 'INSERT INTO servicios_grooming (nombre, descripcion, precio, tipo) VALUES (?,?,?,?)', s)
        conn.commit()
    conn.close()

def init_combos_default():
    conn = get_db()
    existing = fetchone(conn, 'SELECT COUNT(*) as cnt FROM combos')
    cnt = existing['cnt'] if existing else 0
    if cnt == 0:
        execute(conn, "INSERT INTO combos (nombre,descripcion,precio_total) VALUES (?,?,?)",
            ('Paquete Vacunaci\u00f3n', 'Consulta general + vacuna + desparasitante interno', 85))
        cid = fetchone(conn, "SELECT MAX(id) as id FROM combos")["id"]
        execute(conn, "INSERT INTO combo_items (id_combo,tipo_item,referencia_id,nombre,cantidad,precio_unitario) VALUES (?,?,?,?,?,?)",
            (cid, 'servicio_medico', 1, 'Consulta General', 1, 50))
        execute(conn, "INSERT INTO combo_items (id_combo,tipo_item,referencia_id,nombre,cantidad,precio_unitario) VALUES (?,?,?,?,?,?)",
            (cid, 'servicio_medico', 11, 'Tratamiento Antipulgas', 1, 35))

        execute(conn, "INSERT INTO combos (nombre,descripcion,precio_total) VALUES (?,?,?)",
            ('Paquete Esterilizaci\u00f3n', 'Cirug\u00eda de esterilizaci\u00f3n + medicaci\u00f3n + collar isabelino', 320))
        cid = fetchone(conn, "SELECT MAX(id) as id FROM combos")["id"]
        execute(conn, "INSERT INTO combo_items (id_combo,tipo_item,referencia_id,nombre,cantidad,precio_unitario) VALUES (?,?,?,?,?,?)",
            (cid, 'servicio_medico', 6, 'Esterilizacion', 1, 250))
        execute(conn, "INSERT INTO combo_items (id_combo,tipo_item,referencia_id,nombre,cantidad,precio_unitario) VALUES (?,?,?,?,?,?)",
            (cid, 'servicio_medico', 8, 'Medicacion Inyectable', 1, 25))

        execute(conn, "INSERT INTO combos (nombre,descripcion,precio_total) VALUES (?,?,?)",
            ('Paquete Ba\u00f1o Completo', 'Ba\u00f1o general + corte completo + corte de u\u00f1as', 65))
        cid = fetchone(conn, "SELECT MAX(id) as id FROM combos")["id"]
        execute(conn, "INSERT INTO combo_items (id_combo,tipo_item,referencia_id,nombre,cantidad,precio_unitario) VALUES (?,?,?,?,?,?)",
            (cid, 'servicio_grooming', 1, 'Ba\u00f1o General', 1, 25))
        execute(conn, "INSERT INTO combo_items (id_combo,tipo_item,referencia_id,nombre,cantidad,precio_unitario) VALUES (?,?,?,?,?,?)",
            (cid, 'servicio_grooming', 4, 'Corte Completo', 1, 45))
        execute(conn, "INSERT INTO combo_items (id_combo,tipo_item,referencia_id,nombre,cantidad,precio_unitario) VALUES (?,?,?,?,?,?)",
            (cid, 'servicio_grooming', 8, 'Corte de Unas', 1, 10))

        execute(conn, "INSERT INTO combos (nombre,descripcion,precio_total) VALUES (?,?,?)",
            ('Kit Higiene Completo', 'Shampoo medicado + cepillado dental + limpieza de o\u00eddos', 75))
        cid = fetchone(conn, "SELECT MAX(id) as id FROM combos")["id"]
        execute(conn, "INSERT INTO combo_items (id_combo,tipo_item,referencia_id,nombre,cantidad,precio_unitario) VALUES (?,?,?,?,?,?)",
            (cid, 'producto', 5, 'Shampoo Medicado', 1, 45))
        execute(conn, "INSERT INTO combo_items (id_combo,tipo_item,referencia_id,nombre,cantidad,precio_unitario) VALUES (?,?,?,?,?,?)",
            (cid, 'servicio_grooming', 6, 'Cepillado Dental', 1, 20))
        execute(conn, "INSERT INTO combo_items (id_combo,tipo_item,referencia_id,nombre,cantidad,precio_unitario) VALUES (?,?,?,?,?,?)",
            (cid, 'servicio_grooming', 7, 'Limpieza de Oidos', 1, 15))

        conn.commit()
    conn.close()

def init_servicios_medicos_default():
    conn = get_db()
    existing = fetchone(conn, 'SELECT COUNT(*) as cnt FROM servicios_medicos')
    cnt = existing['cnt'] if existing else 0
    if cnt == 0:
        defaults = [
            ('Consulta General', 'Consulta veterinaria general', 50, 'consulta'),
            ('Consulta de Control', 'Consulta de seguimiento', 35, 'consulta'),
            ('Consulta de Urgencia', 'Atencion veterinaria de urgencia', 80, 'consulta'),
            ('Cirugia Menor', 'Cirugia ambulatoria menor', 150, 'cirugia'),
            ('Cirugia Mayor', 'Cirugia general con anestesia', 400, 'cirugia'),
            ('Esterilizacion', 'Cirugia de esterilizacion', 250, 'cirugia'),
            ('Hospitalizacion (dia)', 'Hospitalizacion por dia', 120, 'hospitalizacion'),
            ('Medicacion Inyectable', 'Aplicacion de medicamento inyectable', 25, 'medicacion'),
            ('Medicacion Oral', 'Medicamento oral recetado', 0, 'medicacion'),
            ('Curacion de Heridas', 'Curacion y curado de heridas', 40, 'procedimiento'),
            ('Tratamiento Antipulgas', 'Aplicacion de tratamiento antipulgas', 35, 'medicacion'),
            ('Analisis de Laboratorio', 'Examen de laboratorio basico', 60, 'laboratorio'),
            ('Ecografia', 'Ecografia abdominal', 100, 'laboratorio'),
            ('Radiografia', 'Rayos X (por placa)', 80, 'laboratorio'),
        ]
        for s in defaults:
            execute(conn, "INSERT INTO servicios_medicos (nombre, descripcion, precio, tipo) VALUES (?,?,?,?)", s)
        conn.commit()
    conn.close()

def get_categorias(conn=None):
    close = conn is None
    if close:
        conn = get_db()
    cats = fetchall(conn, "SELECT * FROM categorias ORDER BY nombre")
    if close:
        conn.close()
    return [c["nombre"] for c in cats]

def backup_database():
    if _using_pg():
        return
    import shutil
    db_path = DB_PATH
    backup_dir = os.path.join(os.path.dirname(DB_PATH), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    if os.path.exists(db_path):
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f'veterinaria_{ts}.db')
        shutil.copy2(db_path, backup_path)
        backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.db')])
        while len(backups) > 10:
            os.remove(os.path.join(backup_dir, backups.pop(0)))

def init_series_default():
    conn = get_db()
    for tipo, serie in [('Boleta', 'B001'), ('Factura', 'F001'), ('Nota de Venta', 'NV001'), ('Nota Credito', 'NC01')]:
        try:
            execute(conn, "INSERT INTO series (tipo, serie, ultimo_numero) VALUES (?,?,0)", (tipo, serie))
        except:
            pass
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print(f'Base de datos inicializada: {DB_PATH}')
