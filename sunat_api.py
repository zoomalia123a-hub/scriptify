import requests
import json

def _config():
    import os
    cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(cfg_path):
        with open(cfg_path) as f:
            cfg = json.load(f)
    else:
        cfg = {}
    return {
        "token": cfg.get("sunat_token", ""),
        "base_url": cfg.get("sunat_base_url", "https://dev.apisunat.pe/api/v3"),
        "ruc": cfg.get("sunat_ruc", ""),
        "enabled": cfg.get("sunat_enabled", False),
    }

def _headers():
    c = _config()
    return {
        "Authorization": f"Bearer {c['token']}",
        "Content-Type": "application/json",
    }

def consultar_ruc(num_ruc):
    try:
        r = requests.get(f"https://dev.apisunat.pe/api/v1/business/ruc/{num_ruc}",
            headers=_headers(), timeout=15)
        return r.json()
    except Exception as e:
        return {"success": False, "message": str(e)}

def consultar_dni(dni):
    try:
        r = requests.get(f"https://dev.apisunat.pe/api/v1/person/dni/{dni}",
            headers=_headers(), timeout=15)
        return r.json()
    except Exception as e:
        return {"success": False, "message": str(e)}

def emitir_comprobante(data):
    c = _config()
    if not c["enabled"]:
        return {"success": False, "message": "SUNAT deshabilitado en config"}
    try:
        r = requests.post(f"{c['base_url']}/documents",
            headers=_headers(), json=data, timeout=30)
        return r.json()
    except Exception as e:
        return {"success": False, "message": str(e)}

def consultar_estado(ticket):
    try:
        r = requests.post(f"{_config()['base_url']}/status",
            headers=_headers(), json={"ticket": ticket}, timeout=15)
        return r.json()
    except Exception as e:
        return {"success": False, "message": str(e)}

def armar_comprobante(venta, items):
    tipo_doc = "factura" if venta.get("tipo_comprobante") == "Factura" else "boleta"
    tiene_dni_valido = bool(venta.get("cliente_dni")) and len(venta.get("cliente_dni", "")) == 11
    cliente_tipo = "6" if tiene_dni_valido else "1"
    cliente_num = venta.get("cliente_dni") or "00000000"
    cliente_nombre = venta.get("cliente_nombre") or "Cliente Variado"
    if not cliente_nombre.strip():
        cliente_nombre = "Cliente Variado"
    cliente_dir = venta.get("cliente_direccion") or ""
    tiene_igv = float(venta.get("igv", 0)) > 0
    sunat_items = []
    for it in items:
        cantidad = float(it.get("cantidad") or it.get("cant", 1))
        precio_unitario = float(it.get("precio_unitario") or it.get("precio", 0))
        subtotal_item = float(it.get("subtotal", 0))
        if tiene_igv and tipo_doc == "factura":
            valor_unitario = round(precio_unitario / 1.18, 4)
            igv_item = round(subtotal_item - (subtotal_item / 1.18), 2)
            total_item = subtotal_item
        else:
            valor_unitario = precio_unitario
            igv_item = 0
            total_item = subtotal_item
        codigo = str(it.get("referencia_id") or it.get("id", ""))
        sunat_items.append({
            "unidad_de_medida": "NIU",
            "codigo": codigo or "",
            "descripcion": it.get("nombre", "Producto"),
            "cantidad": cantidad,
            "valor_unitario": valor_unitario,
            "precio_unitario": precio_unitario,
            "subtotal": subtotal_item,
            "tipo_de_igv": "1" if tiene_igv else "2",
            "igv": igv_item,
            "total": total_item,
        })
    data = {
        "documento": tipo_doc,
        "serie": venta.get("serie", "B001"),
        "numero": int(venta.get("numero", 0)),
        "fecha_de_emision": venta.get("fecha", ""),
        "fecha_de_vencimiento": venta.get("fecha", ""),
        "moneda": "PEN",
        "cliente_tipo_de_documento": cliente_tipo,
        "cliente_numero_de_documento": cliente_num,
        "cliente_denominacion": cliente_nombre,
        "cliente_direccion": cliente_dir,
        "items": sunat_items,
    }
    return data
