import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import os
import shutil
import re
from datetime import date, datetime
import json
from PIL import Image, ImageTk


def center_dialog(w, pw):
    w.update_idletasks()
    x = pw.winfo_x() + (pw.winfo_width() - w.winfo_width()) // 2
    y = pw.winfo_y() + (pw.winfo_height() - w.winfo_height()) // 2
    w.geometry("+%d+%d" % (x, y))


def add_keyboard_shortcuts(dialog, save_cb):
    dialog.bind("<Escape>", lambda e: dialog.destroy())
    dialog.bind("<Control-Return>", lambda e: save_cb())


def validate_required(entries, labels):
    for e, lbl in zip(entries, labels):
        if not e.get().strip():
            messagebox.showerror("Error", f"{lbl} es obligatorio")
            return False
    return True


def auto_backup_db():
    backup_dir = os.path.join(os.path.dirname(DB_PATH), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    today = date.today().isoformat()
    backup_file = os.path.join(backup_dir, f"veterinaria_backup_{today}.db")
    if os.path.exists(backup_file):
        return
    try:
        shutil.copy2(DB_PATH, backup_file)
    except:
        pass
class AutocompleteEntry(tk.Frame):
    def __init__(self, master=None, full_values=None, width=37, font=None, **kwargs):
        super().__init__(master, **kwargs)
        self._full_values = full_values or []
        self._selected_value = ""
        self._font = font or ("Segoe UI", 10)
        self._top = None

        self.entry = tk.Entry(self, width=width, font=self._font)
        self.entry.pack(fill="x")
        self.entry.bind("<KeyRelease>", self._on_keyrelease)
        self.entry.bind("<FocusOut>", self._on_focusout)

    def get(self):
        return self.entry.get()

    def set(self, value):
        self.entry.delete(0, "end")
        self.entry.insert(0, value)
        self._selected_value = value

    def set_full_values(self, values):
        self._full_values = list(values)

    def _hide_top(self):
        if self._top:
            self._top.destroy()
            self._top = None

    def _on_keyrelease(self, event):
        if event.keysym in ("Up", "Down", "Return", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R", "Escape"):
            return
        typed = self.entry.get().lower()
        self._hide_top()
        if not typed:
            matches = list(self._full_values)
        else:
            matches = [v for v in self._full_values if typed in v.lower()]
        if not matches:
            return
        self._top = tk.Toplevel(self.master)
        self._top.wm_overrideredirect(True)
        self._top.wm_geometry("+%d+%d" % (self.winfo_rootx(), self.winfo_rooty() + self.entry.winfo_height()))
        listbox = tk.Listbox(self._top, height=min(len(matches), 6), font=self._font,
                             exportselection=False, activestyle="none")
        listbox.pack(fill="both", expand=True)
        for v in matches:
            listbox.insert("end", v)

        def on_select(ev=None):
            sel = listbox.curselection()
            if sel:
                val = listbox.get(sel[0])
                self.entry.delete(0, "end")
                self.entry.insert(0, val)
                self._selected_value = val
            self._hide_top()
            self.entry.focus_set()

        listbox.bind("<ButtonRelease-1>", on_select)
        listbox.bind("<Return>", on_select)
        self._top.bind("<Escape>", lambda e: self._hide_top())

    def _on_focusout(self, event):
        self.after(400, self._hide_top)


DB_PATH = os.path.join(os.path.dirname(__file__), "veterinaria.db")
PHOTOS_DIR = os.path.join(os.path.dirname(__file__), "photos")
EXAMENES_DIR = os.path.join(os.path.dirname(__file__), "examenes")

class App:
    def __init__(self, root):
        self.root = root
        self.root.title('SCRIPTYFY V.02 - Historial Clinico')
        self.root.state('zoomed')
        self.root.configure(bg='#e8edf2')
        self._dark_mode = False
        self._theme_bg = '#e8edf2'
        self._caja_abierta = False
        self._saldo_inicial = 0.0
        os.makedirs(PHOTOS_DIR, exist_ok=True)
        os.makedirs(EXAMENES_DIR, exist_ok=True)
        auto_backup_db()
        self._init_tables()
        self._init_doctores_data()
        self._init_productos_default()
        self._init_servicios_grooming_default()

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', rowheight=28, font=('Segoe UI', 10))
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))

        self.build_menu()
        self.show_dashboard()

    def get_db(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        conn = self.get_db()
        conn.executescript('''
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
                hora TEXT,
                peso REAL,
                doctor TEXT,
                diagnostico TEXT,
                tratamiento TEXT,
                observaciones TEXT,
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
                stock INTEGER NOT NULL DEFAULT 0, categoria TEXT DEFAULT 'General', activo INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS servicios_grooming (
                id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, descripcion TEXT DEFAULT '',
                precio REAL NOT NULL DEFAULT 0, duracion_minutos INTEGER DEFAULT 30, tipo TEXT DEFAULT 'Baño'
            );
            CREATE TABLE IF NOT EXISTS historial_grooming (
                id INTEGER PRIMARY KEY AUTOINCREMENT, id_animal INTEGER NOT NULL, id_servicio INTEGER,
                fecha TEXT NOT NULL, observaciones TEXT DEFAULT '', precio REAL NOT NULL DEFAULT 0,
                estilista TEXT DEFAULT '',
                FOREIGN KEY (id_animal) REFERENCES animales(id),
                FOREIGN KEY (id_servicio) REFERENCES servicios_grooming(id)
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
                fecha TEXT NOT NULL,
                tipo TEXT NOT NULL,
                concepto TEXT,
                monto REAL NOT NULL,
                referencia_tipo TEXT,
                referencia_id INTEGER
            );
        ''')
        conn.commit()
        try: conn.execute('ALTER TABLE duenos ADD COLUMN dni TEXT'); conn.commit()
        except: pass
        try: conn.execute("ALTER TABLE animales ADD COLUMN sexo TEXT DEFAULT ''"); conn.commit()
        except: pass
        try: conn.execute("ALTER TABLE animales ADD COLUMN color TEXT DEFAULT ''"); conn.commit()
        except: pass
        try: conn.execute('ALTER TABLE animales ADD COLUMN fecha_nacimiento TEXT'); conn.commit()
        except: pass
        try: conn.execute('ALTER TABLE animales ADD COLUMN esterilizado INTEGER DEFAULT 0'); conn.commit()
        except: pass
        try: conn.execute("ALTER TABLE citas ADD COLUMN tipo TEXT DEFAULT 'veterinaria'"); conn.commit()
        except: pass
        try: conn.execute('ALTER TABLE citas ADD COLUMN precio REAL DEFAULT 0'); conn.commit()
        except: pass
        conn.close()

    def _init_doctores_data(self):
        conn = self.get_db()
        existing = conn.execute('SELECT COUNT(*) FROM doctores').fetchone()[0]
        if existing == 0:
            for name in ['Carlos Mijica', 'Teresa Buendia']:
                conn.execute('INSERT OR IGNORE INTO doctores (nombre) VALUES (?)', (name,))
            conn.commit()
        conn.close()

    def _init_productos_default(self):
        conn = self.get_db()
        existing = conn.execute('SELECT COUNT(*) FROM productos').fetchone()[0]
        if existing == 0:
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
                conn.execute('INSERT INTO productos (nombre, descripcion, precio_compra, precio_venta, stock, categoria) VALUES (?,?,?,?,?,?)', p)
            conn.commit()
        conn.close()

    def _init_servicios_grooming_default(self):
        conn = self.get_db()
        existing = conn.execute('SELECT COUNT(*) FROM servicios_grooming').fetchone()[0]
        if existing == 0:
            defaults = [
                ('Baño General', 'Baño con shampoo neutro', 25, 'Baño'),
                ('Baño Medicado', 'Baño con shampoo medicado', 35, 'Baño'),
                ('Corte Higienico', 'Corte areas sanitarias', 15, 'Corte'),
                ('Corte Completo', 'Corte completo segun raza', 45, 'Corte'),
                ('Baño + Corte', 'Baño general + corte completo', 55, 'Combo'),
                ('Cepillado Dental', 'Limpieza dental', 20, 'Higiene'),
                ('Limpieza de Oidos', 'Limpieza y revision', 15, 'Higiene'),
                ('Corte de Unas', 'Corte y limado', 10, 'Higiene'),
                ('Deslanado', 'Eliminacion pelo muerto', 20, 'Baño'),
            ]
            for s in defaults:
                conn.execute('INSERT INTO servicios_grooming (nombre, descripcion, precio, tipo) VALUES (?,?,?,?)', s)
            conn.commit()
        conn.close()

    def get_doctores(self):
        conn = self.get_db()
        rows = conn.execute('SELECT nombre FROM doctores ORDER BY nombre').fetchall()
        conn.close()
        return [r['nombre'] for r in rows]

    def manage_doctores_dialog(self, callback=None):
        dialog = tk.Toplevel(self.root)
        dialog.title('Gestionar Doctores')
        dialog.geometry('360x280')
        dialog.resizable(False, False)
        dialog.configure(bg='#e8edf2')
        dialog.transient(self.root)
        dialog.grab_set()
        center_dialog(dialog, self.root)

        tk.Label(dialog, text='Doctores', font=('Segoe UI', 12, 'bold'),
                 bg='#e8edf2', fg='#2c3e50').pack(pady=(12, 5))

        lb = tk.Listbox(dialog, font=('Segoe UI', 10), height=8)
        lb.pack(fill='both', expand=True, padx=15, pady=5)

        def refresh():
            lb.delete(0, 'end')
            for d in self.get_doctores():
                lb.insert('end', d)

        refresh()

        btn_frame = tk.Frame(dialog, bg='#e8edf2')
        btn_frame.pack(fill='x', padx=15, pady=(0, 12))

        tk.Button(btn_frame, text='Agregar', bg='#2ecc71', fg='white',
                  font=('Segoe UI', 9), relief='flat', padx=12, pady=3,
                  cursor='hand2',
                  command=lambda: self._add_doctor_dialog(dialog, refresh, callback)
                  ).pack(side='left', padx=2)
        tk.Button(btn_frame, text='Eliminar', bg='#e74c3c', fg='white',
                  font=('Segoe UI', 9), relief='flat', padx=12, pady=3,
                  cursor='hand2',
                  command=lambda: self._delete_doctor(lb, dialog, refresh, callback)
                  ).pack(side='left', padx=2)
        tk.Button(btn_frame, text='Cerrar', bg='#95a5a6', fg='white',
                  font=('Segoe UI', 9), relief='flat', padx=12, pady=3,
                  cursor='hand2', command=dialog.destroy).pack(side='right', padx=2)

    def _add_doctor_dialog(self, parent_dialog, refresh_cb, final_cb=None):
        d2 = tk.Toplevel(parent_dialog)
        d2.title('Nuevo Doctor')
        d2.geometry('300x120')
        d2.resizable(False, False)
        d2.configure(bg='#e8edf2')
        d2.transient(parent_dialog)
        d2.grab_set()
        center_dialog(d2, parent_dialog)
        tk.Label(d2, text='Nombre del Doctor:', bg='#e8edf2', font=('Segoe UI', 10)).pack(pady=(15, 5))
        e_name = tk.Entry(d2, width=35, font=('Segoe UI', 10))
        e_name.pack()
        e_name.focus_set()
        def save():
            name = e_name.get().strip()
            if not name:
                messagebox.showwarning('Error', 'Ingrese un nombre')
                return
            conn = self.get_db()
            try:
                conn.execute('INSERT INTO doctores (nombre) VALUES (?)', (name,))
                conn.commit()
                conn.close()
                d2.destroy()
                refresh_cb()
                if final_cb:
                    final_cb()
            except sqlite3.IntegrityError:
                conn.close()
                messagebox.showwarning('Error', 'Ese doctor ya existe')
        add_keyboard_shortcuts(d2, save)
        tk.Button(d2, text='Guardar', bg='#2ecc71', fg='white',
                  font=('Segoe UI', 10), relief='flat', padx=15, pady=3,
                  command=save, cursor='hand2').pack(pady=(10, 5))

    def _delete_doctor(self, lb, parent_dialog, refresh_cb, final_cb=None):
        sel = lb.curselection()
        if not sel:
            messagebox.showwarning('Error', 'Seleccione un doctor')
            return
        name = lb.get(sel[0])
        if messagebox.askyesno('Confirmar', f'Eliminar a {name}?'):
            conn = self.get_db()
            conn.execute('DELETE FROM doctores WHERE nombre=?', (name,))
            conn.commit()
            conn.close()
            refresh_cb()
            if final_cb:
                final_cb()

    def clear_frame(self):
        for w in self.root.winfo_children():
            if w != self.menu_frame:
                w.destroy()

    def build_menu(self):
        self.menu_frame = tk.Frame(self.root, bg='#2c3e50', width=200)
        self.menu_frame.pack(side='left', fill='y')
        self.menu_frame.pack_propagate(False)

        tk.Label(self.menu_frame, text='SCRIPTYFY', font=('Segoe UI', 13, 'bold'),
                 bg='#2c3e50', fg='white').pack(pady=(15, 5))
        tk.Label(self.menu_frame, text='V.02', font=('Segoe UI', 9),
                 bg='#2c3e50', fg='#1abc9c').pack(pady=(0, 15))

        nav_buttons = [
            ('🏠 Inicio', self.show_dashboard),
            ('📋 Historial Clinico', self.show_medical_history),
            ('✂️ Peluqueria/Grooming', self.show_grooming),
            ('📦 Productos', self.show_productos),
            ('💰 Ventas / Caja', self.show_ventas),
        ]
        for txt, cmd in nav_buttons:
            tk.Button(self.menu_frame, text=txt, font=('Segoe UI', 10),
                      bg='#34495e', fg='white', relief='flat', anchor='w', padx=15,
                      activebackground='#1abc9c', activeforeground='white',
                      command=cmd, cursor='hand2').pack(fill='x', padx=8, pady=3)

        tk.Frame(self.menu_frame, bg='#34495e', height=1).pack(fill='x', padx=15, pady=15)

        quick_buttons = [
            ('+ Dueño', self.add_owner_dialog, '#e67e22'),
            ('+ Cita', self.add_appointment_dialog, '#f39c12'),
            ('+ Consulta', self.add_medical_record_dialog, '#1abc9c'),
            ('Doctores', lambda: self.manage_doctores_dialog(), '#3498db'),
        ]
        for txt, cmd, color in quick_buttons:
            tk.Button(self.menu_frame, text=txt, font=('Segoe UI', 9),
                      bg=color, fg='white', relief='flat', anchor='w', padx=15,
                      command=cmd, cursor='hand2').pack(fill='x', padx=8, pady=2)

    def toggle_theme(self):
        self._dark_mode = not self._dark_mode
        if self._dark_mode:
            self._theme_bg = '#2c3e50'
            self.root.configure(bg='#2c3e50')
        else:
            self._theme_bg = '#e8edf2'
            self.root.configure(bg='#e8edf2')

    # ---------- INICIO ----------
    def show_dashboard(self):
        self.clear_frame()
        main = tk.Frame(self.root, bg='#f0f4f8')
        main.pack(fill='both', expand=True, padx=40, pady=30)

        logo_path = os.path.join('photos', 'logo.png')
        self._dashboard_logo = None
        if os.path.exists(logo_path):
            pil_img = Image.open(logo_path).resize((100, 100), Image.LANCZOS)
            self._dashboard_logo = ImageTk.PhotoImage(pil_img)

        header = tk.Frame(main, bg='#f0f4f8')
        header.pack(anchor='w', pady=(0, 20))
        if self._dashboard_logo:
            tk.Label(header, image=self._dashboard_logo, bg='#f0f4f8').pack(side='left', padx=(0, 15))
        tk.Label(header, text='Panel Principal', font=('Segoe UI', 16, 'bold'),
                 bg='#f0f4f8', fg='#2c3e50').pack(side='left')

        conn = self.get_db()
        total_d = conn.execute('SELECT COUNT(*) FROM duenos').fetchone()[0]
        total_a = conn.execute('SELECT COUNT(*) FROM animales').fetchone()[0]
        citas_vet_hoy = conn.execute(
            "SELECT COUNT(*) FROM citas WHERE fecha = ? AND estado = 'pendiente' AND (tipo = 'veterinaria' OR tipo = '')",
            (str(date.today()),)).fetchone()[0]
        citas_grooming_hoy = conn.execute(
            "SELECT COUNT(*) FROM citas WHERE fecha = ? AND estado = 'pendiente' AND tipo = 'grooming'",
            (str(date.today()),)).fetchone()[0]
        ingresos_hoy = conn.execute(
            'SELECT COALESCE(SUM(total), 0) FROM ventas WHERE fecha = ?',
            (str(date.today()),)).fetchone()[0]
        stock_bajo = conn.execute(
            'SELECT COUNT(*) FROM productos WHERE stock <= 3 AND activo = 1').fetchone()[0]

        citas_pendientes = conn.execute(
            'SELECT c.id, a.nombre as animal, d.nombre as dueno, c.fecha, c.motivo, c.tipo '
            'FROM citas c JOIN animales a ON c.id_animal = a.id '
            'JOIN duenos d ON c.id_dueno = d.id '
            "WHERE c.estado = 'pendiente' ORDER BY c.fecha ASC").fetchall()
        productos_bajo = conn.execute(
            'SELECT nombre, stock FROM productos WHERE stock <= 3 AND activo = 1 ORDER BY stock ASC').fetchall()
        conn.close()

        cards = tk.Frame(main, bg='#f0f4f8')
        cards.pack(fill='x')
        for bg_c, val, lab in [('#3498db', total_d, 'Dueños registrados'),
                                ('#2ecc71', total_a, 'Animales registrados'),
                                ('#f39c12', citas_vet_hoy, 'Citas Vet Hoy'),
                                ('#9b59b6', citas_grooming_hoy, 'Citas Grooming Hoy'),
                                ('#1abc9c', f'S/.{ingresos_hoy:.2f}', 'Ingresos Hoy'),
                                ('#e74c3c', stock_bajo, 'Stock Bajo')]:
            card = tk.Frame(cards, bg='white', highlightbackground='#ddd',
                            highlightthickness=1, padx=20, pady=15)
            card.pack(side='left', fill='x', expand=True, padx=8)
            tk.Label(card, text=str(val), font=('Segoe UI', 36, 'bold'),
                     bg='white', fg=bg_c).pack()
            tk.Label(card, text=lab, font=('Segoe UI', 10), bg='white', fg='#7f8c8d').pack()

        bottom_split = tk.Frame(main, bg='#f0f4f8')
        bottom_split.pack(fill='both', expand=True, pady=(15, 0))

        left_col = tk.Frame(bottom_split, bg='#f0f4f8')
        left_col.pack(side='left', fill='both', expand=True, padx=(0, 8))

        citas_frame = tk.Frame(left_col, bg='#f0f4f8')
        citas_frame.pack(fill='x', pady=(0, 10))
        tk.Label(citas_frame, text='Citas Pendientes', font=('Segoe UI', 14, 'bold'),
                 bg='#f0f4f8', fg='#2c3e50').pack(anchor='w', pady=(0, 10))
        if citas_pendientes:
            cols = ('fecha', 'animal', 'dueno', 'motivo', 'tipo')
            tree = ttk.Treeview(citas_frame, columns=cols, show='headings', height=8)
            tree.heading('fecha', text='Fecha')
            tree.heading('animal', text='Animal')
            tree.heading('dueno', text='Dueño')
            tree.heading('motivo', text='Motivo')
            tree.heading('tipo', text='Tipo')
            tree.column('fecha', width=90)
            tree.column('animal', width=160)
            tree.column('dueno', width=160)
            tree.column('motivo', width=200)
            tree.column('tipo', width=80)
            tree.pack(fill='x')
            for r in citas_pendientes:
                tipo = r['tipo'] or 'veterinaria'
                tree.insert('', 'end', values=(r['fecha'], r['animal'], r['dueno'], r['motivo'], tipo))
            tree.tag_configure('vet', background='#d6eaf8')
            tree.tag_configure('groom', background='#e8daef')
            for item in tree.get_children():
                vals = tree.item(item, 'values')
                if vals[4] == 'grooming':
                    tree.item(item, tags=('groom',))
                else:
                    tree.item(item, tags=('vet',))
            def marcar_atendida():
                sel = tree.selection()
                if not sel: return
                vals = tree.item(sel[0], 'values')
                c = self.get_db()
                c.execute("UPDATE citas SET estado='atendida' WHERE fecha=? AND id_animal IN "
                          "(SELECT id FROM animales WHERE nombre=? AND id_dueno IN "
                          "(SELECT id FROM duenos WHERE nombre=?))", (vals[0], vals[1], vals[2]))
                c.commit()
                c.close()
                self.show_dashboard()
                messagebox.showinfo('Exito', 'Cita marcada como atendida')
            btn_frame = tk.Frame(citas_frame, bg='#e8edf2')
            btn_frame.pack(fill='x', pady=(5, 0))
            tk.Button(btn_frame, text='Marcar como Atendida', bg='#2ecc71', fg='white',
                      font=('Segoe UI', 9), relief='flat', padx=12, pady=3,
                      command=marcar_atendida, cursor='hand2').pack(side='left')
        else:
            tk.Label(citas_frame, text='No hay citas pendientes',
                     bg='#f0f4f8', fg='#999', font=('Segoe UI', 10)).pack(anchor='w')

        if productos_bajo:
            stock_frame = tk.Frame(left_col, bg='#f0f4f8')
            stock_frame.pack(fill='x')
            tk.Label(stock_frame, text='Stock Bajo', font=('Segoe UI', 12, 'bold'),
                     bg='#f0f4f8', fg='#e74c3c').pack(anchor='w', pady=(0, 5))
            sf = tk.Frame(stock_frame, bg='white', highlightbackground='#ddd',
                          highlightthickness=1, padx=10, pady=5)
            sf.pack(fill='x')
            for p in productos_bajo:
                tk.Label(sf, text=f'  {p["nombre"]} - Stock: {p["stock"]}',
                         font=('Segoe UI', 9), bg='white', fg='#e74c3c', anchor='w').pack(fill='x', pady=1)

        right_col = tk.Frame(bottom_split, bg='#f0f4f8')
        right_col.pack(side='left', fill='both', expand=True)

        rec_frame = tk.Frame(right_col, bg='#f0f4f8')
        rec_frame.pack(fill='x', pady=(0, 10))
        tk.Label(rec_frame, text='Recordatorios', font=('Segoe UI', 14, 'bold'),
                 bg='#f0f4f8', fg='#e67e22').pack(anchor='w', pady=(0, 8))
        conn_rec = self.get_db()
        hoy = date.today()
        prox_citas = conn_rec.execute(
            'SELECT a.nombre, c.fecha, c.motivo FROM citas c JOIN animales a ON c.id_animal = a.id '
            "WHERE c.fecha BETWEEN ? AND ? AND c.estado='pendiente' ORDER BY c.fecha",
            (hoy.isoformat(), date(hoy.year + (hoy.month + 1 > 12), ((hoy.month + 1) % 12) or 12, 1).isoformat())).fetchall()
        vac_pend = conn_rec.execute(
            'SELECT v.nombre as vacuna, a.nombre as animal, v.proxima_dosis '
            'FROM vacunas v JOIN animales a ON v.id_animal = a.id '
            "WHERE v.proxima_dosis IS NOT NULL AND v.proxima_dosis <= ? ORDER BY v.proxima_dosis",
            (hoy.isoformat(),)).fetchall()
        conn_rec.close()
        rec_inner = tk.Frame(rec_frame, bg='white', highlightbackground='#ddd',
                             highlightthickness=1, padx=10, pady=8)
        rec_inner.pack(fill='x')
        items_list = []
        for r in prox_citas:
            items_list.append(f'Proxima cita: {r["nombre"]} - {r["fecha"]} ({r["motivo"]})')
        for r in vac_pend:
            items_list.append(f'Vacuna pendiente: {r["animal"]} - {r["vacuna"]} (vencida: {r["proxima_dosis"]})')
        if items_list:
            for txt in items_list:
                tk.Label(rec_inner, text='  ' + txt, font=('Segoe UI', 9),
                         bg='white', fg='#e67e22', anchor='w').pack(fill='x', pady=1)
        else:
            tk.Label(rec_inner, text='  No hay recordatorios pendientes',
                     font=('Segoe UI', 9), bg='white', fg='#999').pack(anchor='w')

        chart_frame = tk.Frame(right_col, bg='white', highlightbackground='#ddd',
                               highlightthickness=1)
        chart_frame.pack(fill='x', pady=(0, 10))
        tk.Label(chart_frame, text='Estadisticas', font=('Segoe UI', 11, 'bold'),
                 bg='white', fg='#2c3e50', padx=10, pady=8).pack(anchor='w')
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            conn_stats = self.get_db()
            rows_mes = conn_stats.execute(
                "SELECT strftime('%Y-%m', fecha) as mes, COUNT(*) as total "
                'FROM registros_medicos GROUP BY mes ORDER BY mes').fetchall()
            rows_esp = conn_stats.execute(
                'SELECT especie, COUNT(*) as total FROM animales GROUP BY especie').fetchall()
            rows_doc = conn_stats.execute(
                "SELECT doctor, COUNT(*) as total FROM registros_medicos WHERE doctor IS NOT NULL AND doctor != '' GROUP BY doctor ORDER BY total DESC").fetchall()
            conn_stats.close()

            fig = Figure(figsize=(5, 3.5), dpi=85, facecolor='white')

            ax1 = fig.add_subplot(221)
            if rows_mes:
                meses = [r['mes'] for r in rows_mes]
                totales = [r['total'] for r in rows_mes]
                ax1.bar(meses, totales, color='#3498db', width=0.6)
                ax1.set_xticks(range(len(meses)))
                ax1.set_xticklabels(meses, rotation=45, fontsize=6)
                ax1.set_title('Consultas por Mes', fontsize=9)
            else:
                ax1.text(0.5, 0.5, 'Sin datos', ha='center', va='center', fontsize=9)
                ax1.set_title('Consultas por Mes', fontsize=9)

            ax2 = fig.add_subplot(222)
            if rows_esp:
                labels = [r['especie'] for r in rows_esp]
                sizes = [r['total'] for r in rows_esp]
                colors_pie = ['#2ecc71', '#3498db', '#e74c3c', '#f39c12', '#9b59b6']
                ax2.pie(sizes, labels=labels, autopct='%1.0f%%', colors=colors_pie[:len(sizes)],
                        startangle=90, textprops={'fontsize': 8})
                ax2.set_title('Pacientes por Especie', fontsize=9)
            else:
                ax2.text(0.5, 0.5, 'Sin datos', ha='center', va='center', fontsize=9)
                ax2.set_title('Pacientes por Especie', fontsize=9)

            ax3 = fig.add_subplot(223)
            if rows_doc:
                docs = [r['doctor'] for r in rows_doc]
                counts = [r['total'] for r in rows_doc]
                ax3.barh(docs, counts, color='#9b59b6', height=0.5)
                ax3.set_xlabel('Consultas', fontsize=8)
                ax3.set_title('Consultas por Doctor', fontsize=9)
            else:
                ax3.text(0.5, 0.5, 'Sin datos', ha='center', va='center', fontsize=9)
                ax3.set_title('Consultas por Doctor', fontsize=9)

            fig.tight_layout(pad=2)
            canvas_chart = FigureCanvasTkAgg(fig, master=chart_frame)
            canvas_chart.draw()
            canvas_chart.get_tk_widget().pack(fill='x', padx=5, pady=5)
        except Exception as ex:
            tk.Label(chart_frame, text=f'Grafico no disponible: {ex}', bg='white',
                     fg='#999').pack(expand=True)

        feed_frame = tk.Frame(right_col, bg='white', highlightbackground='#ddd',
                              highlightthickness=1)
        feed_frame.pack(fill='x')
        tk.Label(feed_frame, text='Actividad Reciente', font=('Segoe UI', 11, 'bold'),
                 bg='white', fg='#2c3e50', padx=10, pady=8).pack(anchor='w')
        conn3 = self.get_db()
        ultimas = conn3.execute(
            'SELECT rm.fecha, rm.hora, a.nombre as animal, rm.diagnostico '
            'FROM registros_medicos rm JOIN animales a ON rm.id_animal = a.id '
            'ORDER BY rm.fecha DESC, rm.hora DESC LIMIT 10').fetchall()
        nuevos = conn3.execute(
            'SELECT id, nombre, especie, foto FROM animales ORDER BY id DESC LIMIT 5').fetchall()
        conn3.close()
        feed_inner = tk.Frame(feed_frame, bg='white')
        feed_inner.pack(fill='both', expand=True, padx=8, pady=5)
        if ultimas:
            tk.Label(feed_inner, text='Ultimas Consultas', font=('Segoe UI', 9, 'bold'),
                     bg='white', fg='#7f8c8d').pack(anchor='w', pady=(0, 3))
            for r in ultimas[:5]:
                tk.Label(feed_inner,
                    text=f"{r['fecha']} - {r['animal']}: {r['diagnostico']}",
                    font=('Segoe UI', 9), bg='white', fg='#555',
                    anchor='w', wraplength=300, justify='left').pack(fill='x', pady=1)
        if nuevos:
            tk.Label(feed_inner, text='\nNuevos Pacientes', font=('Segoe UI', 9, 'bold'),
                     bg='white', fg='#7f8c8d').pack(anchor='w', pady=(5, 3))
            for r in nuevos:
                tk.Label(feed_inner, text=f"{r['nombre']} ({r['especie']})",
                         font=('Segoe UI', 9), bg='white', fg='#555',
                         anchor='w').pack(fill='x', pady=1)

        tk.Button(main, text='Ir a Historial Clinico', bg='#1abc9c', fg='white',
                  font=('Segoe UI', 12), relief='flat', padx=30, pady=12,
                  command=self.show_medical_history, cursor='hand2').pack(pady=40)
    def show_medical_history(self):
        self.clear_frame()
        main = tk.Frame(self.root, bg="#f0f4f8")
        main.pack(fill="both", expand=True, padx=20, pady=15)

        # Top bar
        top_bar = tk.Frame(main, bg="#f0f4f8")
        top_bar.pack(fill="x")
        tk.Label(top_bar, text="Historial Clinico", font=("Segoe UI", 16, "bold"),
                 bg="#f0f4f8", fg="#2c3e50").pack(side="left")

        for txt, cmd, color in [("+ Nuevo Animal", self.add_animal_dialog, "#2ecc71")]:
            tk.Button(top_bar, text=txt, bg=color, fg="white", font=("Segoe UI", 9),
                      relief="flat", padx=10, pady=4, command=cmd,
                      cursor="hand2").pack(side="right", padx=2)

        content = tk.Frame(main, bg="#f0f4f8")
        content.pack(fill="both", expand=True, pady=(10, 0))

        # Left panel - patient list
        left = tk.Frame(content, bg="white", width=280,
                        highlightbackground="#ddd", highlightthickness=1)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        tk.Label(left, text="Pacientes", font=("Segoe UI", 12, "bold"),
                 bg="#2c3e50", fg="white", padx=10, pady=8).pack(fill="x")

        search_frame = tk.Frame(left, bg="white", padx=8, pady=5)
        search_frame.pack(fill="x")
        tk.Label(search_frame, text="Buscar:", bg="white", font=("Segoe UI", 9)).pack(anchor="w")
        search_entry = tk.Entry(search_frame, font=("Segoe UI", 10))
        search_entry.pack(fill="x")

        especie_frame = tk.Frame(left, bg="white")
        especie_frame.pack(fill="x", padx=8, pady=(0, 5))
        tk.Label(especie_frame, text="Filtrar:", bg="white", font=("Segoe UI", 9)).pack(side="left", padx=(0, 5))
        filtro_especie = ttk.Combobox(especie_frame, values=["Todos", "Perro", "Gato"],
                                      width=20, font=("Segoe UI", 9), state="readonly")
        filtro_especie.set("Todos")
        filtro_especie.pack(side="left")

        list_frame = tk.Frame(left, bg="white")
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        canvas = tk.Canvas(list_frame, bg="white", highlightthickness=0)
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg="white")
        scrollable.bind("<Configure>",
                        lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Right panel - patient detail
        right = tk.Frame(content, bg="white",
                         highlightbackground="#ddd", highlightthickness=1)
        right.pack(side="left", fill="both", expand=True)

        detail_frame = tk.Frame(right, bg="#f0f4f8")
        detail_frame.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(detail_frame, text="Seleccione un paciente de la lista",
                 font=("Segoe UI", 14), bg="#f0f4f8", fg="#999").pack(expand=True)

        self._selected_card = None

        def load_patients(filter_text="", especie_filtro="Todos"):
            self._selected_card = None
            for w in scrollable.winfo_children():
                w.destroy()
            conn = self.get_db()
            query = ("SELECT a.id, a.nombre, a.especie, a.raza, a.edad, a.foto, "
                     "d.nombre as dueno_nombre, d.telefono as dueno_telefono, d.dni as dueno_dni "
                     "FROM animales a JOIN duenos d ON a.id_dueno = d.id ")
            params = []
            if especie_filtro != "Todos":
                query += "WHERE a.especie = ? "
                params.append(especie_filtro)
            query += "ORDER BY a.nombre"
            rows = conn.execute(query, params).fetchall()
            conn.close()
            for a in rows:
                if filter_text:
                    fl = filter_text.lower()
                    if (fl not in a["nombre"].lower() and
                        fl not in a["dueno_nombre"].lower() and
                        fl not in (a["dueno_dni"] or "")):
                        continue
                card = tk.Frame(scrollable, bg="white",
                                highlightbackground="#e8e8e8",
                                highlightthickness=1, padx=8, pady=6, cursor="hand2")
                card.pack(fill="x", pady=2)
                if a["foto"] and os.path.exists(os.path.join(PHOTOS_DIR, a["foto"])):
                    try:
                        img = Image.open(os.path.join(PHOTOS_DIR, a["foto"]))
                        img.thumbnail((40, 40))
                        tk_img = ImageTk.PhotoImage(img)
                        foto_lbl = tk.Label(card, image=tk_img, bg="#ddd")
                        foto_lbl.image = tk_img
                    except:
                        foto_lbl = tk.Label(card, text="  ", bg="#ddd", width=4, height=2)
                else:
                    foto_lbl = tk.Label(card, text="  ", bg="#ddd", width=4, height=2)
                foto_lbl.pack(side="left", padx=(0, 8))
                text_frame = tk.Frame(card, bg="white")
                text_frame.pack(side="left", fill="x", expand=True)
                tk.Label(text_frame, text=a["nombre"],
                         font=("Segoe UI", 10, "bold"),
                         bg="white", fg="#2c3e50").pack(anchor="w")
                tk.Label(text_frame,
                         text=a["especie"] + " - " + a["dueno_nombre"] +
                               (" | Tel: " + a["dueno_telefono"] if a["dueno_telefono"] else ""),
                         font=("Segoe UI", 8), bg="white",
                         fg="#7f8c8d").pack(anchor="w")
                aid = a["id"]

                def select_card(e, c=card, aid=aid):
                    if self._selected_card:
                        try:
                            self._selected_card.configure(bg="white", highlightbackground="#e8e8e8", highlightthickness=1)
                        except tk.TclError:
                            pass
                    self._selected_card = c
                    c.configure(bg="#d6eaf8", highlightbackground="#2980b9", highlightthickness=2)
                    self.show_detail(detail_frame, aid, load_patients)

                card.bind("<Button-1>", select_card)
                def bind_all_children(w):
                    for ch in w.winfo_children():
                        ch.bind("<Button-1>", select_card)
                        bind_all_children(ch)
                bind_all_children(card)

        def on_search(*args):
            load_patients(search_entry.get(), filtro_especie.get())

        def on_especie_filter(*args):
            load_patients(search_entry.get(), filtro_especie.get())

        search_entry.bind("<KeyRelease>", on_search)
        filtro_especie.bind("<<ComboboxSelected>>", on_especie_filter)
        load_patients()
        self.root.bind("<F5>", lambda e: load_patients(search_entry.get(), filtro_especie.get()))

    def show_detail(self, detail_frame, animal_id, reload_callback):
        for w in detail_frame.winfo_children():
            w.destroy()

        conn = self.get_db()
        animal = conn.execute(
            "SELECT a.*, d.id as dueno_id, d.nombre as dueno_nombre, d.telefono as dueno_telefono, "
            "d.email as dueno_email, d.direccion as dueno_direccion "
            "FROM animales a JOIN duenos d ON a.id_dueno = d.id "
            "WHERE a.id=?", (animal_id,)).fetchone()
        historial = conn.execute(
            "SELECT * FROM registros_medicos WHERE id_animal=? ORDER BY fecha DESC",
            (animal_id,)).fetchall()
        conn.close()

        if not animal:
            tk.Label(detail_frame, text="Animal no encontrado",
                     bg="#f0f4f8", fg="red").pack()
            return

        # Scrollable container
        canvas_outer = tk.Frame(detail_frame, bg="#f0f4f8")
        canvas_outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(canvas_outer, bg="#f0f4f8", highlightthickness=0)
        v_scroll = ttk.Scrollbar(canvas_outer, orient="vertical", command=canvas.yview)
        scrollable = tk.Frame(canvas, bg="#f0f4f8")
        scrollable.bind("<Configure>",
                        lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        window_id = canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=v_scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")

        def _configure_canvas(event):
            canvas.itemconfig(window_id, width=event.width)
        canvas.bind("<Configure>", _configure_canvas)
        canvas.bind("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))

        outer = scrollable

        # Header with photo
        header = tk.Frame(outer, bg="white", padx=15, pady=12,
                          highlightbackground="#ddd", highlightthickness=1)
        header.pack(fill="x")

        left_p = tk.Frame(header, bg="white")
        left_p.pack(side="left", padx=(0, 15))

        photo_frame = tk.Frame(left_p, bg="#eee", width=180, height=180,
                               highlightbackground="#ccc", highlightthickness=1)
        photo_frame.pack()
        photo_frame.pack_propagate(False)

        foto_path = os.path.join(PHOTOS_DIR, animal["foto"]) if animal["foto"] else ""
        if animal["foto"] and os.path.exists(foto_path):
            try:
                img = Image.open(foto_path)
                img.thumbnail((170, 170))
                tk_img = ImageTk.PhotoImage(img)
                lbl_img = tk.Label(photo_frame, image=tk_img, bg="#eee")
                lbl_img.image = tk_img
                lbl_img.pack(fill="both", expand=True)
            except:
                tk.Label(photo_frame, text="Sin foto", bg="#eee",
                         fg="#999").pack(expand=True)
        else:
            tk.Label(photo_frame, text="Sin foto", bg="#eee",
                     fg="#999").pack(expand=True)

        def change_photo():
            path = filedialog.askopenfilename(
                filetypes=[("Imagenes", "*.jpg *.jpeg *.png *.bmp *.gif")])
            if path:
                ext = os.path.splitext(path)[1]
                dest = os.path.join(PHOTOS_DIR, str(animal_id) + ext)
                shutil.copy2(path, dest)
                c = self.get_db()
                c.execute("UPDATE animales SET foto=? WHERE id=?",
                          (str(animal_id) + ext, animal_id))
                c.commit()
                c.close()
                self.show_detail(detail_frame, animal_id, reload_callback)

        tk.Button(left_p, text="Cambiar Foto", bg="#3498db", fg="white",
                  font=("Segoe UI", 8), relief="flat", padx=8, pady=2,
                  command=change_photo, cursor="hand2").pack(pady=(5, 0))

        info_p = tk.Frame(header, bg="white")
        info_p.pack(side="left", fill="x", expand=True)

        tk.Label(info_p, text=animal["nombre"] + " (" + animal["especie"] + ")",
                 font=("Segoe UI", 16, "bold"), bg="white", fg="#2c3e50").pack(anchor="w")
        det = ("Raza: " + (animal["raza"] or "N/A") +
               "  |  Edad: " + str(animal["edad"]) + " anios" +
               "  |  Peso: " + str(animal["peso"]) + " kg" +
               "  |  Sexo: " + (animal["sexo"] or "N/A") +
               "  |  Color: " + (animal["color"] or "N/A") +
               "  |  Esterilizado: " + ("Si" if animal["esterilizado"] else "No"))
        tk.Label(info_p, text=det, bg="white", fg="#555",
                 font=("Segoe UI", 10)).pack(anchor="w")
        tk.Label(info_p, text="", bg="white").pack(anchor="w", pady=2)
        tk.Label(info_p, text="Due\u00f1o: ", bg="white", fg="#555",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        dueno_line = tk.Frame(info_p, bg="white")
        dueno_line.pack(anchor="w")
        lbl_dueno = tk.Label(dueno_line, text=animal["dueno_nombre"],
                             bg="white", fg="#2980b9", font=("Segoe UI", 10, "bold"),
                             cursor="hand2")
        lbl_dueno.pack(side="left")
        lbl_dueno.bind("<Button-1>", lambda e: self.show_owner_detail(animal["dueno_id"]))
        tk.Button(dueno_line, text="Editar", bg="#f39c12", fg="white",
                  font=("Segoe UI", 8), relief="flat", padx=6, pady=0,
                  cursor="hand2",
                  command=lambda: self.edit_owner_dialog(animal["dueno_id"], animal_id, detail_frame, reload_callback)
                  ).pack(side="left", padx=(8, 0))
        tk.Label(info_p,
                 text="Telefono: " + animal["dueno_telefono"] +
                 "  |  Email: " + (animal["dueno_email"] or "N/A"),
                 bg="white", fg="#555", font=("Segoe UI", 10)).pack(anchor="w")
        tk.Label(info_p, text="Direccion: " + (animal["dueno_direccion"] or "N/A"),
                 bg="white", fg="#555", font=("Segoe UI", 10)).pack(anchor="w")

        action_frame = tk.Frame(header, bg="white")
        action_frame.pack(side="right", padx=(10, 0))
        def delete_animal():
            if messagebox.askyesno("Confirmar", "\u00bfEliminar este animal y todos sus registros?"):
                c = self.get_db()
                c.execute("DELETE FROM signos_vitales WHERE id_registro IN (SELECT id FROM registros_medicos WHERE id_animal=?)", (animal_id,))
                c.execute("DELETE FROM registros_medicos WHERE id_animal=?", (animal_id,))
                c.execute("DELETE FROM vacunas WHERE id_animal=?", (animal_id,))
                c.execute("DELETE FROM alergias WHERE id_animal=?", (animal_id,))
                c.execute("DELETE FROM examenes_auxiliares WHERE id_animal=?", (animal_id,))
                c.execute("DELETE FROM medicacion WHERE id_animal=?", (animal_id,))
                c.execute("DELETE FROM citas WHERE id_animal=?", (animal_id,))
                c.execute("DELETE FROM historial_grooming WHERE id_animal=?", (animal_id,))
                c.execute("DELETE FROM animales WHERE id=?", (animal_id,))
                c.commit()
                c.close()
                reload_callback()
        tk.Button(action_frame, text="Editar", bg="#f39c12", fg="white",
                  font=("Segoe UI", 9), relief="flat", padx=0, pady=3, width=8,
                  command=lambda: self.edit_animal_dialog(animal_id, reload_callback),
                  cursor="hand2").pack(side="top", pady=2)
        tk.Button(action_frame, text="Grooming", bg="#9b59b6", fg="white",
                  font=("Segoe UI", 9), relief="flat", padx=0, pady=3, width=8,
                  command=lambda: self.add_grooming_from_detail(animal_id, detail_frame, reload_callback),
                  cursor="hand2").pack(side="top", pady=2)
        tk.Button(action_frame, text="Eliminar", bg="#e74c3c", fg="white",
                  font=("Segoe UI", 9), relief="flat", padx=0, pady=3, width=8,
                  command=delete_animal, cursor="hand2").pack(side="top", pady=2)
        tk.Button(action_frame, text="PDF", bg="#9b59b6", fg="white",
                  font=("Segoe UI", 9), relief="flat", padx=0, pady=3, width=8,
                  command=lambda: self.export_pdf(animal_id),
                  cursor="hand2").pack(side="top", pady=2)
        hist_frame = tk.Frame(outer, bg="#e8edf2")
        hist_frame.pack(fill="x", pady=(6, 0))

        # --- RESUMEN RAPIDO ---
        self._resumen_rapido(hist_frame, animal_id)

        # --- ALERGIAS ---
        self._seccion_alergias(hist_frame, animal_id, detail_frame, reload_callback)

        # ========== HISTORIAL MEDICO ==========
        hist_header = tk.Frame(hist_frame, bg="#e8edf2")
        hist_header.pack(fill="x", pady=(8, 2))
        tk.Label(hist_header, text="Historial Medico",
                 font=("Segoe UI", 12, "bold"),
                 bg="#e8edf2", fg="#2c3e50").pack(side="left")

        # Filter bar
        filtros_frame = tk.Frame(hist_frame, bg="#e8edf2")
        filtros_frame.pack(fill="x", pady=(0, 4))
        tk.Label(filtros_frame, text="Filtrar:", bg="#e8edf2", font=("Segoe UI", 8)).pack(side="left", padx=(0, 4))
        filtro_entry = tk.Entry(filtros_frame, font=("Segoe UI", 9), width=25)
        filtro_entry.pack(side="left", padx=2)

        def filtrar_historial():
            texto = filtro_entry.get().lower()
            for item in tree.get_children():
                vals = tree.item(item, "values")
                if not texto:
                    tree.reattach(item, "", "end")
                elif any(texto in str(v).lower() for v in vals):
                    tree.reattach(item, "", "end")
                else:
                    tree.detach(item)

        tk.Button(filtros_frame, text="Filtrar", bg="#3498db", fg="white",
                  font=("Segoe UI", 8), relief="flat", padx=8, pady=1,
                  command=filtrar_historial, cursor="hand2").pack(side="left", padx=2)
        tk.Button(filtros_frame, text="Limpiar", bg="#95a5a6", fg="white",
                  font=("Segoe UI", 8), relief="flat", padx=8, pady=1,
                  command=lambda: (filtro_entry.delete(0, "end"), filtrar_historial()),
                  cursor="hand2").pack(side="left", padx=2)

        tk.Button(hist_header, text="+ Nueva Consulta", bg="#2ecc71",
                  fg="white", font=("Segoe UI", 9), relief="flat", padx=12, pady=3,
                  command=lambda: self.add_medical_record_for(
                      animal_id, callback=lambda: self.show_detail(
                          detail_frame, animal_id, reload_callback)),
                  cursor="hand2").pack(side="right", padx=2)
        tk.Button(hist_header, text="+ Programar Cita", bg="#3498db",
                  fg="white", font=("Segoe UI", 9), relief="flat", padx=12, pady=3,
                  command=lambda: self.add_appointment_dialog(animal_id),
                  cursor="hand2").pack(side="right")

        if not historial:
            tk.Label(hist_frame, text="No hay registros medicos para este paciente",
                     bg="white", fg="#999", font=("Segoe UI", 10),
                     padx=15, pady=20).pack(fill="x", pady=5)
        else:
            table_frame = tk.Frame(hist_frame, bg="white",
                                   highlightbackground="#ddd", highlightthickness=1)
            table_frame.pack(fill="both", expand=True, pady=5)
            columns = ("id", "fecha", "peso", "hora", "doctor", "diagnostico", "tratamiento", "observaciones")
            tree = ttk.Treeview(table_frame, columns=columns, show="headings")
            tree.heading("id", text="ID")
            tree.heading("fecha", text="Fecha")
            tree.heading("peso", text="Peso")
            tree.heading("hora", text="Hora")
            tree.heading("doctor", text="Doctor")
            tree.heading("diagnostico", text="Diagnostico")
            tree.heading("tratamiento", text="Tratamiento")
            tree.heading("observaciones", text="Observaciones")
            tree.column("id", width=0, stretch=False)
            tree.column("fecha", width=80)
            tree.column("peso", width=50)
            tree.column("hora", width=55)
            tree.column("doctor", width=110)
            tree.column("diagnostico", width=150)
            tree.column("tratamiento", width=150)
            tree.column("observaciones", width=150)
            tree.pack(fill="both", expand=True)
            for r in historial:
                p = str(r["peso"]) + " kg" if r["peso"] else "-"
                tree.insert("", "end", values=(r["id"], r["fecha"], p, r["hora"] or "",
                                                r["doctor"] or "", r["diagnostico"],
                                                r["tratamiento"], r["observaciones"] or ""))
            def edit_selected():
                sel = tree.selection()
                if not sel: return
                vals = tree.item(sel[0], "values")
                self.edit_registro_dialog(int(vals[0]), animal_id,
                    lambda: self.show_detail(detail_frame, animal_id, reload_callback))
            def delete_selected():
                sel = tree.selection()
                if not sel: return
                vals = tree.item(sel[0], "values")
                if messagebox.askyesno("Confirmar", "\u00bfEliminar este registro medico?"):
                    c = self.get_db()
                    c.execute("DELETE FROM signos_vitales WHERE id_registro=?", (int(vals[0]),))
                    c.execute("DELETE FROM registros_medicos WHERE id=?", (int(vals[0]),))
                    c.commit()
                    c.close()
                    self.show_detail(detail_frame, animal_id, reload_callback)
            btn_row = tk.Frame(hist_frame, bg="#e8edf2")
            btn_row.pack(fill="x", pady=(3, 0))
            tk.Button(btn_row, text="Editar", bg="#f39c12", fg="white",
                      font=("Segoe UI", 9), relief="flat", padx=10, pady=2,
                      command=edit_selected, cursor="hand2").pack(side="left", padx=2)
            tk.Button(btn_row, text="Eliminar", bg="#e74c3c", fg="white",
                      font=("Segoe UI", 9), relief="flat", padx=10, pady=2,
                      command=delete_selected, cursor="hand2").pack(side="left", padx=2)
            tk.Button(btn_row, text="Agregar Signos Vitales", bg="#e74c3c", fg="white",
                      font=("Segoe UI", 9), relief="flat", padx=10, pady=2,
                      command=lambda: self._add_signos_vitales_dialog(animal_id, detail_frame, reload_callback),
                      cursor="hand2").pack(side="left", padx=2)

        # --- SIGNOS VITALES ---
        self._seccion_signos_vitales(hist_frame, animal_id)

        # --- CITAS ---
        conn2 = self.get_db()
        citas_paciente = conn2.execute(
            "SELECT id, fecha, motivo, estado, tipo FROM citas WHERE id_animal=? ORDER BY fecha DESC",
            (animal_id,)).fetchall()
        conn2.close()
        if citas_paciente:
            sec, lbl = self._make_section(hist_frame, "Citas", "#3498db")
            c_frame = self._make_table_frame(hist_frame)
            cols_c = ("fecha_c", "motivo_c", "tipo_c", "estado_c")
            c_tree = ttk.Treeview(c_frame, columns=cols_c, show="headings", height=4)
            c_tree.heading("fecha_c", text="Fecha")
            c_tree.heading("motivo_c", text="Motivo")
            c_tree.heading("tipo_c", text="Tipo")
            c_tree.heading("estado_c", text="Estado")
            c_tree.column("fecha_c", width=100)
            c_tree.column("motivo_c", width=200)
            c_tree.column("tipo_c", width=80)
            c_tree.column("estado_c", width=80)
            c_tree.pack(fill="x")
            for r in citas_paciente:
                c_tree.insert("", "end", values=(r["fecha"], r["motivo"], r["tipo"] or "veterinaria", r["estado"] or "pendiente"))

        # --- VACUNAS ---
        self._seccion_vacunas(hist_frame, animal_id, detail_frame, reload_callback)

        # --- MEDICACION ---
        self._seccion_medicacion(hist_frame, animal_id, detail_frame, reload_callback)

        # --- EXAMENES ---
        self._seccion_examenes(hist_frame, animal_id, detail_frame, reload_callback)

        # --- GROOMING HISTORY ---
        self._seccion_historial_grooming(hist_frame, animal_id)

        # --- GRAFICO PESO ---
        self._grafico_peso(hist_frame, historial)

        # --- DIAGNOSTICOS RECURRENTES ---
        self._diagnosticos_recurrentes(hist_frame, animal_id)

        # Notificacion de citas proximas
        conn3 = self.get_db()
        prox = conn3.execute(
            "SELECT fecha, motivo FROM citas WHERE id_animal=? AND estado='pendiente' AND fecha >= ? ORDER BY fecha ASC LIMIT 1",
            (animal_id, str(date.today()))).fetchone()
        if prox:
            dias = (date.fromisoformat(prox["fecha"]) - date.today()).days
            if dias <= 3:
                msg = f"Proxima cita: {prox['fecha']} ({prox['motivo']})"
                if dias == 0: msg = f"Cita programada para HOY: {prox['motivo']}"
                elif dias == 1: msg = f"Cita programada para MA\u00d1ANA: {prox['motivo']}"
                lbl_notif = tk.Label(hist_frame, text=msg, font=("Segoe UI", 9, "bold"),
                                      bg="#fef9e7", fg="#e67e22", anchor="w", padx=10, pady=4)
                lbl_notif.pack(fill="x", pady=(6, 0))
        conn3.close()

    # ---------- NUEVAS SECCIONES ----------
    def _make_section(self, parent, title, color="#2c3e50"):
        f = tk.Frame(parent, bg="#e8edf2")
        f.pack(fill="x", pady=(8, 2))
        lbl = tk.Label(f, text=title, font=("Segoe UI", 12, "bold"),
                       bg="#e8edf2", fg=color)
        lbl.pack(side="left")
        return f, lbl

    def _make_table_frame(self, parent):
        f = tk.Frame(parent, bg="white", highlightbackground="#ddd", highlightthickness=1)
        f.pack(fill="x", pady=(0, 4))
        return f

    def _resumen_rapido(self, parent, animal_id):
        conn = self.get_db()
        total_consultas = conn.execute(
            "SELECT COUNT(*) FROM registros_medicos WHERE id_animal=?", (animal_id,)).fetchone()[0]
        ultima = conn.execute(
            "SELECT fecha, diagnostico FROM registros_medicos WHERE id_animal=? ORDER BY fecha DESC LIMIT 1",
            (animal_id,)).fetchone()
        ultima_vacuna = conn.execute(
            "SELECT fecha, nombre FROM vacunas WHERE id_animal=? AND tipo='vacuna' ORDER BY fecha DESC LIMIT 1",
            (animal_id,)).fetchone()
        prox_cita = conn.execute(
            "SELECT fecha, motivo FROM citas WHERE id_animal=? AND estado='pendiente' ORDER BY fecha ASC LIMIT 1",
            (animal_id,)).fetchone()
        conn.close()

        card = tk.Frame(parent, bg="white", highlightbackground="#ddd",
                        highlightthickness=1, padx=12, pady=8)
        card.pack(fill="x", pady=(0, 6))
        items = [("Consultas", str(total_consultas), "#3498db")]
        if ultima:
            items.append(("Ultima Consulta", f"{ultima['fecha']} - {ultima['diagnostico'][:30]}", "#2ecc71"))
        if ultima_vacuna:
            items.append(("Ultima Vacuna", f"{ultima_vacuna['fecha']} - {ultima_vacuna['nombre']}", "#9b59b6"))
        if prox_cita:
            items.append(("Proxima Cita", f"{prox_cita['fecha']} - {prox_cita['motivo']}", "#e67e22"))
        inner = tk.Frame(card, bg="white")
        inner.pack(fill="x")
        for lbl_t, val, color in items:
            cell = tk.Frame(inner, bg="white", padx=10, pady=4)
            cell.pack(side="left", fill="x", expand=True)
            tk.Label(cell, text=lbl_t, font=("Segoe UI", 8, "bold"),
                     bg="white", fg=color).pack(anchor="w")
            tk.Label(cell, text=val, font=("Segoe UI", 9),
                     bg="white", fg="#555").pack(anchor="w")

    def _seccion_alergias(self, parent, animal_id, detail_frame, reload_callback):
        conn = self.get_db()
        alergias = conn.execute(
            "SELECT * FROM alergias WHERE id_animal=? ORDER BY alergeno", (animal_id,)).fetchall()
        conn.close()
        sec, lbl = self._make_section(parent, "Alergias", "#e74c3c")

        def add_alergia():
            dialog = tk.Toplevel(self.root)
            dialog.title("Agregar Alergia")
            dialog.geometry("420x280")
            dialog.resizable(False, False)
            dialog.configure(bg="#e8edf2")
            dialog.transient(self.root)
            dialog.grab_set()
            center_dialog(dialog, self.root)
            tk.Label(dialog, text="Alergeno", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="e", padx=10, pady=6)
            e_alergeno = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
            e_alergeno.grid(row=0, column=1, padx=10, pady=6)
            tk.Label(dialog, text="Tipo", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="e", padx=10, pady=6)
            e_tipo = ttk.Combobox(dialog, values=["Alimentaria", "Ambiental", "Farmacologica", "Picadura", "Contacto", "Otra"],
                                  width=37, font=("Segoe UI", 10))
            e_tipo.grid(row=1, column=1, padx=10, pady=6)
            tk.Label(dialog, text="Severidad", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="e", padx=10, pady=6)
            e_sev = ttk.Combobox(dialog, values=["Leve", "Moderada", "Grave"],
                                 width=37, font=("Segoe UI", 10))
            e_sev.set("Leve")
            e_sev.grid(row=2, column=1, padx=10, pady=6)
            tk.Label(dialog, text="Observaciones", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=3, column=0, sticky="e", padx=10, pady=6)
            e_obs = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
            e_obs.grid(row=3, column=1, padx=10, pady=6)
            def save():
                conn = self.get_db()
                conn.execute("INSERT INTO alergias (id_animal, alergeno, tipo, severidad, observaciones) VALUES (?,?,?,?,?)",
                             (animal_id, e_alergeno.get(), e_tipo.get(), e_sev.get(), e_obs.get()))
                conn.commit()
                conn.close()
                dialog.destroy()
                self.show_detail(detail_frame, animal_id, reload_callback)
            tk.Button(dialog, text="Guardar", bg="#2ecc71", fg="white",
                      font=("Segoe UI", 10), relief="flat", padx=20, pady=5,
                      command=save, cursor="hand2").grid(row=4, column=1, pady=15, sticky="e")

        tk.Button(sec, text="+", bg="#e74c3c", fg="white", font=("Segoe UI", 9, "bold"),
                  relief="flat", width=2, cursor="hand2", command=add_alergia).pack(side="right", padx=2)
        if alergias:
            f = self._make_table_frame(parent)
            for r in alergias:
                color = "#e74c3c" if r["severidad"] == "Grave" else "#f39c12" if r["severidad"] == "Moderada" else "#2ecc71"
                row_f = tk.Frame(f, bg="white", padx=8, pady=2)
                row_f.pack(fill="x")
                tk.Label(row_f, text=r["alergeno"], font=("Segoe UI", 10, "bold"),
                         bg="white", fg=color).pack(side="left", padx=5)
                tk.Label(row_f, text=f"({r['tipo']}) [{r['severidad']}]",
                         font=("Segoe UI", 9), bg="white", fg="#7f8c8d").pack(side="left")
                if r["observaciones"]:
                    tk.Label(row_f, text=r["observaciones"], font=("Segoe UI", 9),
                             bg="white", fg="#555").pack(side="left", padx=10)
        else:
            tk.Label(parent, text="  No se registraron alergias", font=("Segoe UI", 9),
                     bg="#e8edf2", fg="#999", anchor="w").pack(fill="x")

    def _seccion_vacunas(self, parent, animal_id, detail_frame, reload_callback):
        conn = self.get_db()
        vacunas = conn.execute(
            "SELECT * FROM vacunas WHERE id_animal=? ORDER BY fecha DESC", (animal_id,)).fetchall()
        conn.close()
        sec, lbl = self._make_section(parent, "Vacunas y Desparasitaciones", "#9b59b6")

        def add_vacuna():
            from tkcalendar import DateEntry
            dialog = tk.Toplevel(self.root)
            dialog.title("Agregar Vacuna / Desparasitacion")
            dialog.geometry("450x340")
            dialog.resizable(False, False)
            dialog.configure(bg="#e8edf2")
            dialog.transient(self.root)
            dialog.grab_set()
            center_dialog(dialog, self.root)
            tk.Label(dialog, text="Tipo", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="e", padx=10, pady=6)
            e_tipo = ttk.Combobox(dialog, values=["Vacuna", "Desparasitacion"], width=37, font=("Segoe UI", 10), state="readonly")
            e_tipo.set("Vacuna")
            e_tipo.grid(row=0, column=1, padx=10, pady=6)
            tk.Label(dialog, text="Nombre", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="e", padx=10, pady=6)
            e_nombre = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
            e_nombre.grid(row=1, column=1, padx=10, pady=6)
            tk.Label(dialog, text="Fecha aplicacion", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="e", padx=10, pady=6)
            e_fecha = DateEntry(dialog, width=37, font=("Segoe UI", 10),
                                background="#2c3e50", foreground="white",
                                borderwidth=2, date_pattern="yyyy-mm-dd")
            e_fecha.grid(row=2, column=1, padx=10, pady=6)
            tk.Label(dialog, text="Lote", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=3, column=0, sticky="e", padx=10, pady=6)
            e_lote = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
            e_lote.grid(row=3, column=1, padx=10, pady=6)
            tk.Label(dialog, text="Proxima dosis", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=4, column=0, sticky="e", padx=10, pady=6)
            e_prox = DateEntry(dialog, width=37, font=("Segoe UI", 10),
                               background="#2c3e50", foreground="white",
                               borderwidth=2, date_pattern="yyyy-mm-dd")
            e_prox.grid(row=4, column=1, padx=10, pady=6)
            def save():
                conn = self.get_db()
                conn.execute(
                    "INSERT INTO vacunas (id_animal, tipo, nombre, fecha, lote, proxima_dosis) VALUES (?,?,?,?,?,?)",
                    (animal_id, e_tipo.get().lower(), e_nombre.get(), e_fecha.get(), e_lote.get(), e_prox.get()))
                conn.commit()
                conn.close()
                dialog.destroy()
                self.show_detail(detail_frame, animal_id, reload_callback)
            tk.Button(dialog, text="Guardar", bg="#2ecc71", fg="white",
                      font=("Segoe UI", 10), relief="flat", padx=20, pady=5,
                      command=save, cursor="hand2").grid(row=5, column=1, pady=15, sticky="e")

        tk.Button(sec, text="+", bg="#9b59b6", fg="white", font=("Segoe UI", 9, "bold"),
                  relief="flat", width=2, cursor="hand2", command=add_vacuna).pack(side="right", padx=2)
        if vacunas:
            f = self._make_table_frame(parent)
            cols = ("f_v", "tipo_v", "nombre_v", "lote_v", "prox_v")
            tree = ttk.Treeview(f, columns=cols, show="headings", height=4)
            tree.heading("f_v", text="Fecha")
            tree.heading("tipo_v", text="Tipo")
            tree.heading("nombre_v", text="Nombre")
            tree.heading("lote_v", text="Lote")
            tree.heading("prox_v", text="Proxima Dosis")
            tree.column("f_v", width=90)
            tree.column("tipo_v", width=100)
            tree.column("nombre_v", width=180)
            tree.column("lote_v", width=100)
            tree.column("prox_v", width=100)
            tree.pack(fill="x")
            for r in vacunas:
                prox = r["proxima_dosis"] or ""
                tag = ""
                if prox:
                    try:
                        if date.fromisoformat(prox) < date.today():
                            tag = "vencida"
                        elif (date.fromisoformat(prox) - date.today()).days <= 15:
                            tag = "proxima"
                    except: pass
                tree.insert("", "end", values=(r["fecha"], r["tipo"].capitalize(),
                                               r["nombre"], r["lote"] or "", prox),
                            tags=(tag,) if tag else ())
            tree.tag_configure("vencida", background="#fadbd8")
            tree.tag_configure("proxima", background="#fef9e7")
        else:
            tk.Label(parent, text="  No hay vacunas registradas", font=("Segoe UI", 9),
                     bg="#e8edf2", fg="#999", anchor="w").pack(fill="x")

    def _seccion_medicacion(self, parent, animal_id, detail_frame, reload_callback):
        conn = self.get_db()
        medicacion = conn.execute(
            "SELECT * FROM medicacion WHERE id_animal=? ORDER BY activo DESC, fecha_inicio DESC",
            (animal_id,)).fetchall()
        conn.close()
        sec, lbl = self._make_section(parent, "Medicacion Actual", "#e67e22")

        def add_medicacion():
            from tkcalendar import DateEntry
            dialog = tk.Toplevel(self.root)
            dialog.title("Agregar Medicacion")
            dialog.geometry("480x350")
            dialog.resizable(False, False)
            dialog.configure(bg="#e8edf2")
            dialog.transient(self.root)
            dialog.grab_set()
            center_dialog(dialog, self.root)
            tk.Label(dialog, text="Medicamento", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="e", padx=10, pady=6)
            e_med = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
            e_med.grid(row=0, column=1, padx=10, pady=6)
            tk.Label(dialog, text="Dosis", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="e", padx=10, pady=6)
            e_dosis = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
            e_dosis.grid(row=1, column=1, padx=10, pady=6)
            tk.Label(dialog, text="Frecuencia", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="e", padx=10, pady=6)
            e_freq = ttk.Combobox(dialog, values=["Cada 8h", "Cada 12h", "Cada 24h", "Cada 48h", "Semanal", "Mensual", "Segun indicacion"],
                                  width=37, font=("Segoe UI", 10))
            e_freq.grid(row=2, column=1, padx=10, pady=6)
            tk.Label(dialog, text="Via", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=3, column=0, sticky="e", padx=10, pady=6)
            e_via = ttk.Combobox(dialog, values=["Oral", "Topica", "Intramuscular", "Subcutanea", "Intravenosa", "Otica", "Oftalmica", "Otra"],
                                 width=37, font=("Segoe UI", 10))
            e_via.grid(row=3, column=1, padx=10, pady=6)
            tk.Label(dialog, text="Inicio", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=4, column=0, sticky="e", padx=10, pady=6)
            e_ini = DateEntry(dialog, width=37, font=("Segoe UI", 10),
                              background="#2c3e50", foreground="white", borderwidth=2, date_pattern="yyyy-mm-dd")
            e_ini.grid(row=4, column=1, padx=10, pady=6)
            tk.Label(dialog, text="Fin", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=5, column=0, sticky="e", padx=10, pady=6)
            e_fin = DateEntry(dialog, width=37, font=("Segoe UI", 10),
                              background="#2c3e50", foreground="white", borderwidth=2, date_pattern="yyyy-mm-dd")
            e_fin.grid(row=5, column=1, padx=10, pady=6)
            def save():
                conn = self.get_db()
                conn.execute(
                    "INSERT INTO medicacion (id_animal, medicamento, dosis, frecuencia, via, fecha_inicio, fecha_fin) VALUES (?,?,?,?,?,?,?)",
                    (animal_id, e_med.get(), e_dosis.get(), e_freq.get(), e_via.get(), e_ini.get(), e_fin.get()))
                conn.commit()
                conn.close()
                dialog.destroy()
                self.show_detail(detail_frame, animal_id, reload_callback)
            tk.Button(dialog, text="Guardar", bg="#2ecc71", fg="white",
                      font=("Segoe UI", 10), relief="flat", padx=20, pady=5,
                      command=save, cursor="hand2").grid(row=6, column=1, pady=15, sticky="e")

        tk.Button(sec, text="+", bg="#e67e22", fg="white", font=("Segoe UI", 9, "bold"),
                  relief="flat", width=2, cursor="hand2", command=add_medicacion).pack(side="right", padx=2)
        if medicacion:
            f = self._make_table_frame(parent)
            cols = ("m_med", "m_dosis", "m_freq", "m_via", "m_ini", "m_fin", "m_act")
            tree = ttk.Treeview(f, columns=cols, show="headings", height=4)
            tree.heading("m_med", text="Medicamento")
            tree.heading("m_dosis", text="Dosis")
            tree.heading("m_freq", text="Frecuencia")
            tree.heading("m_via", text="Via")
            tree.heading("m_ini", text="Inicio")
            tree.heading("m_fin", text="Fin")
            tree.heading("m_act", text="Activo")
            for c in cols: tree.column(c, width=90)
            tree.column("m_med", width=130)
            tree.column("m_act", width=50)
            tree.pack(fill="x")
            for r in medicacion:
                tree.insert("", "end", values=(r["medicamento"], r["dosis"], r["frecuencia"],
                                               r["via"] or "", r["fecha_inicio"], r["fecha_fin"] or "",
                                               "Si" if r["activo"] else "No"))
        else:
            tk.Label(parent, text="  Sin medicacion activa", font=("Segoe UI", 9),
                     bg="#e8edf2", fg="#999", anchor="w").pack(fill="x")

    def _seccion_examenes(self, parent, animal_id, detail_frame, reload_callback):
        conn = self.get_db()
        examenes = conn.execute(
            "SELECT * FROM examenes_auxiliares WHERE id_animal=? ORDER BY fecha DESC",
            (animal_id,)).fetchall()
        conn.close()
        sec, lbl = self._make_section(parent, "Examenes Auxiliares", "#1abc9c")

        def add_examen():
            from tkcalendar import DateEntry
            dialog = tk.Toplevel(self.root)
            dialog.title("Agregar Examen Auxiliar")
            dialog.geometry("480x350")
            dialog.resizable(False, False)
            dialog.configure(bg="#e8edf2")
            dialog.transient(self.root)
            dialog.grab_set()
            center_dialog(dialog, self.root)
            tk.Label(dialog, text="Tipo", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="e", padx=10, pady=6)
            e_tipo = ttk.Combobox(dialog, values=["Laboratorio", "Radiografia", "Ecografia", "Electrocardiograma", "Endoscopia", "Otro"],
                                  width=37, font=("Segoe UI", 10))
            e_tipo.grid(row=0, column=1, padx=10, pady=6)
            tk.Label(dialog, text="Nombre", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="e", padx=10, pady=6)
            e_nombre = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
            e_nombre.grid(row=1, column=1, padx=10, pady=6)
            tk.Label(dialog, text="Fecha", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="e", padx=10, pady=6)
            e_fecha = DateEntry(dialog, width=37, font=("Segoe UI", 10),
                                background="#2c3e50", foreground="white", borderwidth=2, date_pattern="yyyy-mm-dd")
            e_fecha.grid(row=2, column=1, padx=10, pady=6)
            tk.Label(dialog, text="Resultados", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=3, column=0, sticky="ne", padx=10, pady=6)
            e_result = tk.Text(dialog, width=30, height=3, font=("Segoe UI", 10))
            e_result.grid(row=3, column=1, padx=10, pady=6)
            selected_file = tk.StringVar(value="")
            tk.Label(dialog, text="Adjuntar archivo", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=4, column=0, sticky="e", padx=10, pady=6)
            file_frame = tk.Frame(dialog, bg="#e8edf2")
            file_frame.grid(row=4, column=1, padx=10, pady=6, sticky="w")
            file_label = tk.Label(file_frame, text="Ninguno", bg="#e8edf2", fg="#999", font=("Segoe UI", 9))
            file_label.pack(side="left")
            def choose_file():
                path = filedialog.askopenfilename(filetypes=[("Todos los archivos", "*.*")])
                if path:
                    selected_file.set(path)
                    file_label.config(text=os.path.basename(path))
            tk.Button(file_frame, text="Examinar", bg="#3498db", fg="white",
                      font=("Segoe UI", 9), relief="flat", padx=8, pady=1,
                      command=choose_file, cursor="hand2").pack(side="left", padx=5)
            def save():
                conn = self.get_db()
                archivo = ""
                if selected_file.get():
                    ext = os.path.splitext(selected_file.get())[1]
                    dest = os.path.join(EXAMENES_DIR, f"{animal_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}")
                    shutil.copy2(selected_file.get(), dest)
                    archivo = os.path.basename(dest)
                conn.execute(
                    "INSERT INTO examenes_auxiliares (id_animal, tipo, nombre, fecha, archivo, resultados) VALUES (?,?,?,?,?,?)",
                    (animal_id, e_tipo.get(), e_nombre.get(), e_fecha.get(), archivo, e_result.get("1.0", "end-1c")))
                conn.commit()
                conn.close()
                dialog.destroy()
                self.show_detail(detail_frame, animal_id, reload_callback)
            tk.Button(dialog, text="Guardar", bg="#2ecc71", fg="white",
                      font=("Segoe UI", 10), relief="flat", padx=20, pady=5,
                      command=save, cursor="hand2").grid(row=5, column=1, pady=15, sticky="e")

        tk.Button(sec, text="+", bg="#1abc9c", fg="white", font=("Segoe UI", 9, "bold"),
                  relief="flat", width=2, cursor="hand2", command=add_examen).pack(side="right", padx=2)
        if examenes:
            f = self._make_table_frame(parent)
            cols = ("e_fecha", "e_tipo", "e_nombre", "e_result", "e_archivo")
            tree = ttk.Treeview(f, columns=cols, show="headings", height=4)
            tree.heading("e_fecha", text="Fecha")
            tree.heading("e_tipo", text="Tipo")
            tree.heading("e_nombre", text="Nombre")
            tree.heading("e_result", text="Resultados")
            tree.heading("e_archivo", text="Archivo")
            tree.column("e_fecha", width=80)
            tree.column("e_tipo", width=90)
            tree.column("e_nombre", width=130)
            tree.column("e_result", width=170)
            tree.column("e_archivo", width=100)
            tree.pack(fill="x")

            def ver_examen():
                sel = tree.selection()
                if not sel: return
                vals = tree.item(sel[0], "values")
                archivo = vals[4] if len(vals) > 4 else ""
                if not archivo:
                    messagebox.showinfo("Info", "Este examen no tiene archivo adjunto")
                    return
                ruta = os.path.join(EXAMENES_DIR, archivo)
                if not os.path.exists(ruta):
                    messagebox.showerror("Error", "Archivo no encontrado")
                    return
                ext = os.path.splitext(archivo)[1].lower()
                if ext in (".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"):
                    try:
                        viewer = tk.Toplevel(self.root)
                        viewer.title(f"Radiografia/Imagen - {vals[2]}")
                        viewer.geometry("900x700")
                        viewer.transient(self.root)
                        img = Image.open(ruta)
                        w, h = img.size
                        max_w, max_h = 850, 650
                        if w > max_w or h > max_h:
                            ratio = min(max_w/w, max_h/h)
                            img = img.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
                        tk_img = ImageTk.PhotoImage(img)
                        lbl = tk.Label(viewer, image=tk_img)
                        lbl.image = tk_img
                        lbl.pack(expand=True)
                        info_f = tk.Frame(viewer, bg="#f0f4f8", padx=10, pady=5)
                        info_f.pack(fill="x")
                        tk.Label(info_f, text=f"{vals[2]} ({vals[1]}) - {vals[0]}",
                                 font=("Segoe UI", 10), bg="#f0f4f8").pack()
                        tk.Button(info_f, text="Abrir con visor externo", bg="#3498db", fg="white",
                                  font=("Segoe UI", 9), relief="flat", padx=10,
                                  command=lambda: os.startfile(ruta), cursor="hand2").pack(pady=5)
                    except Exception as ex:
                        messagebox.showerror("Error", f"No se pudo abrir imagen: {ex}")
                else:
                    try:
                        os.startfile(ruta)
                    except Exception as ex:
                        messagebox.showerror("Error", f"No se pudo abrir archivo: {ex}")

            tree.bind("<Double-1>", lambda e: ver_examen())

            btn_row = tk.Frame(parent, bg="#e8edf2")
            btn_row.pack(fill="x", pady=(2, 0))
            tk.Button(btn_row, text="Ver archivo", bg="#3498db", fg="white",
                      font=("Segoe UI", 9), relief="flat", padx=10, pady=1,
                      command=ver_examen, cursor="hand2").pack(side="left", padx=2)

            for r in examenes:
                archivo = r["archivo"] or ""
                tree.insert("", "end", values=(r["fecha"], r["tipo"], r["nombre"],
                                               (r["resultados"] or "")[:60], archivo))
        else:
            tk.Label(parent, text="  Sin examenes registrados", font=("Segoe UI", 9),
                     bg="#e8edf2", fg="#999", anchor="w").pack(fill="x")

    def _seccion_signos_vitales(self, parent, animal_id):
        conn = self.get_db()
        registros = conn.execute(
            "SELECT rm.id, rm.fecha, sv.temperatura, sv.frecuencia_cardiaca, "
            "sv.frecuencia_respiratoria, sv.presion_sistolica, sv.presion_diastolica "
            "FROM registros_medicos rm "
            "LEFT JOIN signos_vitales sv ON sv.id_registro = rm.id "
            "WHERE rm.id_animal=? AND (sv.temperatura IS NOT NULL OR sv.frecuencia_cardiaca IS NOT NULL) "
            "ORDER BY rm.fecha DESC LIMIT 10", (animal_id,)).fetchall()
        conn.close()
        if not registros:
            return
        sec, lbl = self._make_section(parent, "Signos Vitales", "#e74c3c")
        f = self._make_table_frame(parent)
        cols = ("sv_f", "sv_temp", "sv_fc", "sv_fr", "sv_pa")
        tree = ttk.Treeview(f, columns=cols, show="headings", height=4)
        tree.heading("sv_f", text="Fecha")
        tree.heading("sv_temp", text="Temp (C)")
        tree.heading("sv_fc", text="FC (lpm)")
        tree.heading("sv_fr", text="FR (rpm)")
        tree.heading("sv_pa", text="PA (mmHg)")
        tree.column("sv_f", width=90)
        tree.column("sv_temp", width=80)
        tree.column("sv_fc", width=80)
        tree.column("sv_fr", width=80)
        tree.column("sv_pa", width=100)
        tree.pack(fill="x")
        for r in registros:
            pa = f"{r['presion_sistolica']}/{r['presion_diastolica']}" if r["presion_sistolica"] else ""
            tree.insert("", "end", values=(r["fecha"],
                        f"{r['temperatura']:.1f}" if r["temperatura"] else "-",
                        r["frecuencia_cardiaca"] or "-",
                        r["frecuencia_respiratoria"] or "-", pa or "-"))

    def _grafico_peso(self, parent, historial):
        pesos = [(r["fecha"], r["peso"]) for r in historial if r["peso"]]
        if len(pesos) < 2:
            return
        pesos.sort(key=lambda x: x[0])
        sec, lbl = self._make_section(parent, "Evolucion del Peso", "#2ecc71")
        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            fig = Figure(figsize=(4, 1.8), dpi=80, facecolor="white")
            ax = fig.add_subplot(111)
            fechas = [p[0] for p in pesos]
            valores = [p[1] for p in pesos]
            ax.plot(range(len(valores)), valores, marker="o", color="#2ecc71", linewidth=2, markersize=6)
            ax.fill_between(range(len(valores)), valores, alpha=0.15, color="#2ecc71")
            ax.set_xticks(range(len(fechas)))
            ax.set_xticklabels(fechas, rotation=30, fontsize=7)
            ax.set_ylabel("Kg", fontsize=8)
            fig.tight_layout()
            canvas_chart = FigureCanvasTkAgg(fig, master=parent)
            canvas_chart.draw()
            canvas_chart.get_tk_widget().pack(fill="x", padx=5, pady=5)
        except Exception:
            f = self._make_table_frame(parent)
            cols = ("pf", "pp", "pc")
            tree = ttk.Treeview(f, columns=cols, show="headings", height=4)
            tree.heading("pf", text="Fecha")
            tree.heading("pp", text="Peso (kg)")
            tree.heading("pc", text="Cambio")
            tree.column("pf", width=100)
            tree.column("pp", width=80)
            tree.column("pc", width=80)
            tree.pack(fill="x")
            prev = None
            for fecha, p in pesos:
                cambio = ""
                if prev is not None:
                    diff = p - prev
                    if diff > 0: cambio = f"+{diff:.1f} kg"
                    elif diff < 0: cambio = f"{diff:.1f} kg"
                    else: cambio = "="
                tree.insert("", "end", values=(fecha, f"{p:.1f}", cambio))
                prev = p

    def _diagnosticos_recurrentes(self, parent, animal_id):
        conn = self.get_db()
        rows = conn.execute(
            "SELECT diagnostico, COUNT(*) as total FROM registros_medicos "
            "WHERE id_animal=? AND diagnostico != '' GROUP BY diagnostico HAVING total > 1 ORDER BY total DESC",
            (animal_id,)).fetchall()
        conn.close()
        if not rows:
            return
        sec, lbl = self._make_section(parent, "Diagnosticos Recurrentes", "#e74c3c")
        f = self._make_table_frame(parent)
        for r in rows:
            row_f = tk.Frame(f, bg="white", padx=8, pady=2)
            row_f.pack(fill="x")
            tk.Label(row_f, text=r["diagnostico"], font=("Segoe UI", 10),
                     bg="white", fg="#c0392b").pack(side="left")
            tk.Label(row_f, text=f"({r['total']} veces)", font=("Segoe UI", 9, "bold"),
                     bg="white", fg="#e74c3c").pack(side="left", padx=10)

    # ---------- DUENNO ----------
    def add_owner_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Nuevo DueÃ±o")
        dialog.geometry("600x550")
        dialog.resizable(False, False)
        dialog.configure(bg="#f0f4f8")
        dialog.transient(self.root)
        dialog.grab_set()
        center_dialog(dialog, self.root)

        main_frame = tk.Frame(dialog, bg="#f0f4f8")
        main_frame.pack(fill='both', expand=True, padx=15, pady=10)

        # Owner fields
        tk.Label(main_frame, text="DATOS DEL DUEÃ‘O", font=("Segoe UI", 11, "bold"),
                 bg="#f0f4f8", fg="#2c3e50").grid(row=0, column=0, columnspan=2, pady=(0,5), sticky='w')

        fields = [("DNI", "dni"), ("Nombre", "nombre"), ("Telefono", "telefono"),
                  ("Email", "email"), ("Direccion", "direccion")]
        entries = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(main_frame, text=label, bg="#f0f4f8", font=("Segoe UI", 10)).grid(
                row=i+1, column=0, sticky="e", padx=5, pady=4)
            e = tk.Entry(main_frame, width=35, font=("Segoe UI", 10))
            e.grid(row=i+1, column=1, padx=5, pady=4, sticky='w')
            entries[key] = e

        # Pet section
        tk.Label(main_frame, text="REGISTRAR MASCOTAS", font=("Segoe UI", 11, "bold"),
                 bg="#f0f4f8", fg="#2c3e50").grid(row=7, column=0, columnspan=3, pady=(10,5), sticky='w')

        pet_fields_frame = tk.Frame(main_frame, bg="#f0f4f8")
        pet_fields_frame.grid(row=8, column=0, columnspan=3, sticky='ew')

        pet_labels = ["Nombre", "Especie", "Raza", "Edad", "Sexo"]
        pet_widgets = {}
        for j, lbl in enumerate(pet_labels):
            tk.Label(pet_fields_frame, text=lbl, bg="#f0f4f8", font=("Segoe UI", 9)).grid(row=0, column=j, padx=3)
        e_pet_nombre = tk.Entry(pet_fields_frame, width=18, font=("Segoe UI", 9))
        e_pet_nombre.grid(row=1, column=0, padx=3)
        e_pet_especie = ttk.Combobox(pet_fields_frame, values=["Perro", "Gato", "Otro"], width=15, font=("Segoe UI", 9))
        e_pet_especie.grid(row=1, column=1, padx=3)
        e_pet_especie.set("Perro")
        e_pet_raza = tk.Entry(pet_fields_frame, width=16, font=("Segoe UI", 9))
        e_pet_raza.grid(row=1, column=2, padx=3)
        e_pet_edad = tk.Spinbox(pet_fields_frame, from_=0, to=50, width=6, font=("Segoe UI", 9))
        e_pet_edad.grid(row=1, column=3, padx=3)
        e_pet_sexo = ttk.Combobox(pet_fields_frame, values=["Macho", "Hembra"], width=10, font=("Segoe UI", 9))
        e_pet_sexo.grid(row=1, column=4, padx=3)
        e_pet_sexo.set("Macho")

        pet_list_frame = tk.Frame(main_frame, bg="white", highlightbackground="#ccc", highlightthickness=1)
        pet_list_frame.grid(row=9, column=0, columnspan=3, sticky='ew', pady=5, ipady=5)
        pet_listbox = tk.Listbox(pet_list_frame, height=4, font=("Segoe UI", 9))
        pet_listbox.pack(fill='x', padx=3, pady=3)
        pets_to_add = []

        def add_pet():
            nom = e_pet_nombre.get().strip()
            if not nom:
                messagebox.showwarning("Error", "Ingrese nombre de la mascota")
                return
            pets_to_add.append({
                "nombre": nom,
                "especie": e_pet_especie.get(),
                "raza": e_pet_raza.get().strip(),
                "edad": int(e_pet_edad.get()) if e_pet_edad.get().isdigit() else 0,
                "sexo": e_pet_sexo.get(),
            })
            pet_listbox.insert('end', f"{nom} - {e_pet_especie.get()} ({e_pet_sexo.get()})")
            e_pet_nombre.delete(0, 'end')
            e_pet_raza.delete(0, 'end')
            e_pet_especie.set("Perro")
            e_pet_sexo.set("Macho")
            e_pet_edad.delete(0, 'end')
            e_pet_edad.insert(0, "0")
            e_pet_nombre.focus_set()

        def remove_pet():
            sel = pet_listbox.curselection()
            if sel:
                idx = sel[0]
                pet_listbox.delete(idx)
                pets_to_add.pop(idx)

        btn_pet_frame = tk.Frame(main_frame, bg="#f0f4f8")
        btn_pet_frame.grid(row=10, column=0, columnspan=3, pady=3)
        tk.Button(btn_pet_frame, text="+ Agregar Mascota", bg="#3498db", fg="white",
                  font=("Segoe UI", 9), relief="flat", padx=10, pady=2,
                  command=add_pet, cursor="hand2").pack(side='left', padx=3)
        tk.Button(btn_pet_frame, text="- Quitar", bg="#e74c3c", fg="white",
                  font=("Segoe UI", 9), relief="flat", padx=10, pady=2,
                  command=remove_pet, cursor="hand2").pack(side='left', padx=3)

        def save():
            if not validate_required([entries["nombre"]], ["Nombre"]):
                return
            conn = self.get_db()
            cursor = conn.execute(
                "INSERT INTO duenos (dni, nombre, telefono, email, direccion) VALUES (?, ?, ?, ?, ?)",
                (entries["dni"].get(), entries["nombre"].get(), entries["telefono"].get(),
                 entries["email"].get(), entries["direccion"].get()))
            dueno_id = cursor.lastrowid
            for pet in pets_to_add:
                conn.execute(
                    "INSERT INTO animales (nombre, especie, raza, edad, sexo, id_dueno) VALUES (?,?,?,?,?,?)",
                    (pet["nombre"], pet["especie"], pet["raza"], pet["edad"], pet["sexo"], dueno_id))
            conn.commit()
            conn.close()
            dialog.destroy()
            self.show_medical_history()
            msg = f"DueÃ±o registrado"
            if pets_to_add:
                msg += f" con {len(pets_to_add)} mascota(s)"
            messagebox.showinfo("Exito", msg)

        tk.Button(main_frame, text="Guardar Todo", bg="#2ecc71", fg="white",
                  font=("Segoe UI", 10, "bold"), relief="flat", padx=30, pady=6,
                  command=save, cursor="hand2").grid(row=11, column=0, columnspan=3, pady=10)

    def show_owner_detail(self, dueno_id):
        conn = self.get_db()
        d = conn.execute("SELECT * FROM duenos WHERE id=?", (dueno_id,)).fetchone()
        conn.close()
        if not d:
            return
        dia = tk.Toplevel(self.root)
        dia.title("Ficha del DueÃ±o")
        dia.geometry("400x280")
        dia.resizable(False, False)
        dia.configure(bg="#e8edf2")
        dia.transient(self.root)
        dia.grab_set()
        center_dialog(dia, self.root)
        data = [
            ("DNI", d["dni"] or "N/A"),
            ("Nombre", d["nombre"]),
            ("Telefono", d["telefono"] or "N/A"),
            ("Email", d["email"] or "N/A"),
            ("Direccion", d["direccion"] or "N/A"),
        ]
        for i, (lbl, val) in enumerate(data):
            tk.Label(dia, text=lbl + ":", font=("Segoe UI", 10, "bold"),
                     bg="#e8edf2", fg="#2c3e50").grid(row=i, column=0, sticky="e", padx=10, pady=6)
            tk.Label(dia, text=val, font=("Segoe UI", 10),
                     bg="#e8edf2", fg="#555").grid(row=i, column=1, sticky="w", padx=10, pady=6)
        tk.Button(dia, text="Cerrar", bg="#e74c3c", fg="white", relief="flat",
                  command=dia.destroy, cursor="hand2").grid(row=len(data), column=1, pady=15, sticky="e")

    def edit_owner_dialog(self, dueno_id, animal_id, detail_frame, reload_callback):
        conn = self.get_db()
        d = conn.execute("SELECT * FROM duenos WHERE id=?", (dueno_id,)).fetchone()
        conn.close()
        if not d:
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Editar DueÃ±o")
        dialog.geometry("450x280")
        dialog.resizable(False, False)
        dialog.configure(bg="#f0f4f8")
        dialog.transient(self.root)
        dialog.grab_set()
        center_dialog(dialog, self.root)
        fields = [("DNI", "dni"), ("Nombre", "nombre"), ("Telefono", "telefono"),
                  ("Email", "email"), ("Direccion", "direccion")]
        entries = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(dialog, text=label, bg="#f0f4f8", font=("Segoe UI", 10)).grid(
                row=i, column=0, sticky="e", padx=10, pady=6)
            e = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
            e.insert(0, d[key] or "")
            e.grid(row=i, column=1, padx=10, pady=6)
            entries[key] = e
        def save():
            if not validate_required([entries["nombre"]], ["Nombre"]):
                return
            conn = self.get_db()
            conn.execute("UPDATE duenos SET dni=?, nombre=?, telefono=?, email=?, direccion=? WHERE id=?",
                         (entries["dni"].get(), entries["nombre"].get(), entries["telefono"].get(),
                          entries["email"].get(), entries["direccion"].get(), dueno_id))
            conn.commit()
            conn.close()
            dialog.destroy()
            self.show_detail(detail_frame, animal_id, reload_callback)
            messagebox.showinfo("Exito", "DueÃ±o actualizado")
        add_keyboard_shortcuts(dialog, save)
        tk.Button(dialog, text="Guardar", bg="#2ecc71", fg="white",
                  font=("Segoe UI", 10), relief="flat", padx=20, pady=5,
                  command=save, cursor="hand2").grid(row=len(fields), column=1, pady=15, sticky="e")

    def export_pdf(self, animal_id):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import cm
            conn = self.get_db()
            a = conn.execute(
                "SELECT a.*, d.nombre as dname, d.telefono as dtel, d.direccion as ddir "
                "FROM animales a JOIN duenos d ON a.id_dueno = d.id WHERE a.id=?",
                (animal_id,)).fetchone()
            regs = conn.execute(
                "SELECT * FROM registros_medicos WHERE id_animal=? ORDER BY fecha DESC",
                (animal_id,)).fetchall()
            vacs = conn.execute(
                "SELECT * FROM vacunas WHERE id_animal=? ORDER BY fecha DESC", (animal_id,)).fetchall()
            conn.close()
            if not a: return
            from tkinter import filedialog
            path = filedialog.asksaveasfilename(defaultextension=".pdf",
                filetypes=[("PDF", "*.pdf")], title="Guardar Historial como PDF")
            if not path: return
            c = canvas.Canvas(path, pagesize=A4)
            w, h = A4
            c.setFont("Helvetica-Bold", 18)
            c.drawString(2*cm, h-2*cm, f"Historial Clinico - {a['nombre']}")
            c.setFont("Helvetica", 11)
            y = h - 3.5*cm
            c.drawString(2*cm, y, f"Especie: {a['especie']}   Raza: {a['raza'] or 'N/A'}")
            y -= 0.8*cm
            c.drawString(2*cm, y, f"Edad: {a['edad']} anios   Peso: {a['peso']} kg")
            y -= 0.8*cm
            c.drawString(2*cm, y, f"DueÃ±o: {a['dname']}   Tel: {a['dtel'] or 'N/A'}")
            y -= 1.5*cm
            c.setFont("Helvetica-Bold", 14)
            c.drawString(2*cm, y, "Registros Medicos")
            y -= 0.8*cm
            c.setFont("Helvetica", 10)
            for r in regs:
                if y < 3*cm:
                    c.showPage()
                    c.setFont("Helvetica", 10)
                    y = h - 2*cm
                c.drawString(2*cm, y, f"{r['fecha']} {r['hora'] or ''} - {r['doctor'] or ''}")
                y -= 0.5*cm
                c.drawString(2.5*cm, y, f"Dx: {r['diagnostico']}")
                y -= 0.5*cm
                c.drawString(2.5*cm, y, f"Tx: {r['tratamiento']}")
                y -= 0.5*cm
                obs = r['observaciones'] or ''
                if obs:
                    c.drawString(2.5*cm, y, f"Obs: {obs[:80]}")
                    y -= 0.5*cm
                y -= 0.3*cm
            if vacs:
                y -= 0.5*cm
                c.setFont("Helvetica-Bold", 14)
                c.drawString(2*cm, y, "Vacunas y Desparasitaciones")
                y -= 0.8*cm
                c.setFont("Helvetica", 10)
                for v in vacs:
                    if y < 3*cm:
                        c.showPage()
                        c.setFont("Helvetica", 10)
                        y = h - 2*cm
                    c.drawString(2*cm, y, f"{v['fecha']} - {v['nombre']} ({v['tipo'].capitalize()})")
                    y -= 0.5*cm
            c.save()
            messagebox.showinfo("Exito", f"PDF guardado en {path}")
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo exportar PDF: {ex}")

    def print_card(self, animal_id):
        try:
            from reportlab.lib.pagesizes import A6
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import cm
            conn = self.get_db()
            a = conn.execute(
                "SELECT a.*, d.nombre as dname, d.telefono as dtel "
                "FROM animales a JOIN duenos d ON a.id_dueno = d.id WHERE a.id=?",
                (animal_id,)).fetchone()
            conn.close()
            if not a: return
            from tkinter import filedialog
            path = filedialog.asksaveasfilename(defaultextension=".pdf",
                filetypes=[("PDF", "*.pdf")], title="Guardar Ficha del Paciente")
            if not path: return
            c = canvas.Canvas(path, pagesize=A6)
            c.setFont("Helvetica-Bold", 14)
            c.drawString(1*cm, 10*cm, a['nombre'])
            c.setFont("Helvetica", 10)
            y = 9*cm
            for lbl, val in [("Especie", a['especie']), ("Raza", a['raza'] or 'N/A'),
                             ("Edad", f"{a['edad']} anios"), ("Peso", f"{a['peso']} kg"),
                             ("DueÃ±o", a['dname']), ("Tel", a['dtel'] or 'N/A')]:
                c.drawString(1*cm, y, f"{lbl}: {val}")
                y -= 0.7*cm
            c.showPage()
            c.save()
            messagebox.showinfo("Exito", f"Ficha guardada en {path}")
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo guardar: {ex}")

    def export_excel(self, animal_id):
        try:
            import csv
            conn = self.get_db()
            a = conn.execute(
                "SELECT a.*, d.nombre as dname FROM animales a JOIN duenos d ON a.id_dueno = d.id WHERE a.id=?",
                (animal_id,)).fetchone()
            regs = conn.execute(
                "SELECT * FROM registros_medicos WHERE id_animal=? ORDER BY fecha DESC",
                (animal_id,)).fetchall()
            conn.close()
            if not a:
                return
            from tkinter import filedialog
            path = filedialog.asksaveasfilename(defaultextension=".csv",
                filetypes=[("CSV", "*.csv")], title="Guardar Historial como CSV")
            if not path:
                return
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["Historial Clinico - " + a["nombre"]])
                w.writerow(["Especie", a["especie"], "Raza", a["raza"] or "N/A",
                            "Edad", str(a["edad"]), "Peso", str(a["peso"]) + " kg"])
                w.writerow(["Dueno", a["dname"]])
                w.writerow([])
                w.writerow(["Fecha", "Hora", "Peso", "Doctor", "Diagnostico", "Tratamiento", "Observaciones"])
                for r in regs:
                    w.writerow([r["fecha"], r["hora"] or "", str(r["peso"]) if r["peso"] else "",
                                r["doctor"] or "", r["diagnostico"], r["tratamiento"],
                                r["observaciones"] or ""])
            messagebox.showinfo("Exito", f"Historial exportado a {path}")
        except Exception as ex:
            messagebox.showerror("Error", f"No se pudo exportar: {ex}")

    # ---------- ANIMAL ----------
    def add_animal_dialog(self, callback=None):
        dialog = tk.Toplevel(self.root)
        dialog.title("Nuevo Animal")
        dialog.geometry("500x450")
        dialog.resizable(False, False)
        dialog.configure(bg="#f0f4f8")
        dialog.transient(self.root)
        dialog.grab_set()
        center_dialog(dialog, self.root)

        selected_photo = tk.StringVar(value="")

        tk.Label(dialog, text="Nombre", bg="#f0f4f8", font=("Segoe UI", 10)).grid(
            row=0, column=0, sticky="e", padx=10, pady=6)
        e_nombre = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
        e_nombre.grid(row=0, column=1, padx=10, pady=6)

        razas_perro = [
            "Labrador Retriever", "Golden Retriever", "Pastor Aleman", "Bulldog Frances",
            "Bulldog Ingles", "Beagle", "Caniche", "Chihuahua", "Yorkshire Terrier",
            "Boxer", "Rottweiler", "Doberman", "Husky Siberiano", "Shih Tzu",
            "Pug", "Border Collie", "Dalmata", "Cocker Spaniel", "Pomerania",
            "Bichon FrisÃ©", "Maltes", "Schnauzer", "Pastor Belga", "Samoyedo",
            "Gran Danes", "San Bernardo", "Akita Inu", "Shiba Inu", "Pit Bull",
            "American Staffordshire", "Weimaraner", "Galgos", "Whippet",
            "Terrier Escoces", "West Highland White Terrier", "Corgi",
            "Carlino", "Boston Terrier", "Jack Russell Terrier", "Fox Terrier",
            "Basenji", "Chow Chow", "Shar Pei", "Lhasa Apso", "Bulldog Americano",
            "Mastin Napolitano", "Boyero de Berna", "Papillon", "Habanero",
            "Cavalier King Charles Spaniel", "Otra"
        ]
        razas_gato = [
            "Mestizo", "Persa", "SiamÃ©s", "Maine Coon", "Bengala",
            "Sphynx", "Ragdoll", "British Shorthair", "Scottish Fold",
            "Abisinio", "Bosque de Noruega", "Ruso Azul", "Oriental",
            "Cornish Rex", "Devon Rex", "Burmes", "Tonquines",
            "Siberiano", "Savannah", "Birmano", "Angora Turco",
            "La Perm", "Mau Egipcio", "Sokoke", "American Shorthair",
            "Exotico", "Himalayo", "Ocicat", "Selkirk Rex",
            "Toyger", "Otra"
        ]

        def actualizar_razas(*args):
            esp = e_especie.get()
            if esp == "Perro":
                e_raza.set_full_values(razas_perro)
                e_raza.set("")
            elif esp == "Gato":
                e_raza.set_full_values(razas_gato)
                e_raza.set("")
            else:
                e_raza.set_full_values([])
                e_raza.set("")

        tk.Label(dialog, text="Especie", bg="#f0f4f8", font=("Segoe UI", 10)).grid(
            row=1, column=0, sticky="e", padx=10, pady=6)
        e_especie = ttk.Combobox(dialog, values=["Perro", "Gato", "Otros"],
                                 width=37, font=("Segoe UI", 10))
        e_especie.grid(row=1, column=1, padx=10, pady=6)
        e_especie.bind("<<ComboboxSelected>>", actualizar_razas)

        tk.Label(dialog, text="Raza", bg="#f0f4f8", font=("Segoe UI", 10)).grid(
            row=2, column=0, sticky="e", padx=10, pady=6)
        e_raza = AutocompleteEntry(dialog, full_values=[], width=37, font=("Segoe UI", 10))
        e_raza.grid(row=2, column=1, padx=10, pady=6)

        tk.Label(dialog, text="Edad", bg="#f0f4f8", font=("Segoe UI", 10)).grid(
            row=3, column=0, sticky="e", padx=10, pady=6)
        edad_frame = tk.Frame(dialog, bg="#f0f4f8")
        edad_frame.grid(row=3, column=1, padx=10, pady=6, sticky="w")
        e_edad = tk.Entry(edad_frame, width=10, font=("Segoe UI", 10))
        e_edad.pack(side="left")
        tk.Label(edad_frame, text="anios", bg="#f0f4f8", font=("Segoe UI", 9)).pack(side="left", padx=3)
        from tkcalendar import DateEntry
        tk.Label(edad_frame, text="  Fec.Nac:", bg="#f0f4f8", font=("Segoe UI", 9)).pack(side="left", padx=(10, 2))
        e_fecnac = DateEntry(edad_frame, width=12, font=("Segoe UI", 9),
                             background="#2c3e50", foreground="white",
                             borderwidth=2, date_pattern="yyyy-mm-dd")
        e_fecnac.pack(side="left")
        def calc_edad(*args):
            try:
                nac = e_fecnac.get_date()
                hoy = date.today()
                edad_calc = hoy.year - nac.year - ((hoy.month, hoy.day) < (nac.month, nac.day))
                e_edad.delete(0, "end")
                e_edad.insert(0, str(edad_calc))
            except:
                pass
        e_fecnac.bind("<<DateEntrySelected>>", calc_edad)

        tk.Label(dialog, text="Peso (kg)", bg="#f0f4f8", font=("Segoe UI", 10)).grid(
            row=4, column=0, sticky="e", padx=10, pady=6)
        e_peso = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
        e_peso.grid(row=4, column=1, padx=10, pady=6)

        tk.Label(dialog, text="DueÃ±o", bg="#f0f4f8", font=("Segoe UI", 10)).grid(
            row=5, column=0, sticky="e", padx=10, pady=6)
        dueno_frame = tk.Frame(dialog, bg="#f0f4f8")
        dueno_frame.grid(row=8, column=1, padx=10, pady=6, sticky="w")

        def refresh_owners():
            conn = self.get_db()
            duenos = conn.execute("SELECT id, nombre FROM duenos ORDER BY nombre").fetchall()
            conn.close()
            dueno_map.clear()
            for d in duenos:
                dueno_map[d["nombre"]] = d["id"]
            e_dueno.config(values=list(dueno_map.keys()))

        dueno_map = {}
        e_dueno = ttk.Combobox(dueno_frame, width=33, font=("Segoe UI", 10))
        e_dueno.pack(side="left")

        def add_owner_mini():
            d2 = tk.Toplevel(dialog)
            d2.title("Nuevo DueÃ±o")
            d2.geometry("400x250")
            d2.resizable(False, False)
            d2.configure(bg="#f0f4f8")
            d2.transient(dialog)
            d2.grab_set()
            center_dialog(d2, dialog)
            tk.Label(d2, text="DNI:", bg="#f0f4f8", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="e", padx=5, pady=5)
            e_dni = tk.Entry(d2, width=30, font=("Segoe UI", 10))
            e_dni.grid(row=0, column=1, padx=5, pady=5)
            tk.Label(d2, text="Nombre:", bg="#f0f4f8", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="e", padx=5, pady=5)
            e_nom = tk.Entry(d2, width=30, font=("Segoe UI", 10))
            e_nom.grid(row=1, column=1, padx=5, pady=5)
            tk.Label(d2, text="Telefono:", bg="#f0f4f8", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="e", padx=5, pady=5)
            e_tel = tk.Entry(d2, width=30, font=("Segoe UI", 10))
            e_tel.grid(row=2, column=1, padx=5, pady=5)
            tk.Label(d2, text="Direccion:", bg="#f0f4f8", font=("Segoe UI", 10)).grid(row=3, column=0, sticky="e", padx=5, pady=5)
            e_dir = tk.Entry(d2, width=30, font=("Segoe UI", 10))
            e_dir.grid(row=3, column=1, padx=5, pady=5)
            tk.Label(d2, text="Email:", bg="#f0f4f8", font=("Segoe UI", 10)).grid(row=4, column=0, sticky="e", padx=5, pady=5)
            e_email = tk.Entry(d2, width=30, font=("Segoe UI", 10))
            e_email.grid(row=4, column=1, padx=5, pady=5)
            def save_mini():
                conn = self.get_db()
                conn.execute("INSERT INTO duenos (nombre, dni, telefono, direccion, email) VALUES (?, ?, ?, ?, ?)",
                             (e_nom.get(), e_dni.get(), e_tel.get(), e_dir.get(), e_email.get()))
                conn.commit()
                conn.close()
                refresh_owners()
                e_dueno.set(e_nom.get())
                d2.destroy()
            tk.Button(d2, text="Guardar", bg="#2ecc71", fg="white", relief="flat",
                      command=save_mini, cursor="hand2").grid(row=5, column=1, pady=10, sticky="e")

        tk.Button(dueno_frame, text="+", bg="#3498db", fg="white", relief="flat",
                  width=3, command=add_owner_mini, cursor="hand2").pack(side="left", padx=(3, 0))

        refresh_owners()

        def choose_photo():
            path = filedialog.askopenfilename(
                filetypes=[("Imagenes", "*.jpg *.jpeg *.png *.bmp *.gif")])
            if path:
                selected_photo.set(path)
                photo_label.config(text="Foto: " + os.path.basename(path))

        tk.Button(dialog, text="Seleccionar Foto", bg="#3498db", fg="white",
                  relief="flat", command=choose_photo, cursor="hand2").grid(
            row=9, column=0, padx=10, pady=6)
        photo_label = tk.Label(dialog, text="Ninguna foto seleccionada",
                               bg="#f0f4f8", fg="#999", font=("Segoe UI", 9))
        photo_label.grid(row=9, column=1, padx=10, pady=6, sticky="w")

        def save():
            if not validate_required([e_nombre, e_edad, e_peso, e_dueno], ["Nombre", "Edad", "Peso", "DueÃ±o"]):
                return
            try:
                int(e_edad.get())
                float(e_peso.get())
            except ValueError:
                messagebox.showerror("Error", "Edad debe ser numero entero y Peso debe ser numero")
                return
            try:
                conn = self.get_db()
                fecnac = ""
                try:
                    fecnac = e_fecnac.get()
                except:
                    pass
                cur = conn.execute(
                    "INSERT INTO animales (nombre, especie, raza, edad, peso, sexo, color, fecha_nacimiento, esterilizado, id_dueno, foto) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (e_nombre.get(), e_especie.get(), e_raza.get(),
                     int(e_edad.get()), float(e_peso.get()),
                     e_sexo.get(), e_color.get(), fecnac,
                     1 if e_esterilizado.get() == "Si" else 0,
                     dueno_map[e_dueno.get()], ""))
                animal_id = cur.lastrowid
                if selected_photo.get():
                    ext = os.path.splitext(selected_photo.get())[1]
                    dest = os.path.join(PHOTOS_DIR, str(animal_id) + ext)
                    shutil.copy2(selected_photo.get(), dest)
                    conn.execute("UPDATE animales SET foto=? WHERE id=?",
                                 (str(animal_id) + ext, animal_id))
                conn.commit()
                conn.close()
                dialog.destroy()
                if callback:
                    callback()
                self.show_medical_history()
                messagebox.showinfo("Exito", "Animal registrado")
            except Exception as ex:
                messagebox.showerror("Error", str(ex))

        tk.Button(dialog, text="Guardar", bg="#2ecc71", fg="white",
                  font=("Segoe UI", 10), relief="flat", padx=20, pady=5,
                  command=save, cursor="hand2").grid(row=10, column=1, pady=10, sticky="e")
        dialog.bind("<Escape>", lambda e: dialog.destroy())
        dialog.bind("<Control-Return>", lambda e: save())

    def edit_animal_dialog(self, animal_id, reload_callback):
        conn = self.get_db()
        a = conn.execute("SELECT * FROM animales WHERE id=?", (animal_id,)).fetchone()
        duenos = conn.execute("SELECT id, nombre FROM duenos ORDER BY nombre").fetchall()
        conn.close()
        if not a:
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Editar Animal")
        dialog.geometry("500x450")
        dialog.resizable(False, False)
        dialog.configure(bg="#e8edf2")
        dialog.transient(self.root)
        dialog.grab_set()
        center_dialog(dialog, self.root)
        tk.Label(dialog, text="Nombre", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="e", padx=10, pady=6)
        e_nombre = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
        e_nombre.insert(0, a["nombre"])
        e_nombre.grid(row=0, column=1, padx=10, pady=6)
        tk.Label(dialog, text="Especie", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=1, column=0, sticky="e", padx=10, pady=6)
        e_especie = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
        e_especie.insert(0, a["especie"] or "")
        e_especie.grid(row=1, column=1, padx=10, pady=6)
        tk.Label(dialog, text="Raza", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="e", padx=10, pady=6)
        e_raza = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
        e_raza.insert(0, a["raza"] or "")
        e_raza.grid(row=2, column=1, padx=10, pady=6)
        tk.Label(dialog, text="Edad", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=3, column=0, sticky="e", padx=10, pady=6)
        e_edad = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
        e_edad.insert(0, str(a["edad"]))
        e_edad.grid(row=3, column=1, padx=10, pady=6)
        tk.Label(dialog, text="Peso (kg)", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=4, column=0, sticky="e", padx=10, pady=6)
        e_peso = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
        e_peso.insert(0, str(a["peso"]))
        e_peso.grid(row=4, column=1, padx=10, pady=6)
        dueno_map = {d["nombre"]: d["id"] for d in duenos}
        tk.Label(dialog, text="DueÃ±o", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=5, column=0, sticky="e", padx=10, pady=6)
        e_dueno = ttk.Combobox(dialog, values=list(dueno_map.keys()), width=37, font=("Segoe UI", 10))
        dueno_orig = conn.execute("SELECT nombre FROM duenos WHERE id=?", (a["id_dueno"],)).fetchone()
        if dueno_orig:
            e_dueno.set(dueno_orig["nombre"])
        e_dueno.grid(row=5, column=1, padx=10, pady=6)
        def save():
            conn = self.get_db()
            conn.execute("UPDATE animales SET nombre=?, especie=?, raza=?, edad=?, peso=?, id_dueno=? WHERE id=?",
                         (e_nombre.get(), e_especie.get(), e_raza.get(), int(e_edad.get()),
                          float(e_peso.get()), dueno_map[e_dueno.get()], animal_id))
            conn.commit()
            conn.close()
            dialog.destroy()
            reload_callback()
            messagebox.showinfo("Exito", "Animal actualizado")
        tk.Button(dialog, text="Guardar", bg="#2ecc71", fg="white",
                  font=("Segoe UI", 10), relief="flat", padx=20, pady=5,
                  command=save, cursor="hand2").grid(row=6, column=1, pady=15, sticky="e")

    def edit_registro_dialog(self, reg_id, animal_id, callback):
        conn = self.get_db()
        r = conn.execute("SELECT * FROM registros_medicos WHERE id=?", (reg_id,)).fetchone()
        conn.close()
        if not r:
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Editar Consulta")
        dialog.geometry("450x340")
        dialog.resizable(False, False)
        dialog.configure(bg="#e8edf2")
        dialog.transient(self.root)
        dialog.grab_set()
        center_dialog(dialog, self.root)
        tk.Label(dialog, text="Peso (kg)", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="e", padx=10, pady=6)
        e_peso = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
        e_peso.insert(0, str(r["peso"]) if r["peso"] else "")
        e_peso.grid(row=0, column=1, padx=10, pady=6)
        e_doctor = self._make_doctor_frame(dialog, 1, r["doctor"] or "")
        tk.Label(dialog, text="Diagnostico", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=2, column=0, sticky="e", padx=10, pady=6)
        e_diag = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
        e_diag.insert(0, r["diagnostico"] or "")
        e_diag.grid(row=2, column=1, padx=10, pady=6)
        tk.Label(dialog, text="Tratamiento", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=3, column=0, sticky="e", padx=10, pady=6)
        e_trat = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
        e_trat.insert(0, r["tratamiento"] or "")
        e_trat.grid(row=3, column=1, padx=10, pady=6)
        tk.Label(dialog, text="Observaciones", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=4, column=0, sticky="e", padx=10, pady=6)
        e_obs = tk.Text(dialog, width=30, height=2, font=("Segoe UI", 10))
        e_obs.insert("1.0", r["observaciones"] or "")
        e_obs.grid(row=4, column=1, padx=10, pady=6)
        def save():
            conn = self.get_db()
            peso = e_peso.get().strip()
            peso_val = float(peso) if peso else None
            conn.execute("UPDATE registros_medicos SET peso=?, doctor=?, diagnostico=?, tratamiento=?, observaciones=? WHERE id=?",
                         (peso_val, e_doctor.get(), e_diag.get(), e_trat.get(), e_obs.get("1.0", "end-1c"), reg_id))
            conn.commit()
            conn.close()
            dialog.destroy()
            callback()
            messagebox.showinfo("Exito", "Registro actualizado")
        tk.Button(dialog, text="Guardar", bg="#2ecc71", fg="white",
                  font=("Segoe UI", 10), relief="flat", padx=20, pady=5,
                  command=save, cursor="hand2").grid(row=5, column=1, pady=15, sticky="e")

    def _add_signos_vitales_dialog(self, animal_id, detail_frame, reload_callback):
        dialog = tk.Toplevel(self.root)
        dialog.title("Agregar Signos Vitales")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.configure(bg="#e8edf2")
        dialog.transient(self.root)
        dialog.grab_set()
        center_dialog(dialog, self.root)
        conn = self.get_db()
        registros = conn.execute(
            "SELECT id, fecha, diagnostico FROM registros_medicos WHERE id_animal=? ORDER BY fecha DESC",
            (animal_id,)).fetchall()
        conn.close()
        reg_map = {f"{r['fecha']} - {r['diagnostico'][:30]}": r["id"] for r in registros}
        tk.Label(dialog, text="Consulta:", bg="#e8edf2", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="e", padx=10, pady=6)
        e_reg = ttk.Combobox(dialog, values=list(reg_map.keys()), width=35, font=("Segoe UI", 10))
        e_reg.grid(row=0, column=1, padx=10, pady=6)
        if reg_map:
            e_reg.set(list(reg_map.keys())[0])
        fields_data = [(1, "Temperatura (C)", "temp"), (2, "Frec. Cardiaca (lpm)", "fc"),
                       (3, "Frec. Respiratoria (rpm)", "fr"), (4, "Presion Sistolica", "sis"),
                       (5, "Presion Diastolica", "dis")]
        entries = {}
        for row, label, key in fields_data:
            tk.Label(dialog, text=label, bg="#e8edf2", font=("Segoe UI", 10)).grid(row=row, column=0, sticky="e", padx=10, pady=4)
            e = tk.Entry(dialog, width=20, font=("Segoe UI", 10))
            e.grid(row=row, column=1, padx=10, pady=4, sticky="w")
            entries[key] = e

        def save():
            if not e_reg.get():
                messagebox.showerror("Error", "Seleccione una consulta"); return
            conn = self.get_db()
            reg_id = reg_map[e_reg.get()]
            conn.execute(
                "INSERT OR REPLACE INTO signos_vitales (id_registro, temperatura, frecuencia_cardiaca, frecuencia_respiratoria, presion_sistolica, presion_diastolica) VALUES (?,?,?,?,?,?)",
                (reg_id,
                 float(entries["temp"].get()) if entries["temp"].get() else None,
                 int(entries["fc"].get()) if entries["fc"].get() else None,
                 int(entries["fr"].get()) if entries["fr"].get() else None,
                 int(entries["sis"].get()) if entries["sis"].get() else None,
                 int(entries["dis"].get()) if entries["dis"].get() else None))
            conn.commit()
            conn.close()
            dialog.destroy()
            self.show_detail(detail_frame, animal_id, reload_callback)

        tk.Button(dialog, text="Guardar", bg="#2ecc71", fg="white",
                  font=("Segoe UI", 10), relief="flat", padx=20, pady=5,
                  command=save, cursor="hand2").grid(row=6, column=1, pady=15, sticky="e")

    def _make_doctor_frame(self, parent, row, default=""):
        frame = tk.Frame(parent, bg="#e8edf2")
        frame.grid(row=row, column=0, columnspan=2, padx=10, pady=6, sticky="w")
        tk.Label(frame, text="Doctor", bg="#e8edf2", font=("Segoe UI", 10)).pack(side="left", padx=(0, 8))
        valores = self.get_doctores()
        cb = ttk.Combobox(frame, values=valores, width=30, font=("Segoe UI", 10), state="normal")
        if default:
            cb.set(default)
        cb.pack(side="left")
        tk.Button(frame, text="+", bg="#2ecc71", fg="white", font=("Segoe UI", 9, "bold"),
                  relief="flat", width=2, cursor="hand2",
                  command=lambda: (self.manage_doctores_dialog(
                      lambda: cb.configure(values=self.get_doctores())))).pack(side="left", padx=(4, 0))
        return cb
    def add_appointment_dialog(self, animal_id=None):
        from tkcalendar import DateEntry
        dialog = tk.Toplevel(self.root)
        dialog.title("Nueva Cita")
        dialog.geometry("450x280")
        dialog.resizable(False, False)
        dialog.configure(bg="#f0f4f8")
        dialog.transient(self.root)
        dialog.grab_set()
        center_dialog(dialog, self.root)

        conn = self.get_db()
        animales = conn.execute(
            "SELECT a.id, a.nombre, d.nombre as dname "
            "FROM animales a JOIN duenos d ON a.id_dueno = d.id "
            "ORDER BY a.nombre").fetchall()
        conn.close()
        animal_map = {a["nombre"] + " (" + a["dname"] + ")": a["id"] for a in animales}

        tk.Label(dialog, text="Animal", bg="#f0f4f8", font=("Segoe UI", 10)).grid(
            row=0, column=0, sticky="e", padx=10, pady=8)
        e_animal = AutocompleteEntry(dialog, full_values=list(animal_map.keys()),
                                        width=37, font=("Segoe UI", 10))
        e_animal.grid(row=0, column=1, padx=10, pady=8)

        tk.Label(dialog, text="Tipo", bg="#f0f4f8", font=("Segoe UI", 10)).grid(
            row=1, column=0, sticky="e", padx=10, pady=8)
        e_tipo = ttk.Combobox(dialog, values=["veterinaria", "grooming"], width=37, font=("Segoe UI", 10))
        e_tipo.set("veterinaria")
        e_tipo.grid(row=1, column=1, padx=10, pady=8)

        if animal_id:
            for name, aid in animal_map.items():
                if aid == animal_id:
                    e_animal.set(name)
                    break

        tk.Label(dialog, text="Fecha", bg="#f0f4f8", font=("Segoe UI", 10)).grid(
            row=2, column=0, sticky="e", padx=10, pady=8)
        e_fecha = DateEntry(dialog, width=37, font=("Segoe UI", 10),
                            background="#2c3e50", foreground="white",
                            borderwidth=2, date_pattern="yyyy-mm-dd")
        e_fecha.grid(row=2, column=1, padx=10, pady=8)

        tk.Label(dialog, text="Precio", bg="#f0f4f8", font=("Segoe UI", 10)).grid(
            row=3, column=0, sticky="e", padx=10, pady=8)
        e_precio = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
        e_precio.grid(row=3, column=1, padx=10, pady=8)

        motivos = ["Consulta general", "Vacunacion", "Desparasitacion",
                   "Cirugia", "Control", "Emergencia", "Peluqueria",
                   "Analisis", "Hospitalizacion", "Otros"]

        def motivo_selected(*args):
            if e_motivo.get() == "Otros":
                e_motivo.config(state="normal")

        tk.Label(dialog, text="Motivo", bg="#f0f4f8", font=("Segoe UI", 10)).grid(
            row=2, column=0, sticky="e", padx=10, pady=8)
        e_motivo = ttk.Combobox(dialog, values=motivos, width=37, font=("Segoe UI", 10))
        e_motivo.grid(row=4, column=1, padx=10, pady=8)
        e_motivo.bind("<<ComboboxSelected>>", motivo_selected)

        def save():
            animal_id = animal_map[e_animal.get()]
            conn = self.get_db()
            id_dueno = conn.execute(
                "SELECT id_dueno FROM animales WHERE id=?", (animal_id,)).fetchone()[0]
            animal_nombre = conn.execute(
                "SELECT nombre FROM animales WHERE id=?", (animal_id,)).fetchone()[0]
            dueno_info = conn.execute(
                "SELECT nombre, telefono FROM duenos WHERE id=?", (id_dueno,)).fetchone()
            conn.execute(
                "INSERT INTO citas (id_animal, id_dueno, fecha, motivo, tipo, precio) VALUES (?, ?, ?, ?, ?, ?)",
                (animal_id, id_dueno, e_fecha.get(), e_motivo.get(), e_tipo.get(), float(e_precio.get() or 0)))
            conn.commit()
            conn.close()
            dialog.destroy()
            receipt = (
                "--- COMPROBANTE DE CITA ---\n\n"
                f"Animal: {animal_nombre}\n"
                f"DueÃ±o: {dueno_info['nombre']}\n"
                f"Tel: {dueno_info['telefono'] or 'N/A'}\n"
                f"Fecha: {e_fecha.get()}\n"
                f"Motivo: {e_motivo.get()}\n\n"
                "-----------------------------"
            )
            messagebox.showinfo("Cita Agendada", receipt)

        tk.Button(dialog, text="Guardar", bg="#2ecc71", fg="white",
                  font=("Segoe UI", 10), relief="flat", padx=20, pady=5,
                  command=save, cursor="hand2").grid(row=5, column=1, pady=15, sticky="e")

    # ---------- REGISTRO MEDICO ----------
    def add_medical_record_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Nueva Consulta")
        dialog.geometry("450x340")
        dialog.resizable(False, False)
        dialog.configure(bg="#e8edf2")
        dialog.transient(self.root)
        dialog.grab_set()
        center_dialog(dialog, self.root)

        conn = self.get_db()
        animales = conn.execute(
            "SELECT a.id, a.nombre, d.nombre as dname "
            "FROM animales a JOIN duenos d ON a.id_dueno = d.id "
            "ORDER BY a.nombre").fetchall()
        conn.close()
        animal_map = {a["nombre"] + " (" + a["dname"] + ")": a["id"] for a in animales}

        now = datetime.now()

        tk.Label(dialog, text="Animal", bg="#e8edf2", font=("Segoe UI", 10)).grid(
            row=0, column=0, sticky="e", padx=10, pady=6)
        e_animal = AutocompleteEntry(dialog, full_values=list(animal_map.keys()),
                                        width=37, font=("Segoe UI", 10))
        e_animal.grid(row=0, column=1, padx=10, pady=6)

        tk.Label(dialog, text="Peso (kg)", bg="#e8edf2", font=("Segoe UI", 10)).grid(
            row=1, column=0, sticky="e", padx=10, pady=6)
        e_peso = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
        e_peso.grid(row=1, column=1, padx=10, pady=6)

        e_doctor = self._make_doctor_frame(dialog, 2)

        tk.Label(dialog, text="Diagnostico", bg="#e8edf2", font=("Segoe UI", 10)).grid(
            row=3, column=0, sticky="e", padx=10, pady=6)
        e_diag = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
        e_diag.grid(row=3, column=1, padx=10, pady=6)

        tk.Label(dialog, text="Tratamiento", bg="#e8edf2", font=("Segoe UI", 10)).grid(
            row=4, column=0, sticky="e", padx=10, pady=6)
        e_trat = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
        e_trat.grid(row=4, column=1, padx=10, pady=6)

        tk.Label(dialog, text="Observaciones", bg="#e8edf2", font=("Segoe UI", 10)).grid(
            row=5, column=0, sticky="e", padx=10, pady=6)
        e_obs = tk.Text(dialog, width=30, height=2, font=("Segoe UI", 10))
        e_obs.grid(row=5, column=1, padx=10, pady=6)

        def save():
            conn = self.get_db()
            peso = e_peso.get().strip()
            peso_val = float(peso) if peso else None
            conn.execute(
                "INSERT INTO registros_medicos (id_animal, fecha, hora, peso, doctor, diagnostico, tratamiento, observaciones) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (animal_map[e_animal.get()], str(date.today()),
                 datetime.now().strftime("%H:%M"), peso_val, e_doctor.get(),
                 e_diag.get(), e_trat.get(), e_obs.get("1.0", "end-1c")))
            conn.commit()
            conn.close()
            dialog.destroy()
            self.show_medical_history()
            messagebox.showinfo("Exito", "Registro agregado")

        tk.Button(dialog, text="Guardar", bg="#2ecc71", fg="white",
                  font=("Segoe UI", 10), relief="flat", padx=20, pady=5,
                  command=save, cursor="hand2").grid(row=6, column=1, pady=15, sticky="e")

    def add_medical_record_for(self, animal_id, callback=None):
        dialog = tk.Toplevel(self.root)
        dialog.title("Nueva Consulta")
        dialog.geometry("450x320")
        dialog.resizable(False, False)
        dialog.configure(bg="#e8edf2")
        dialog.transient(self.root)
        dialog.grab_set()
        center_dialog(dialog, self.root)

        now = datetime.now()

        tk.Label(dialog, text="Peso (kg)", bg="#e8edf2", font=("Segoe UI", 10)).grid(
            row=0, column=0, sticky="e", padx=10, pady=6)
        e_peso = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
        e_peso.grid(row=0, column=1, padx=10, pady=6)

        e_doctor = self._make_doctor_frame(dialog, 1)

        tk.Label(dialog, text="Diagnostico", bg="#e8edf2", font=("Segoe UI", 10)).grid(
            row=2, column=0, sticky="e", padx=10, pady=6)
        e_diag = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
        e_diag.grid(row=2, column=1, padx=10, pady=6)

        tk.Label(dialog, text="Tratamiento", bg="#e8edf2", font=("Segoe UI", 10)).grid(
            row=3, column=0, sticky="e", padx=10, pady=6)
        e_trat = tk.Entry(dialog, width=40, font=("Segoe UI", 10))
        e_trat.grid(row=3, column=1, padx=10, pady=6)

        tk.Label(dialog, text="Observaciones", bg="#e8edf2", font=("Segoe UI", 10)).grid(
            row=4, column=0, sticky="e", padx=10, pady=6)
        e_obs = tk.Text(dialog, width=30, height=2, font=("Segoe UI", 10))
        e_obs.grid(row=4, column=1, padx=10, pady=6)

        def save():
            conn = self.get_db()
            peso = e_peso.get().strip()
            peso_val = float(peso) if peso else None
            conn.execute(
                "INSERT INTO registros_medicos (id_animal, fecha, hora, peso, doctor, diagnostico, tratamiento, observaciones) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (animal_id, str(date.today()),
                 datetime.now().strftime("%H:%M"), peso_val, e_doctor.get(),
                 e_diag.get(), e_trat.get(), e_obs.get("1.0", "end-1c")))
            conn.commit()
            conn.close()
            dialog.destroy()
            if callback:
                callback()
            messagebox.showinfo("Exito", "Registro agregado")

        tk.Button(dialog, text="Guardar", bg="#2ecc71", fg="white",
                  font=("Segoe UI", 10), relief="flat", padx=20, pady=5,
                  command=save, cursor="hand2").grid(row=5, column=1, pady=15, sticky="e")



    # ---------- GROOMING / PELUQUERIA ----------
    def show_grooming(self):
        self.clear_frame()
        main = tk.Frame(self.root, bg='#f0f4f8')
        main.pack(fill='both', expand=True, padx=20, pady=15)

        tk.Label(main, text='Peluqueria / Grooming', font=('Segoe UI', 16, 'bold'),
                 bg='#f0f4f8', fg='#2c3e50').pack(anchor='w')

        notebook = ttk.Notebook(main)
        notebook.pack(fill='both', expand=True, pady=(10, 0))

        # Tab 1: Servicios
        tab1 = tk.Frame(notebook, bg='#f0f4f8')
        notebook.add(tab1, text='Servicios')

        top1 = tk.Frame(tab1, bg='#f0f4f8')
        top1.pack(fill='x')
        tk.Button(top1, text='+ Nuevo Servicio', bg='#2ecc71', fg='white',
                  font=('Segoe UI', 9), relief='flat', padx=10, pady=3,
                  command=self.add_grooming_service_dialog, cursor='hand2').pack(side='right')

        cols_s = ('id', 'nombre', 'descripcion', 'precio', 'tipo')
        tree_s = ttk.Treeview(tab1, columns=cols_s, show='headings', height=12)
        tree_s.heading('id', text='ID')
        tree_s.heading('nombre', text='Nombre')
        tree_s.heading('descripcion', text='Descripcion')
        tree_s.heading('precio', text='Precio')
        tree_s.heading('tipo', text='Tipo')
        tree_s.column('id', width=40)
        tree_s.column('nombre', width=200)
        tree_s.column('descripcion', width=300)
        tree_s.column('precio', width=70)
        tree_s.column('tipo', width=100)
        tree_s.pack(fill='both', expand=True, pady=5)

        def load_servicios():
            for item in tree_s.get_children():
                tree_s.delete(item)
            conn = self.get_db()
            rows = conn.execute('SELECT * FROM servicios_grooming ORDER BY nombre').fetchall()
            conn.close()
            for r in rows:
                tree_s.insert('', 'end', values=(r['id'], r['nombre'], r['descripcion'],
                                               f'S/.{r["precio"]:.2f}', r['tipo']))

        load_servicios()

        def delete_servicio():
            sel = tree_s.selection()
            if not sel: return
            vals = tree_s.item(sel[0], 'values')
            if messagebox.askyesno('Confirmar', 'Eliminar servicio?'):
                conn = self.get_db()
                conn.execute('DELETE FROM servicios_grooming WHERE id=?', (int(vals[0]),))
                conn.commit()
                conn.close()
                load_servicios()

        btn_s = tk.Frame(tab1, bg='#f0f4f8')
        btn_s.pack(fill='x')
        tk.Button(btn_s, text='Eliminar', bg='#e74c3c', fg='white',
                  font=('Segoe UI', 9), relief='flat', padx=10, pady=2,
                  command=delete_servicio, cursor='hand2').pack(side='left', padx=2)

        # Tab 2: Historial Grooming
        tab2 = tk.Frame(notebook, bg='#f0f4f8')
        notebook.add(tab2, text='Historial Grooming')

        tabla_frame = tk.Frame(tab2, bg='#f0f4f8')
        tabla_frame.pack(fill='both', expand=True)

        # Top: search by DNI or name
        search_frame = tk.Frame(tabla_frame, bg='#f0f4f8')
        search_frame.pack(fill='x', pady=(0, 5))
        tk.Label(search_frame, text='Buscar por DNI o Dueño:', bg='#f0f4f8',
                 font=('Segoe UI', 9)).pack(side='left', padx=(0, 5))
        e_buscar = tk.Entry(search_frame, width=30, font=('Segoe UI', 10))
        e_buscar.pack(side='left', padx=2)

        cols_h = ('fecha', 'animal', 'dueno', 'dueno_dni', 'servicio', 'precio', 'visitas')
        tree_h = ttk.Treeview(tabla_frame, columns=cols_h, show='headings', height=12)
        tree_h.heading('fecha', text='Fecha')
        tree_h.heading('animal', text='Animal')
        tree_h.heading('dueno', text='Dueño')
        tree_h.heading('dueno_dni', text='DNI')
        tree_h.heading('servicio', text='Servicio')
        tree_h.heading('precio', text='Precio')
        tree_h.heading('visitas', text='Visitas')
        tree_h.column('fecha', width=80)
        tree_h.column('animal', width=130)
        tree_h.column('dueno', width=130)
        tree_h.column('dueno_dni', width=80)
        tree_h.column('servicio', width=130)
        tree_h.column('precio', width=60)
        tree_h.column('visitas', width=50)
        tree_h.pack(fill='both', expand=True, pady=5)

        def load_historial(filter_text=''):
            for item in tree_h.get_children():
                tree_h.delete(item)
            conn = self.get_db()
            rows = conn.execute(
                'SELECT hg.fecha, a.nombre as animal, d.nombre as dueno, d.dni as dueno_dni, '
                'sg.nombre as servicio, hg.precio, hg.id_animal '
                'FROM historial_grooming hg '
                'JOIN animales a ON hg.id_animal = a.id '
                'JOIN duenos d ON a.id_dueno = d.id '
                'LEFT JOIN servicios_grooming sg ON hg.id_servicio = sg.id '
                'ORDER BY hg.fecha DESC').fetchall()
            visitas_count = conn.execute(
                'SELECT id_animal, COUNT(*) as total FROM historial_grooming GROUP BY id_animal'
            ).fetchall()
            conn.close()
            visitas_map = {r['id_animal']: r['total'] for r in visitas_count}
            for r in rows:
                if filter_text:
                    fl = filter_text.lower()
                    if fl not in r['dueno'].lower() and fl not in (r['dueno_dni'] or '').lower() and fl not in r['animal'].lower():
                        continue
                tree_h.insert('', 'end', values=(
                    r['fecha'], r['animal'], r['dueno'], r['dueno_dni'] or '',
                    r['servicio'] or 'N/A', f'S/.{r["precio"]:.2f}',
                    visitas_map.get(r['id_animal'], 1)))

        load_historial()
        e_buscar.bind('<KeyRelease>', lambda e: load_historial(e_buscar.get()))

        # Tab 3: Citas Grooming
        tab3 = tk.Frame(notebook, bg='#f0f4f8')
        notebook.add(tab3, text='Citas Grooming')

        cols_g = ('fecha', 'animal', 'dueno', 'motivo')
        tree_g = ttk.Treeview(tab3, columns=cols_g, show='headings', height=12)
        tree_g.heading('fecha', text='Fecha')
        tree_g.heading('animal', text='Animal')
        tree_g.heading('dueno', text='Dueño')
        tree_g.heading('motivo', text='Motivo')
        tree_g.column('fecha', width=100)
        tree_g.column('animal', width=180)
        tree_g.column('dueno', width=180)
        tree_g.column('motivo', width=250)
        tree_g.pack(fill='both', expand=True, pady=5)

        def load_citas_grooming():
            for item in tree_g.get_children():
                tree_g.delete(item)
            conn = self.get_db()
            rows = conn.execute(
                'SELECT c.fecha, a.nombre as animal, d.nombre as dueno, c.motivo '
                'FROM citas c JOIN animales a ON c.id_animal = a.id '
                'JOIN duenos d ON c.id_dueno = d.id '
                "WHERE c.tipo = 'grooming' AND c.estado = 'pendiente' ORDER BY c.fecha").fetchall()
            conn.close()
            for r in rows:
                tree_g.insert('', 'end', values=(r['fecha'], r['animal'], r['dueno'], r['motivo']))

        load_citas_grooming()

    def add_grooming_service_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title('Nuevo Servicio de Grooming')
        dialog.geometry('400x220')
        dialog.resizable(False, False)
        dialog.configure(bg='#e8edf2')
        dialog.transient(self.root)
        dialog.grab_set()
        center_dialog(dialog, self.root)

        tk.Label(dialog, text='Nombre', bg='#e8edf2', font=('Segoe UI', 10)).grid(row=0, column=0, sticky='e', padx=10, pady=6)
        e_nombre = tk.Entry(dialog, width=35, font=('Segoe UI', 10))
        e_nombre.grid(row=0, column=1, padx=10, pady=6)
        tk.Label(dialog, text='Descripcion', bg='#e8edf2', font=('Segoe UI', 10)).grid(row=1, column=0, sticky='e', padx=10, pady=6)
        e_desc = tk.Entry(dialog, width=35, font=('Segoe UI', 10))
        e_desc.grid(row=1, column=1, padx=10, pady=6)
        tk.Label(dialog, text='Precio', bg='#e8edf2', font=('Segoe UI', 10)).grid(row=2, column=0, sticky='e', padx=10, pady=6)
        e_precio = tk.Entry(dialog, width=35, font=('Segoe UI', 10))
        e_precio.grid(row=2, column=1, padx=10, pady=6)
        tk.Label(dialog, text='Tipo', bg='#e8edf2', font=('Segoe UI', 10)).grid(row=3, column=0, sticky='e', padx=10, pady=6)
        e_tipo = ttk.Combobox(dialog, values=['Baño', 'Corte', 'Combo', 'Higiene', 'Otros'], width=32, font=('Segoe UI', 10))
        e_tipo.set('Baño')
        e_tipo.grid(row=3, column=1, padx=10, pady=6)

        def save():
            conn = self.get_db()
            conn.execute(
                'INSERT INTO servicios_grooming (nombre, descripcion, precio, duracion_minutos, tipo) VALUES (?,?,?,?,?)',
                (e_nombre.get(), e_desc.get(), float(e_precio.get() or 0), 0, e_tipo.get()))
            conn.commit()
            conn.close()
            dialog.destroy()
            self.show_grooming()

        tk.Button(dialog, text='Guardar', bg='#2ecc71', fg='white',
                  font=('Segoe UI', 10), relief='flat', padx=20, pady=5,
                  command=save, cursor='hand2').grid(row=4, column=1, pady=15, sticky='e')

    def add_grooming_from_detail(self, animal_id, detail_frame, reload_callback):
        conn = self.get_db()
        servicios = conn.execute('SELECT * FROM servicios_grooming ORDER BY nombre').fetchall()
        animal = conn.execute('SELECT a.id, a.nombre, d.nombre as dueno, d.dni FROM animales a JOIN duenos d ON a.id_dueno=d.id WHERE a.id=?', (animal_id,)).fetchone()
        visitas = conn.execute('SELECT COUNT(*) FROM historial_grooming WHERE id_animal=?', (animal_id,)).fetchone()[0]
        conn.close()
        if not servicios:
            messagebox.showinfo('Info', 'No hay servicios de grooming. Cree uno primero.')
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(f'Registrar Grooming - {animal["nombre"]}')
        dialog.geometry('420x300')
        dialog.resizable(False, False)
        dialog.configure(bg='#e8edf2')
        dialog.transient(self.root)
        dialog.grab_set()
        center_dialog(dialog, self.root)

        info_f = tk.Frame(dialog, bg='#e8edf2')
        info_f.grid(row=0, column=0, columnspan=2, padx=10, pady=6, sticky='w')
        tk.Label(info_f, text=f'Dueño: {animal["dueno"]} | DNI: {animal["dni"] or "N/A"} | Visitas: {visitas}',
                 font=('Segoe UI', 9, 'bold'), bg='#e8edf2', fg='#9b59b6').pack()

        svc_map = {s['nombre']: s for s in servicios}
        svc_names = list(svc_map.keys()) + ['Otros']
        tk.Label(dialog, text='Servicio:', bg='#e8edf2', font=('Segoe UI', 10)).grid(row=1, column=0, sticky='e', padx=10, pady=6)
        e_servicio = ttk.Combobox(dialog, values=svc_names, width=35, font=('Segoe UI', 10))
        e_servicio.set(list(svc_map.keys())[0])
        e_servicio.grid(row=1, column=1, padx=10, pady=6)
        tk.Label(dialog, text='Precio:', bg='#e8edf2', font=('Segoe UI', 10)).grid(row=2, column=0, sticky='e', padx=10, pady=6)
        e_precio = tk.Entry(dialog, width=35, font=('Segoe UI', 10))
        e_precio.grid(row=2, column=1, padx=10, pady=6)
        tk.Label(dialog, text='Estilista:', bg='#e8edf2', font=('Segoe UI', 10)).grid(row=3, column=0, sticky='e', padx=10, pady=6)
        e_estilista = tk.Entry(dialog, width=35, font=('Segoe UI', 10))
        e_estilista.grid(row=3, column=1, padx=10, pady=6)
        tk.Label(dialog, text='Observaciones:', bg='#e8edf2', font=('Segoe UI', 10)).grid(row=4, column=0, sticky='e', padx=10, pady=6)
        e_obs = tk.Entry(dialog, width=35, font=('Segoe UI', 10))
        e_obs.grid(row=4, column=1, padx=10, pady=6)

        def on_servicio_select(*args):
            s = svc_map.get(e_servicio.get())
            if s:
                e_precio.delete(0, 'end')
                e_precio.insert(0, str(s['precio']))
            else:
                e_precio.delete(0, 'end')
        e_servicio.bind('<<ComboboxSelected>>', on_servicio_select)
        on_servicio_select()

        def save():
            conn = self.get_db()
            svc_name = e_servicio.get()
            s = svc_map.get(svc_name)
            svc_id = s['id'] if s else None
            conn.execute(
                'INSERT INTO historial_grooming (id_animal, id_servicio, fecha, observaciones, precio, estilista) VALUES (?,?,?,?,?,?)',
                (animal_id, svc_id, str(date.today()), e_obs.get(), float(e_precio.get() or 0), e_estilista.get()))
            conn.commit()
            conn.close()
            dialog.destroy()
            self.show_detail(detail_frame, animal_id, reload_callback)
            messagebox.showinfo('Exito', 'Grooming registrado')

        tk.Button(dialog, text='Guardar', bg='#2ecc71', fg='white',
                  font=('Segoe UI', 10), relief='flat', padx=20, pady=5,
                  command=save, cursor='hand2').grid(row=5, column=1, pady=15, sticky='e')

    def _seccion_historial_grooming(self, parent, animal_id):
        conn = self.get_db()
        rows = conn.execute(
            'SELECT hg.fecha, sg.nombre as servicio, hg.precio, hg.estilista, hg.observaciones '
            'FROM historial_grooming hg '
            'LEFT JOIN servicios_grooming sg ON hg.id_servicio = sg.id '
            'WHERE hg.id_animal=? ORDER BY hg.fecha DESC', (animal_id,)).fetchall()
        total_visitas = conn.execute(
            'SELECT COUNT(*) as total FROM historial_grooming WHERE id_animal=?', (animal_id,)).fetchone()[0]
        conn.close()
        sec, lbl = self._make_section(parent, 'Historial Grooming', '#9b59b6')
        lbl_visitas = tk.Label(sec, text=f'({total_visitas} visita(s))', font=('Segoe UI', 9),
                               bg='#e8edf2', fg='#9b59b6')
        lbl_visitas.pack(side='left', padx=(8, 0))
        if not rows:
            tk.Label(parent, text='  Sin historial de grooming', font=('Segoe UI', 9),
                     bg='#e8edf2', fg='#999', anchor='w').pack(fill='x')
            return
        f = self._make_table_frame(parent)
        cols = ('gf', 'gs', 'gp', 'ge', 'go')
        tree = ttk.Treeview(f, columns=cols, show='headings', height=4)
        tree.heading('gf', text='Fecha')
        tree.heading('gs', text='Servicio')
        tree.heading('gp', text='Precio')
        tree.heading('ge', text='Estilista')
        tree.heading('go', text='Observaciones')
        tree.column('gf', width=90)
        tree.column('gs', width=150)
        tree.column('gp', width=70)
        tree.column('ge', width=100)
        tree.column('go', width=180)
        tree.pack(fill='x')
        for r in rows:
            tree.insert("", "end", values=(r["fecha"], r["servicio"] or "N/A",
                        f"S/.{r['precio']:.2f}", r["estilista"] or "", r["observaciones"] or ""))

    # ---------- PRODUCTOS ----------
    def show_productos(self):
        self.clear_frame()
        main = tk.Frame(self.root, bg='#f0f4f8')
        main.pack(fill='both', expand=True, padx=20, pady=15)

        top = tk.Frame(main, bg='#f0f4f8')
        top.pack(fill='x')
        tk.Label(top, text='Productos / Inventario', font=('Segoe UI', 16, 'bold'),
                 bg='#f0f4f8', fg='#2c3e50').pack(side='left')
        tk.Button(top, text='+ Nuevo Producto', bg='#2ecc71', fg='white',
                  font=('Segoe UI', 9), relief='flat', padx=10, pady=3,
                  command=lambda: self.add_producto_dialog(self.show_productos), cursor='hand2').pack(side='right')

        cols = ('id', 'nombre', 'desc', 'precio_compra', 'precio_venta', 'stock', 'categoria')
        tree = ttk.Treeview(main, columns=cols, show='headings', height=18)
        tree.heading('id', text='ID')
        tree.heading('nombre', text='Nombre')
        tree.heading('desc', text='Descripcion')
        tree.heading('precio_compra', text='Costo')
        tree.heading('precio_venta', text='Venta')
        tree.heading('stock', text='Stock')
        tree.heading('categoria', text='Categoria')
        tree.column('id', width=40)
        tree.column('nombre', width=200)
        tree.column('desc', width=250)
        tree.column('precio_compra', width=70)
        tree.column('precio_venta', width=70)
        tree.column('stock', width=60)
        tree.column('categoria', width=100)
        tree.pack(fill='both', expand=True, pady=10)

        def load_productos():
            for item in tree.get_children():
                tree.delete(item)
            conn = self.get_db()
            rows = conn.execute('SELECT * FROM productos WHERE activo=1 ORDER BY nombre').fetchall()
            conn.close()
            for r in rows:
                item = tree.insert('', 'end', values=(
                    r['id'], r['nombre'], r['descripcion'],
                    f'S/.{r["precio_compra"]:.2f}', f'S/.{r["precio_venta"]:.2f}',
                    r['stock'], r['categoria']))
                stock = r['stock']
                if stock <= 2:
                    tree.tag_configure('critical', background='#fadbd8')
                    tree.item(item, tags=('critical',))
                elif stock <= 5:
                    tree.tag_configure('low', background='#fef9e7')
                    tree.item(item, tags=('low',))

        load_productos()

        btn_frame = tk.Frame(main, bg='#f0f4f8')
        btn_frame.pack(fill='x')
        tk.Button(btn_frame, text='Editar', bg='#f39c12', fg='white',
                  font=('Segoe UI', 9), relief='flat', padx=10, pady=2,
                  command=lambda: self.add_producto_dialog(self.show_productos, tree), cursor='hand2').pack(side='left', padx=2)
        tk.Button(btn_frame, text='Eliminar', bg='#e74c3c', fg='white',
                  font=('Segoe UI', 9), relief='flat', padx=10, pady=2,
                  command=lambda: self._delete_producto(tree, load_productos), cursor='hand2').pack(side='left', padx=2)

    def _delete_producto(self, tree, reload_cb):
        sel = tree.selection()
        if not sel: return
        vals = tree.item(sel[0], 'values')
        if messagebox.askyesno('Confirmar', 'Desactivar producto?'):
            conn = self.get_db()
            conn.execute('UPDATE productos SET activo=0 WHERE id=?', (int(vals[0]),))
            conn.commit()
            conn.close()
            reload_cb()

    def add_producto_dialog(self, callback=None, tree=None):
        edit_id = None
        if tree:
            sel = tree.selection()
            if sel:
                vals = tree.item(sel[0], 'values')
                edit_id = int(vals[0])

        dialog = tk.Toplevel(self.root)
        title = 'Editar Producto' if edit_id else 'Nuevo Producto'
        dialog.title(title)
        dialog.geometry('400x300')
        dialog.resizable(False, False)
        dialog.configure(bg='#e8edf2')
        dialog.transient(self.root)
        dialog.grab_set()
        center_dialog(dialog, self.root)

        data = {}
        if edit_id:
            conn = self.get_db()
            d = conn.execute('SELECT * FROM productos WHERE id=?', (edit_id,)).fetchone()
            conn.close()
            if d:
                for k in d.keys(): data[k] = d[k]

        fields = [('Nombre', 'nombre'), ('Descripcion', 'descripcion'),
                   ('Precio Compra', 'precio_compra'), ('Precio Venta', 'precio_venta'),
                   ('Stock', 'stock'), ('Categoria', 'categoria')]
        entries = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(dialog, text=label, bg='#e8edf2', font=('Segoe UI', 10)).grid(
                row=i, column=0, sticky='e', padx=10, pady=5)
            e = tk.Entry(dialog, width=35, font=('Segoe UI', 10))
            if key in data:
                e.insert(0, str(data[key]) if data[key] is not None else '')
            e.grid(row=i, column=1, padx=10, pady=5)
            entries[key] = e

        def save():
            conn = self.get_db()
            if edit_id:
                conn.execute(
                    'UPDATE productos SET nombre=?, descripcion=?, precio_compra=?, precio_venta=?, stock=?, categoria=? WHERE id=?',
                    (entries['nombre'].get(), entries['descripcion'].get(),
                     float(entries['precio_compra'].get() or 0), float(entries['precio_venta'].get() or 0),
                     int(entries['stock'].get() or 0), entries['categoria'].get(), edit_id))
            else:
                conn.execute(
                    'INSERT INTO productos (nombre, descripcion, precio_compra, precio_venta, stock, categoria) VALUES (?,?,?,?,?,?)',
                    (entries['nombre'].get(), entries['descripcion'].get(),
                     float(entries['precio_compra'].get() or 0), float(entries['precio_venta'].get() or 0),
                     int(entries['stock'].get() or 0), entries['categoria'].get()))
            conn.commit()
            conn.close()
            dialog.destroy()
            if callback: callback()

        tk.Button(dialog, text='Guardar', bg='#2ecc71', fg='white',
                  font=('Segoe UI', 10), relief='flat', padx=20, pady=5,
                  command=save, cursor='hand2').grid(row=len(fields), column=1, pady=15, sticky='e')

    def aperturar_caja_dialog(self, callback=None):
        if self._caja_abierta:
            messagebox.showinfo("Info", f"Caja ya esta abierta (Saldo inicial: S/.{self._saldo_inicial:.2f})")
            if callback: callback()
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Aperturar Caja")
        dialog.geometry("350x150")
        dialog.resizable(False, False)
        dialog.configure(bg="#e8edf2")
        dialog.transient(self.root)
        dialog.grab_set()
        from . import center_dialog
        try:
            from veterinaria_gui import center_dialog
        except:
            pass
        # Use inline centering instead
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry("+%d+%d" % (x, y))

        tk.Label(dialog, text="Aperturar Caja del Dia", font=("Segoe UI", 12, "bold"),
                 bg="#e8edf2", fg="#2c3e50").pack(pady=(10, 5))
        tk.Label(dialog, text="Monto inicial (S/):", bg="#e8edf2", font=("Segoe UI", 10)).pack()
        e_monto = tk.Entry(dialog, width=25, font=("Segoe UI", 12), justify="center")
        e_monto.pack(pady=5)
        e_monto.insert(0, "0.00")
        e_monto.focus_set()

        def abrir():
            try:
                monto = float(e_monto.get())
            except:
                messagebox.showerror("Error", "Ingrese un monto valido")
                return
            self._caja_abierta = True
            self._saldo_inicial = monto
            conn = self.get_db()
            conn.execute("INSERT INTO caja (fecha, tipo, concepto, monto) VALUES (?, 'apertura', 'Apertura de caja', ?)",
                         (str(date.today()), monto))
            conn.commit()
            conn.close()
            dialog.destroy()
            messagebox.showinfo("Exito", f"Caja aperturada con S/.{monto:.2f}")
            if callback: callback()

        tk.Button(dialog, text="Abrir Caja", bg="#2ecc71", fg="white",
                  font=("Segoe UI", 10), relief="flat", padx=20, pady=5,
                  command=abrir, cursor="hand2").pack(pady=10)

    def show_ventas(self):
        self.clear_frame()
        main = tk.Frame(self.root, bg='#f0f4f8')
        main.pack(fill='both', expand=True, padx=20, pady=15)

        top_bar = tk.Frame(main, bg='#f0f4f8')
        top_bar.pack(fill='x')
        tk.Label(top_bar, text='Ventas / Caja', font=('Segoe UI', 16, 'bold'),
                 bg='#f0f4f8', fg='#2c3e50').pack(side='left')

        # Caja status
        if self._caja_abierta:
            tk.Label(top_bar, text=f'  Caja: S/.{self._saldo_inicial:.2f} (Abierta)',
                     font=('Segoe UI', 11, 'bold'), bg='#f0f4f8', fg='#2ecc71').pack(side='left', padx=10)
        else:
            tk.Button(top_bar, text='🔓 Aperturar Caja', bg='#e67e22', fg='white',
                      font=('Segoe UI', 9), relief='flat', padx=10, pady=3,
                      command=lambda: self.aperturar_caja_dialog(self.show_ventas),
                      cursor='hand2').pack(side='left', padx=10)

        panes = tk.Frame(main, bg='#f0f4f8')
        panes.pack(fill='both', expand=True, pady=(10, 0))

        # LEFT: POS / Cart
        left = tk.Frame(panes, bg='white', highlightbackground='#ddd', highlightthickness=1)
        left.pack(side='left', fill='both', expand=True, padx=(0, 8))

        tk.Label(left, text='Punto de Venta', font=('Segoe UI', 12, 'bold'),
                 bg='white', fg='#2c3e50', padx=10, pady=8).pack(anchor='w')

        # Client selection by DNI/RUC
        client_frame = tk.Frame(left, bg='white', padx=10, pady=3)
        client_frame.pack(fill='x')
        tk.Label(client_frame, text='DNI / RUC:', bg='white', font=('Segoe UI', 10)).pack(side='left')
        e_dni = tk.Entry(client_frame, width=20, font=('Segoe UI', 10))
        e_dni.pack(side='left', padx=3)
        tk.Label(client_frame, text='Cliente:', bg='white', font=('Segoe UI', 10)).pack(side='left', padx=(10, 3))
        e_cliente = tk.Entry(client_frame, width=25, font=('Segoe UI', 10), state='readonly')
        e_cliente.pack(side='left')
        self._venta_cliente_id = None
        self._venta_cliente_nombre = ''

        def buscar_cliente(*args):
            dni = e_dni.get().strip()
            if not dni:
                return
            conn = self.get_db()
            row = conn.execute("SELECT id, nombre, telefono, direccion FROM duenos WHERE dni=?", (dni,)).fetchone()
            conn.close()
            if row:
                e_cliente.config(state='normal')
                e_cliente.delete(0, 'end')
                e_cliente.insert(0, row['nombre'])
                e_cliente.config(state='readonly')
                self._venta_cliente_id = row['id']
                self._venta_cliente_nombre = row['nombre']
            else:
                if messagebox.askyesno("Cliente no encontrado", f"DNI {dni} no registrado. Desea registrarlo?"):
                    self.add_owner_dialog()
                    # Try again
                    conn = self.get_db()
                    row = conn.execute("SELECT id, nombre FROM duenos WHERE dni=?", (dni,)).fetchone()
                    conn.close()
                    if row:
                        e_cliente.config(state='normal')
                        e_cliente.delete(0, 'end')
                        e_cliente.insert(0, row['nombre'])
                        e_cliente.config(state='readonly')
                        self._venta_cliente_id = row['id']
                        self._venta_cliente_nombre = row['nombre']

        e_dni.bind('<FocusOut>', buscar_cliente)
        e_dni.bind('<Return>', buscar_cliente)

        # Product combo + qty
        item_frame = tk.Frame(left, bg='white', padx=10, pady=3)
        item_frame.pack(fill='x')

        def get_product_list():
            conn = self.get_db()
            rows = conn.execute('SELECT id, nombre, precio_venta, stock FROM productos WHERE activo=1 AND stock>0 ORDER BY nombre').fetchall()
            conn.close()
            return {f"{r['nombre']} - S/.{r['precio_venta']:.2f}": {"id": r["id"], "precio": r["precio_venta"], "nombre": r["nombre"]} for r in rows}

        tk.Label(item_frame, text='Producto:', bg='white', font=('Segoe UI', 10)).pack(side='left')
        prod_map = get_product_list()
        e_producto = ttk.Combobox(item_frame, values=list(prod_map.keys()), width=35, font=('Segoe UI', 10))
        e_producto.pack(side='left', padx=3)

        tk.Label(item_frame, text='Cant:', bg='white', font=('Segoe UI', 10)).pack(side='left', padx=(3, 2))
        e_cant = tk.Spinbox(item_frame, from_=1, to=99, width=5, font=('Segoe UI', 10))
        e_cant.pack(side='left')

        def add_product_to_cart():
            prod_key = e_producto.get()
            if not prod_key or prod_key not in prod_map:
                messagebox.showwarning('Error', 'Seleccione un producto')
                return
            p = prod_map[prod_key]
            try:
                qty = int(e_cant.get())
            except:
                qty = 1
            self._add_to_cart('producto', p['id'], p['nombre'], qty, p['precio'])
            update_cart_display()

        tk.Button(item_frame, text='Agregar', bg='#3498db', fg='white',
                  font=('Segoe UI', 9), relief='flat', padx=8, pady=2,
                  command=add_product_to_cart, cursor='hand2').pack(side='left', padx=(3, 0))

        # Grooming service in cart
        grooming_frame = tk.Frame(left, bg='white', padx=10, pady=3)
        grooming_frame.pack(fill='x')

        def get_grooming_list():
            conn = self.get_db()
            rows = conn.execute('SELECT id, nombre, precio FROM servicios_grooming ORDER BY nombre').fetchall()
            conn.close()
            return {f"{r['nombre']} - S/.{r['precio']:.2f}": {"id": r["id"], "precio": r["precio"], "nombre": r["nombre"]} for r in rows}

        tk.Label(grooming_frame, text='Grooming:', bg='white', font=('Segoe UI', 10)).pack(side='left')
        grooming_map = get_grooming_list()
        e_grooming = ttk.Combobox(grooming_frame, values=list(grooming_map.keys()), width=35, font=('Segoe UI', 10))
        e_grooming.pack(side='left', padx=3)

        def add_grooming_to_cart():
            g_key = e_grooming.get()
            if not g_key or g_key not in grooming_map:
                messagebox.showwarning('Error', 'Seleccione un servicio')
                return
            g = grooming_map[g_key]
            self._add_to_cart('grooming', g['id'], g['nombre'], 1, g['precio'])
            update_cart_display()

        tk.Button(grooming_frame, text='Agregar', bg='#9b59b6', fg='white',
                  font=('Segoe UI', 9), relief='flat', padx=8, pady=2,
                  command=add_grooming_to_cart, cursor='hand2').pack(side='left', padx=(3, 0))

        # Cart display
        cart_frame = tk.Frame(left, bg='white', padx=10, pady=3)
        cart_frame.pack(fill='both', expand=True)
        tk.Label(cart_frame, text='Carrito:', font=('Segoe UI', 11, 'bold'),
                 bg='white', fg='#2c3e50').pack(anchor='w')

        cart_cols = ('item', 'qty', 'price', 'subtotal')
        cart_tree = ttk.Treeview(cart_frame, columns=cart_cols, show='headings', height=6)
        cart_tree.heading('item', text='Item')
        cart_tree.heading('qty', text='Cant')
        cart_tree.heading('price', text='P.Unit')
        cart_tree.heading('subtotal', text='Subtotal')
        cart_tree.column('item', width=300)
        cart_tree.column('qty', width=50)
        cart_tree.column('price', width=80)
        cart_tree.column('subtotal', width=80)
        cart_tree.pack(fill='both', expand=True)

        total_var = tk.StringVar(value='Total: S/.0.00')
        tk.Label(cart_frame, textvariable=total_var, font=('Segoe UI', 14, 'bold'),
                 bg='white', fg='#e74c3c').pack(anchor='e', pady=(3, 0))

        def remove_from_cart():
            sel = cart_tree.selection()
            if not sel: return
            for item in sel:
                cart_tree.delete(item)
            update_cart_display()

        btn_cart = tk.Frame(cart_frame, bg='white')
        btn_cart.pack(fill='x', pady=(3, 0))
        tk.Button(btn_cart, text='Quitar', bg='#e74c3c', fg='white',
                  font=('Segoe UI', 9), relief='flat', padx=10, pady=2,
                  command=remove_from_cart, cursor='hand2').pack(side='left', padx=2)
        tk.Button(btn_cart, text='Limpiar', bg='#95a5a6', fg='white',
                  font=('Segoe UI', 9), relief='flat', padx=10, pady=2,
                  command=lambda: ([cart_tree.delete(i) for i in cart_tree.get_children()], update_cart_display()), cursor='hand2').pack(side='left', padx=2)
        tk.Button(btn_cart, text='Cobrar', bg='#2ecc71', fg='white',
                  font=('Segoe UI', 12, 'bold'), relief='flat', padx=30, pady=5,
                  command=self._checkout, cursor='hand2').pack(side='right', padx=2)

        # RIGHT: Today sales / history
        right = tk.Frame(panes, bg='white', highlightbackground='#ddd', highlightthickness=1)
        right.pack(side='left', fill='both', expand=True)

        tk.Label(right, text='Ventas de Hoy', font=('Segoe UI', 12, 'bold'),
                 bg='white', fg='#2c3e50', padx=10, pady=8).pack(anchor='w')

        # Cash summary
        cash_summary = tk.Frame(right, bg='white', padx=10)
        cash_summary.pack(fill='x')
        daily_total_var = tk.StringVar(value='Total Hoy: S/.0.00')
        tk.Label(cash_summary, textvariable=daily_total_var, font=('Segoe UI', 12, 'bold'),
                 bg='white', fg='#1abc9c').pack(side='left')

        venta_cols = ('id', 'fecha', 'cliente', 'total', 'tipo')
        venta_tree = ttk.Treeview(right, columns=venta_cols, show='headings', height=15)
        venta_tree.heading('id', text='ID')
        venta_tree.heading('fecha', text='Fecha')
        venta_tree.heading('cliente', text='Cliente')
        venta_tree.heading('total', text='Total')
        venta_tree.heading('tipo', text='Tipo')
        venta_tree.column('id', width=40)
        venta_tree.column('fecha', width=90)
        venta_tree.column('cliente', width=180)
        venta_tree.column('total', width=80)
        venta_tree.column('tipo', width=80)
        venta_tree.pack(fill='both', expand=True, padx=10, pady=5)

        def load_daily_sales():
            for item in venta_tree.get_children():
                venta_tree.delete(item)
            conn = self.get_db()
            rows = conn.execute(
                'SELECT v.id, v.fecha, v.total, v.tipo, COALESCE(d.nombre, "-") as cliente '
                'FROM ventas v LEFT JOIN duenos d ON v.id_cliente = d.id '
                'WHERE v.fecha = ? ORDER BY v.id DESC', (str(date.today()),)).fetchall()
            daily_total = conn.execute(
                'SELECT COALESCE(SUM(total), 0) FROM ventas WHERE fecha = ?',
                (str(date.today()),)).fetchone()[0]
            conn.close()
            for r in rows:
                venta_tree.insert("", "end", values=(r["id"], r["fecha"], r["cliente"],
                    f"S/.{r['total']:.2f}", r["tipo"]))
            daily_total_var.set(f"Total Hoy: S/.{daily_total:.2f}")

        load_daily_sales()

        def update_cart_display():
            total = 0.0
            for item in cart_tree.get_children():
                vals = cart_tree.item(item, 'values')
                try:
                    subtotal_str = vals[3].replace('S/.', '')
                    total += float(subtotal_str)
                except:
                    pass
            total_var.set(f"Total: S/.{total:.2f}")

        self._cart_items = []
        self._cart_tree = cart_tree
        self._cart_total_var = total_var
        self._cart_update = update_cart_display
        self._load_daily_sales = load_daily_sales
        self._daily_total_var = daily_total_var

    def _add_to_cart(self, item_type, ref_id, name, qty, price):
        # Check stock for products
        if item_type == 'producto':
            conn = self.get_db()
            stock = conn.execute('SELECT stock FROM productos WHERE id=?', (ref_id,)).fetchone()
            conn.close()
            if stock and stock[0] < qty:
                messagebox.showerror('Stock insuficiente', f'Stock disponible: {stock[0]}')
                return
        # Check if already in cart and update qty
        for item in self._cart_tree.get_children():
            vals = self._cart_tree.item(item, 'values')
            if vals[0] == name:
                new_qty = int(vals[1]) + qty
                subtotal = new_qty * price
                self._cart_tree.item(item, values=(name, str(new_qty), f'S/.{price:.2f}', f'S/.{subtotal:.2f}'))
                return
        subtotal = qty * price
        self._cart_tree.insert('', 'end', values=(name, str(qty), f'S/.{price:.2f}', f'S/.{subtotal:.2f}'))

    def _checkout(self):
        if not self._caja_abierta:
            messagebox.showwarning("Caja Cerrada", "Debe aperturar la caja primero")
            return
        cart_items = []
        total = 0.0
        for item in self._cart_tree.get_children():
            vals = self._cart_tree.item(item, 'values')
            cart_items.append(vals)
            try:
                subtotal_str = vals[3].replace('S/.', '')
                total += float(subtotal_str)
            except:
                pass
        if not cart_items:
            messagebox.showwarning('Carrito vacio', 'Agregue items al carrito')
            return
        if not self._venta_cliente_id:
            if not messagebox.askyesno('Sin cliente', 'No ha seleccionado cliente. Continuar como venta directa?'):
                return
        if messagebox.askyesno('Confirmar', f'Confirmar venta por S/.{total:.2f}?'):
            conn = self.get_db()
            cursor = conn.execute(
                'INSERT INTO ventas (id_cliente, fecha, total, tipo) VALUES (?,?,?,?)',
                (self._venta_cliente_id or None, str(date.today()), total, 'mixto'))
            venta_id = cursor.lastrowid
            for vals in cart_items:
                conn.execute(
                    'INSERT INTO venta_items (id_venta, tipo_item, nombre, cantidad, precio_unitario, subtotal) VALUES (?,?,?,?,?,?)',
                    (venta_id, 'producto', vals[0], int(vals[1]),
                     float(vals[2].replace('S/.', '')), float(vals[3].replace('S/.', ''))))
            # Actually update stock for products
            for item in self._cart_tree.get_children():
                vals = self._cart_tree.item(item, 'values')
                item_name = vals[0]
                item_qty = int(vals[1])
                # Try to find product by name and update stock
                conn.execute('UPDATE productos SET stock = stock - ? WHERE nombre = ? AND activo=1',
                            (item_qty, item_name))
            # Add to caja
            conn.execute("INSERT INTO caja (fecha, tipo, concepto, monto, referencia_tipo, referencia_id) VALUES (?, 'ingreso', ?, ?, 'venta', ?)",
                        (str(date.today()), f'Venta #{venta_id}', total, venta_id))
            conn.commit()
            conn.close()
            # Clear cart
            for i in self._cart_tree.get_children():
                self._cart_tree.delete(i)
            self._cart_update()
            self._load_daily_sales()
            messagebox.showinfo('Exito', f'Venta registrada. Total: S/.{total:.2f}')

    def _get_all_products(self):
        conn = self.get_db()
        rows = conn.execute('SELECT nombre FROM productos WHERE activo=1').fetchall()
        conn.close()
        return [dict(r) for r in rows]

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
