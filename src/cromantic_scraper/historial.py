"""Historial de precios por fecha y detección de descuentos.

Cada ejecución del scraper agrega sus precios con la fecha del día a
data/historial_precios.csv. Comparando las dos últimas fechas se sabe qué
productos bajaron (promoción activa) o subieron (promoción que terminó).
"""

from pathlib import Path

import pandas as pd

from .scraper import formatear_cop

COLUMNAS = ["fecha", "sku", "marca", "nombre", "precio_cop"]


def cargar(ruta):
    """Lee el historial; si no existe devuelve un DataFrame vacío."""
    ruta = Path(ruta)
    if not ruta.exists():
        return pd.DataFrame(columns=COLUMNAS)
    hist = pd.read_csv(ruta, sep=";", encoding="utf-8-sig", dtype={"sku": str})
    hist["precio_cop"] = pd.to_numeric(hist["precio_cop"], errors="coerce")
    return hist[COLUMNAS]


def agregar(df, ruta, fecha):
    """Agrega los precios de `df` con la fecha dada.

    Si ya había datos de esa fecha, los reemplaza: correr el scraper dos
    veces el mismo día no duplica el historial.
    """
    hist = cargar(ruta)
    hist = hist[hist["fecha"] != fecha]
    nuevos = df[["sku", "marca", "nombre", "precio_cop"]].copy()
    nuevos.insert(0, "fecha", fecha)
    hist = pd.concat([hist, nuevos], ignore_index=True)
    hist = hist.sort_values(["fecha", "sku"]).reset_index(drop=True)
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    hist.to_csv(ruta, sep=";", index=False, encoding="utf-8-sig")
    return hist


def fechas(hist):
    return sorted(hist["fecha"].dropna().unique())


def cambios(hist):
    """Compara las dos últimas fechas. Devuelve solo los SKU que cambiaron."""
    fs = fechas(hist)
    if len(fs) < 2:
        return pd.DataFrame()
    anterior, actual = fs[-2], fs[-1]
    a = hist[hist["fecha"] == anterior].drop_duplicates("sku")
    b = hist[hist["fecha"] == actual].drop_duplicates("sku")
    m = a.merge(b, on="sku", suffixes=("_antes", "_ahora"))
    m = m[m["precio_cop_antes"] != m["precio_cop_ahora"]].copy()
    m["fecha_antes"], m["fecha_ahora"] = anterior, actual
    m["marca"], m["nombre"] = m["marca_ahora"], m["nombre_ahora"]
    variacion = m["precio_cop_ahora"] / m["precio_cop_antes"] - 1
    m["variacion_pct"] = (variacion * 100).round(1)
    return m.reset_index(drop=True)


def resumen_cambios(hist):
    """Cuántos productos se compararon, subieron y bajaron."""
    fs = fechas(hist)
    if len(fs) < 2:
        return {"fechas": fs, "comparados": 0, "subieron": 0, "bajaron": 0}
    a = set(hist.loc[hist["fecha"] == fs[-2], "sku"])
    b = set(hist.loc[hist["fecha"] == fs[-1], "sku"])
    c = cambios(hist)
    subieron = bajaron = 0
    if len(c):
        subieron = int((c["precio_cop_ahora"] > c["precio_cop_antes"]).sum())
        bajaron = int((c["precio_cop_ahora"] < c["precio_cop_antes"]).sum())
    return {
        "fechas": fs,
        "fecha_antes": fs[-2],
        "fecha_ahora": fs[-1],
        "comparados": len(a & b),
        "subieron": subieron,
        "bajaron": bajaron,
    }


def top_descuentos(hist, n=10):
    """Los n productos con mayor diferencia entre sus dos últimos precios.

    El precio normal es el más alto de las dos fechas y el de promoción el
    más bajo. Si el precio bajó, la promoción está activa; si subió, ya terminó.
    """
    c = cambios(hist)
    if c.empty:
        return []
    c["precio_normal"] = c[["precio_cop_antes", "precio_cop_ahora"]].max(axis=1)
    c["precio_promocion"] = c[["precio_cop_antes", "precio_cop_ahora"]].min(axis=1)
    proporcion = c["precio_promocion"] / c["precio_normal"]
    c["descuento_pct"] = ((1 - proporcion) * 100).round(1)
    c["ahorro"] = c["precio_normal"] - c["precio_promocion"]
    bajo = c["precio_cop_ahora"] < c["precio_cop_antes"]
    c["estado"] = bajo.map({True: "activa", False: "terminada"})
    c = c.sort_values(["descuento_pct", "ahorro"], ascending=False).head(n)
    filas = []
    for f in c.itertuples():
        filas.append({
            "sku": f.sku,
            "marca": f.marca,
            "nombre": f.nombre,
            "precio_normal": f.precio_normal,
            "precio_promocion": f.precio_promocion,
            "precio_normal_texto": formatear_cop(f.precio_normal),
            "precio_promocion_texto": formatear_cop(f.precio_promocion),
            "descuento_pct": f.descuento_pct,
            "ahorro_texto": formatear_cop(f.ahorro),
            "estado": f.estado,
        })
    return filas
