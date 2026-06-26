# Reads the rest of original file, modifies it, and appends to v2
import os

filepath = r"C:\SCRIPTYFY.V02UNSUEÑO\veterinaria_gui_v2.py"
src_path = r"C:\SCRIPTYFY.V02UNSUEÑO\temp_rest.py"

with open(src_path, "r", encoding="utf-8") as f:
    content = f.read()

# ===== MODIFICATIONS TO EXISTING CODE =====

# 1. Fix show_medical_history - add DNI to query (already has it)
# No changes needed for search - it already matches DNI

# 2. In show_detail - add sexo, color, esterilizado to detail line
content = content.replace(
    "det = (\"Raza: \" + (animal[\"raza\"] or \"N/A\") +\n               \"  |  Edad: \" + str(animal[\"edad\"]) + \" anios\" +\n               \"  |  Peso: \" + str(animal[\"peso\"]) + \" kg\")",
    "det = (\"Raza: \" + (animal[\"raza\"] or \"N/A\") +\n               \"  |  Edad: \" + str(animal[\"edad\"]) + \" anios\" +\n               \"  |  Peso: \" + str(animal[\"peso\"]) + \" kg\" +\n               \"  |  Sexo: \" + (animal[\"sexo\"] or \"N/A\") +\n               \"  |  Color: \" + (animal[\"color\"] or \"N/A\") +\n               \"  |  Esterilizado: \" + (\"Si\" if animal[\"esterilizado\"] else \"No\"))"
)

# 3. Show detail - add Grooming button after Editar button
content = content.replace(
    "tk.Button(action_frame, text=\"Eliminar\", bg=\"#e74c3c\", fg=\"white\",\n                  font=(\"Segoe UI\", 9), relief=\"flat\", padx=0, pady=3, width=8,\n                  command=delete_animal, cursor=\"hand2\").pack(side=\"top\", pady=2)",
    "tk.Button(action_frame, text=\"Grooming\", bg=\"#9b59b6\", fg=\"white\",\n                  font=(\"Segoe UI\", 9), relief=\"flat\", padx=0, pady=3, width=8,\n                  command=lambda: self.add_grooming_from_detail(animal_id, detail_frame, reload_callback),\n                  cursor=\"hand2\").pack(side=\"top\", pady=2)\n        tk.Button(action_frame, text=\"Eliminar\", bg=\"#e74c3c\", fg=\"white\",\n                  font=(\"Segoe UI\", 9), relief=\"flat\", padx=0, pady=3, width=8,\n                  command=delete_animal, cursor=\"hand2\").pack(side=\"top\", pady=2)"
)

# 4. Add DELETE from historial_grooming in delete_animal
content = content.replace(
    "c.execute(\"DELETE FROM citas WHERE id_animal=?\", (animal_id,))",
    "c.execute(\"DELETE FROM citas WHERE id_animal=?\", (animal_id,))\n                c.execute(\"DELETE FROM historial_grooming WHERE id_animal=?\", (animal_id,))"
)

# 5. Show detail - add _seccion_historial_grooming after examenes
content = content.replace(
    "# --- GRAFICO PESO ---\n        self._grafico_peso(hist_frame, historial)",
    "# --- GROOMING HISTORY ---\n        self._seccion_historial_grooming(hist_frame, animal_id)\n\n        # --- GRAFICO PESO ---\n        self._grafico_peso(hist_frame, historial)"
)

# 6. Citas section in show_detail - add tipo column
content = content.replace(
    "cols_c = (\"fecha_c\", \"motivo_c\", \"estado_c\")",
    "cols_c = (\"fecha_c\", \"motivo_c\", \"tipo_c\", \"estado_c\")"
)
content = content.replace(
    "c_tree.heading(\"estado_c\", text=\"Estado\")",
    "c_tree.heading(\"tipo_c\", text=\"Tipo\")\n            c_tree.heading(\"estado_c\", text=\"Estado\")"
)
content = content.replace(
    "c_tree.column(\"estado_c\", width=80)\n            c_tree.pack(fill=\"x\")",
    "c_tree.column(\"tipo_c\", width=80)\n            c_tree.column(\"estado_c\", width=80)\n            c_tree.pack(fill=\"x\")"
)
content = content.replace(
    "c_tree.insert(\"\", \"end\", values=(r[\"fecha\"], r[\"motivo\"], r[\"estado\"] or \"pendiente\"))",
    "c_tree.insert(\"\", \"end\", values=(r[\"fecha\"], r[\"motivo\"], r[\"tipo\"] or \"veterinaria\", r[\"estado\"] or \"pendiente\"))"
)

# 7. Citas query in show_detail - add tipo
content = content.replace(
    "\"SELECT id, fecha, motivo, estado FROM citas WHERE id_animal=? ORDER BY fecha DESC\"",
    "\"SELECT id, fecha, motivo, estado, tipo FROM citas WHERE id_animal=? ORDER BY fecha DESC\""
)

# 8. add_owner_dialog - add DNI field first
content = content.replace(
    "fields = [(\"Nombre\", \"nombre\"), (\"Telefono\", \"telefono\"),\n                  (\"Email\", \"email\"), (\"Direccion\", \"direccion\")]",
    "fields = [(\"DNI\", \"dni\"), (\"Nombre\", \"nombre\"), (\"Telefono\", \"telefono\"),\n                  (\"Email\", \"email\"), (\"Direccion\", \"direccion\")]"
)
content = content.replace(
    "\"INSERT INTO duenos (nombre, telefono, email, direccion) VALUES (?, ?, ?, ?)\",\n                (entries[\"nombre\"].get(), entries[\"telefono\"].get(),\n                 entries[\"email\"].get(), entries[\"direccion\"].get()))",
    "\"INSERT INTO duenos (dni, nombre, telefono, email, direccion) VALUES (?, ?, ?, ?, ?)\",\n                (entries[\"dni\"].get(), entries[\"nombre\"].get(), entries[\"telefono\"].get(),\n                 entries[\"email\"].get(), entries[\"direccion\"].get()))"
)
content = content.replace(
    "tk.Button(dialog, text=\"Guardar\", bg=\"#2ecc71\", fg=\"white\",\n                  font=(\"Segoe UI\", 10), relief=\"flat\", padx=20, pady=5,\n                  command=save, cursor=\"hand2\").grid(row=4, column=1, pady=15, sticky=\"e\")",
    "tk.Button(dialog, text=\"Guardar\", bg=\"#2ecc71\", fg=\"white\",\n                  font=(\"Segoe UI\", 10), relief=\"flat\", padx=20, pady=5,\n                  command=save, cursor=\"hand2\").grid(row=5, column=1, pady=15, sticky=\"e\")"
)

# 9. add_animal_dialog - increase dialog height, add sexo/color/esterilizado, update INSERT
content = content.replace(
    "dialog.geometry(\"500x400\")",
    "dialog.geometry(\"500x450\")"
)
content = content.replace(
    "e_peso.grid(row=4, column=1, padx=10, pady=6)\n\n        tk.Label(dialog, text=\"Dueño\", bg=\"#f0f4f8\", font=(\"Segoe UI\", 10)).grid(\n            row=5, column=0, sticky=\"e\", padx=10, pady=6)",
    "e_peso.grid(row=4, column=1, padx=10, pady=6)\n\n        tk.Label(dialog, text=\"Sexo\", bg=\"#f0f4f8\", font=(\"Segoe UI\", 10)).grid(\n            row=5, column=0, sticky=\"e\", padx=10, pady=6)\n        e_sexo = ttk.Combobox(dialog, values=[\"Macho\", \"Hembra\"], width=37, font=(\"Segoe UI\", 10))\n        e_sexo.grid(row=5, column=1, padx=10, pady=6)\n\n        tk.Label(dialog, text=\"Color\", bg=\"#f0f4f8\", font=(\"Segoe UI\", 10)).grid(\n            row=6, column=0, sticky=\"e\", padx=10, pady=6)\n        e_color = tk.Entry(dialog, width=40, font=(\"Segoe UI\", 10))\n        e_color.grid(row=6, column=1, padx=10, pady=6)\n\n        tk.Label(dialog, text=\"Esterilizado\", bg=\"#f0f4f8\", font=(\"Segoe UI\", 10)).grid(\n            row=7, column=0, sticky=\"e\", padx=10, pady=6)\n        e_esterilizado = ttk.Combobox(dialog, values=[\"No\", \"Si\"], width=37, font=(\"Segoe UI\", 10))\n        e_esterilizado.set(\"No\")\n        e_esterilizado.grid(row=7, column=1, padx=10, pady=6)\n\n        tk.Label(dialog, text=\"Dueño\", bg=\"#f0f4f8\", font=(\"Segoe UI\", 10)).grid(\n            row=8, column=0, sticky=\"e\", padx=10, pady=6)"
)
# Fix dueno_frame row
content = content.replace(
    "dueno_frame.grid(row=5, column=1, padx=10, pady=6, sticky=\"w\")",
    "dueno_frame.grid(row=8, column=1, padx=10, pady=6, sticky=\"w\")"
)
# Fix photo button row
content = content.replace(
    "\"Seleccionar Foto\", bg=\"#3498db\", fg=\"white\",\n                  relief=\"flat\", command=choose_photo, cursor=\"hand2\").grid(\n            row=6, column=0, padx=10, pady=6)",
    "\"Seleccionar Foto\", bg=\"#3498db\", fg=\"white\",\n                  relief=\"flat\", command=choose_photo, cursor=\"hand2\").grid(\n            row=9, column=0, padx=10, pady=6)"
)
content = content.replace(
    "photo_label.grid(row=6, column=1, padx=10, pady=6, sticky=\"w\")",
    "photo_label.grid(row=9, column=1, padx=10, pady=6, sticky=\"w\")"
)
content = content.replace(
    "tk.Button(dialog, text=\"Guardar\", bg=\"#2ecc71\", fg=\"white\",\n                  font=(\"Segoe UI\", 10), relief=\"flat\", padx=20, pady=5,\n                  command=save, cursor=\"hand2\").grid(row=7, column=1, pady=10, sticky=\"e\")",
    "tk.Button(dialog, text=\"Guardar\", bg=\"#2ecc71\", fg=\"white\",\n                  font=(\"Segoe UI\", 10), relief=\"flat\", padx=20, pady=5,\n                  command=save, cursor=\"hand2\").grid(row=10, column=1, pady=10, sticky=\"e\")"
)

# Update INSERT in add_animal_dialog save
old_insert = "\"INSERT INTO animales (nombre, especie, raza, edad, peso, id_dueno, foto) \"\n                    \"VALUES (?, ?, ?, ?, ?, ?, ?)\",\n                    (e_nombre.get(), e_especie.get(), e_raza.get(),\n                     int(e_edad.get()), float(e_peso.get()),\n                     dueno_map[e_dueno.get()], \"\"))"
new_insert = "\"INSERT INTO animales (nombre, especie, raza, edad, peso, sexo, color, fecha_nacimiento, esterilizado, id_dueno, foto) \"\n                    \"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\",\n                    (e_nombre.get(), e_especie.get(), e_raza.get(),\n                     int(e_edad.get()), float(e_peso.get()),\n                     e_sexo.get(), e_color.get(), fecnac,\n                     1 if e_esterilizado.get() == \"Si\" else 0,\n                     dueno_map[e_dueno.get()], \"\"))"

# Need to be more careful - let me find the exact pattern
import re

# Find the INSERT pattern
pattern = r'(\s+)(cur = conn\.execute\(\n\s+"INSERT INTO animales \(nombre, especie, raza, edad, peso, id_dueno, foto\) ".*?\n\s+dueno_map\[e_dueno\.get\(\)\], ""\)\))'
match = re.search(pattern, content, re.DOTALL)
if match:
    indent = "                    "
    # Extract the fecnac variable - need to add it before the insert
    # The fecnac is probably calculated before the conn.execute call
    old_ins = match.group(2)
    
    new_ins = 'cur = conn.execute(\n' + indent + '"INSERT INTO animales (nombre, especie, raza, edad, peso, sexo, color, fecha_nacimiento, esterilizado, id_dueno, foto) "\n' + indent + '"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",\n' + indent + '(e_nombre.get(), e_especie.get(), e_raza.get(),\n' + indent + ' int(e_edad.get()), float(e_peso.get()),\n' + indent + ' e_sexo.get(), e_color.get(), fecnac,\n' + indent + ' 1 if e_esterilizado.get() == "Si" else 0,\n' + indent + ' dueno_map[e_dueno.get()], ""))'
    content = content.replace(old_ins, new_ins)
    
    # Add fecnac variable before the conn.execute
    fecnac_block = '                fecnac = ""\n                try:\n                    fecnac = e_fecnac.get()\n                except:\n                    pass'
    content = content.replace('                conn = self.get_db()\n                cur = conn.execute(', '                conn = self.get_db()\n' + fecnac_block + '\n                cur = conn.execute(')

# 10. edit_animal_dialog - increase dialog height
content = content.replace(
    'dialog.geometry("500x400")',
    'dialog.geometry("500x450")'
)

# 11. add_owner_mini in add_animal_dialog - add email
content = content.replace(
    'd2.geometry("400x220")',
    'd2.geometry("400x250")'
)
content = content.replace(
    'e_dir.grid(row=3, column=1, padx=5, pady=5)\n            def save_mini():',
    'e_dir.grid(row=3, column=1, padx=5, pady=5)\n            tk.Label(d2, text="Email:", bg="#f0f4f8", font=("Segoe UI", 10)).grid(row=4, column=0, sticky="e", padx=5, pady=5)\n            e_email = tk.Entry(d2, width=30, font=("Segoe UI", 10))\n            e_email.grid(row=4, column=1, padx=5, pady=5)\n            def save_mini():'
)
content = content.replace(
    'conn.execute("INSERT INTO duenos (nombre, dni, telefono, direccion) VALUES (?, ?, ?, ?)",\n                             (e_nom.get(), e_dni.get(), e_tel.get(), e_dir.get()))',
    'conn.execute("INSERT INTO duenos (nombre, dni, telefono, direccion, email) VALUES (?, ?, ?, ?, ?)",\n                             (e_nom.get(), e_dni.get(), e_tel.get(), e_dir.get(), e_email.get()))'
)
content = content.replace(
    'tk.Button(d2, text="Guardar", bg="#2ecc71", fg="white", relief="flat",\n                      command=save_mini, cursor="hand2").grid(row=4, column=1, pady=10, sticky="e")',
    'tk.Button(d2, text="Guardar", bg="#2ecc71", fg="white", relief="flat",\n                      command=save_mini, cursor="hand2").grid(row=5, column=1, pady=10, sticky="e")'
)

# 12. add_appointment_dialog - add tipo and precio fields
content = content.replace(
    'e_animal.grid(row=0, column=1, padx=10, pady=8)\n        if animal_id:',
    'e_animal.grid(row=0, column=1, padx=10, pady=8)\n\n        tk.Label(dialog, text="Tipo", bg="#f0f4f8", font=("Segoe UI", 10)).grid(\n            row=1, column=0, sticky="e", padx=10, pady=8)\n        e_tipo = ttk.Combobox(dialog, values=["veterinaria", "grooming"], width=37, font=("Segoe UI", 10))\n        e_tipo.set("veterinaria")\n        e_tipo.grid(row=1, column=1, padx=10, pady=8)\n\n        if animal_id:'
)
content = content.replace(
    'tk.Label(dialog, text="Fecha", bg="#f0f4f8", font=("Segoe UI", 10)).grid(\n            row=1, column=0, sticky="e", padx=10, pady=8)',
    'tk.Label(dialog, text="Fecha", bg="#f0f4f8", font=("Segoe UI", 10)).grid(\n            row=2, column=0, sticky="e", padx=10, pady=8)'
)
content = content.replace(
    'e_fecha.grid(row=1, column=1, padx=10, pady=8)\n\n        motivos',
    'e_fecha.grid(row=2, column=1, padx=10, pady=8)\n\n        tk.Label(dialog, text="Precio", bg="#f0f4f8", font=("Segoe UI", 10)).grid(\n            row=3, column=0, sticky="e", padx=10, pady=8)\n        e_precio = tk.Entry(dialog, width=40, font=("Segoe UI", 10))\n        e_precio.grid(row=3, column=1, padx=10, pady=8)\n\n        motivos'
)
content = content.replace(
    'e_motivo.grid(row=2, column=1, padx=10, pady=8)',
    'e_motivo.grid(row=4, column=1, padx=10, pady=8)'
)
# Fix save in add_appointment_dialog
content = content.replace(
    '"INSERT INTO citas (id_animal, id_dueno, fecha, motivo) VALUES (?, ?, ?, ?)",\n                (animal_id, id_dueno, e_fecha.get(), e_motivo.get()))',
    '"INSERT INTO citas (id_animal, id_dueno, fecha, motivo, tipo, precio) VALUES (?, ?, ?, ?, ?, ?)",\n                (animal_id, id_dueno, e_fecha.get(), e_motivo.get(), e_tipo.get(), float(e_precio.get() or 0)))'
)
content = content.replace(
    'tk.Button(dialog, text="Guardar", bg="#2ecc71", fg="white",\n                  font=("Segoe UI", 10), relief="flat", padx=20, pady=5,\n                  command=save, cursor="hand2").grid(row=3, column=1, pady=15, sticky="e")',
    'tk.Button(dialog, text="Guardar", bg="#2ecc71", fg="white",\n                  font=("Segoe UI", 10), relief="flat", padx=20, pady=5,\n                  command=save, cursor="hand2").grid(row=5, column=1, pady=15, sticky="e")'
)

# 13. Fix _make_doctor_frame - add blank line before add_appointment_dialog
# (this is already fine, it's just a method declaration)

# Append to the file
with open(filepath, "a", encoding="utf-8") as f:
    f.write(content)

# Count lines
with open(filepath, "r", encoding="utf-8") as f:
    total_lines = len(f.readlines())

print(f"Appended modified content from original. Total lines: {total_lines}")
