"""Genera la página HTML que se publica en GitHub Pages."""

import html
from datetime import datetime, timezone

from .analysis import mas_caros, por_marca, resumen_precios
from .scraper import formatear_cop

PLANTILLA = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Precios capilares Cromantic</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 880px;
       margin: 0 auto; padding: 24px 16px; color: #1d1d1f; }}
h1 {{ font-size: 1.6rem; margin-bottom: 4px; }}
.meta {{ color: #666; font-size: .9rem; margin-bottom: 24px; }}
.kpis {{ display: grid; grid-template-columns: repeat(auto-fit,
        minmax(150px, 1fr)); gap: 12px; margin-bottom: 28px; }}
.kpi {{ border: 1px solid #ddd; border-radius: 8px; padding: 12px; }}
.kpi b {{ display: block; font-size: 1.3rem; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 28px;
        font-size: .92rem; }}
th, td {{ border-bottom: 1px solid #e5e5e5; padding: 8px 6px;
         text-align: left; }}
th {{ background: #f6f6f6; }}
td.num {{ text-align: right; white-space: nowrap; }}
</style>
</head>
<body>
<h1>Precios de productos capilares en Cromantic</h1>
<p class="meta">Actualizado: {fecha} &middot; Fuente: {fuente}</p>
<div class="kpis">
<div class="kpi">Productos<b>{productos}</b></div>
<div class="kpi">Precio promedio<b>{promedio}</b></div>
<div class="kpi">Mediana<b>{mediana}</b></div>
<div class="kpi">Rango<b>{minimo} &ndash; {maximo}</b></div>
</div>
<h2>Precio promedio por marca</h2>
<table><tr><th>Marca</th><th>Productos</th><th>Precio promedio</th></tr>
{filas_marca}
</table>
<h2>Los 5 productos más caros</h2>
<table><tr><th>Marca</th><th>Producto</th><th>Precio</th></tr>
{filas_caros}
</table>
<h2>Catálogo extraído</h2>
<table><tr><th>SKU</th><th>Marca</th><th>Producto</th><th>Precio</th></tr>
{filas_todos}
</table>
</body>
</html>
"""


def _e(texto):
    return html.escape(str(texto))


def construir_html(df, fuente="https://www.cromantic.com/capilar"):
    """Devuelve el HTML del reporte a partir del DataFrame."""
    r = resumen_precios(df)
    filas_marca = "\n".join(
        f"<tr><td>{_e(f.marca)}</td><td class='num'>{f.productos}</td>"
        f"<td class='num'>{formatear_cop(f.precio_promedio)}</td></tr>"
        for f in por_marca(df).itertuples()
    )
    filas_caros = "\n".join(
        f"<tr><td>{_e(f.marca)}</td><td>{_e(f.nombre)}</td>"
        f"<td class='num'>{_e(f.precio_texto)}</td></tr>"
        for f in mas_caros(df).itertuples()
    )
    filas_todos = "\n".join(
        f"<tr><td>{_e(f.sku)}</td><td>{_e(f.marca)}</td>"
        f"<td>{_e(f.nombre)}</td><td class='num'>{_e(f.precio_texto)}</td></tr>"
        for f in df.sort_values("precio_cop", ascending=False).itertuples()
    )
    return PLANTILLA.format(
        fecha=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        fuente=_e(fuente),
        productos=r["productos"],
        promedio=formatear_cop(r["promedio"]),
        mediana=formatear_cop(r["mediana"]),
        minimo=formatear_cop(r["minimo"]),
        maximo=formatear_cop(r["maximo"]),
        filas_marca=filas_marca,
        filas_caros=filas_caros,
        filas_todos=filas_todos,
    )
