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
    from datetime import datetime
    tipo_doc = "factura" if venta.get("tipo_comprobante") == "Factura" else "boleta"
    tiene_dni_valido = bool(venta.get("cliente_dni")) and len(venta.get("cliente_dni", "")) == 11
    es_factura = tipo_doc == "factura"
    if es_factura:
        cliente_tipo = "6"
        cliente_num = venta.get("cliente_dni") or "00000000"
    else:
        cliente_tipo = "1"
        cliente_num = venta.get("cliente_dni") or "00000000"
    cliente_nombre = venta.get("cliente_nombre") or ("Cliente Variado" if not es_factura else "CLIENTE VARIOS")
    if not cliente_nombre.strip():
        cliente_nombre = "Cliente Variado" if not es_factura else "CLIENTE VARIOS"
    cliente_dir = venta.get("cliente_direccion") or ""
    tiene_igv = float(venta.get("igv", 0)) > 0
    sunat_items = []
    total_gravada = 0.0
    total_exonerada = 0.0
    total_igv = 0.0
    total_item_sum = 0.0
    for it in items:
        cantidad = float(it.get("cantidad") or it.get("cant", 1))
        precio_unitario = float(it.get("precio_unitario") or it.get("precio", 0))
        subtotal_item = float(it.get("subtotal", 0))
        if tiene_igv and tipo_doc == "factura":
            valor_unitario = round(precio_unitario / 1.18, 6)
            base_item = round(valor_unitario * cantidad, 2)
            igv_item = round(base_item * 0.18, 2)
            total_item = round(base_item + igv_item, 2)
            total_gravada += base_item
            total_igv += igv_item
            pct_igv = "18"
            cod_afectacion = "10"
            tributo = "IGV"
        else:
            valor_unitario = round(precio_unitario, 6)
            igv_item = 0
            base_item = round(valor_unitario * cantidad, 2)
            total_item = base_item
            total_exonerada += base_item
            pct_igv = "0"
            cod_afectacion = "21"
            tributo = "GRA"
        codigo = str(it.get("referencia_id") or it.get("id", ""))
        sunat_items.append({
            "unidad_de_medida": "NIU",
            "codigo_interno": codigo or "",
            "descripcion": it.get("nombre", "Producto"),
            "cantidad": str(cantidad),
            "valor_unitario": str(valor_unitario),
            "precio_unitario": str(round(precio_unitario, 2)),
            "subtotal": str(round(base_item, 2)),
            "porcentaje_igv": pct_igv,
            "codigo_tipo_afectacion_igv": cod_afectacion,
            "nombre_tributo": tributo,
            "tipo_de_igv": "1" if tiene_igv else "2",
            "igv": str(round(igv_item, 2)),
            "total": str(round(total_item, 2)),
        })
        total_item_sum += round(total_item, 2)
    total_general = round(total_gravada + total_exonerada + total_igv, 2)
    data = {
        "documento": tipo_doc,
        "serie": venta.get("serie", "B001"),
        "numero": int(venta.get("numero", 0)),
        "fecha_de_emision": venta.get("fecha", ""),
        "fecha_de_vencimiento": venta.get("fecha", ""),
        "hora_de_emision": venta.get("hora", datetime.now().strftime("%H:%M:%S")),
        "tipo_operacion": "0101",
        "moneda": "PEN",
        "cliente_tipo_de_documento": cliente_tipo,
        "cliente_numero_de_documento": cliente_num,
        "cliente_denominacion": cliente_nombre,
        "cliente_direccion": cliente_dir or "AV SIN DIRECCION 123",
        "total_gravada": str(round(total_gravada, 2)),
        "total_exonerada": str(round(total_exonerada, 2)),
        "total_igv": str(round(total_igv, 2)),
        "total": str(round(total_general, 2)),
        "items": sunat_items,
    }
    return data
