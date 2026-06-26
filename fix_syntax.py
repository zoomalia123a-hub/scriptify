# Fix syntax errors in v2 file
with open(r'C:\SCRIPTYFY.V02UNSUEÑO\veterinaria_gui_v2.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix missing closing parenthesis
content = content.replace(
    "messagebox.showerror('Error', f'Error al procesar venta: {ex}'",
    "messagebox.showerror('Error', f'Error al procesar venta: {ex}')"
)

with open(r'C:\SCRIPTYFY.V02UNSUEÑO\veterinaria_gui_v2.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed syntax errors")

import py_compile
try:
    py_compile.compile(r'C:\SCRIPTYFY.V02UNSUEÑO\veterinaria_gui_v2.py', doraise=True)
    print("Syntax OK")
except py_compile.PyCompileError as e:
    print(f"SYNTAX ERROR: {e}")
