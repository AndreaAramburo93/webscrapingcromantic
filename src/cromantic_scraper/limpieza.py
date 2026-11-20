"""Validación de integridad y limpieza básica de los productos extraídos.

Reglas (fase de preparación de datos en CRISP-DM):
1. Quitar espacios sobrantes en los textos.
2. Descartar filas sin SKU o sin nombre: no se pueden identificar.
3. Descartar precios vacíos, no numéricos o menores o iguales a cero.
4. Descartar SKU repetidos (se conserva la primera aparición).
5. Completar la marca vacía con la marca por defecto.
6. Recalcular el precio en texto a partir del precio numérico.
"""

import pandas as pd

from .scraper import MARCA_POR_DEFECTO, formatear_cop

COLUMNAS = ["sku", "marca", "nombre", "precio_cop", "precio_texto", "categoria"]
VACIOS = {"", "no disponible", "nan", "none"}


def _vacio(serie):
    return serie.isna() | serie.astype(str).str.strip().str.lower().isin(VACIOS)


def limpiar(df):
    """Devuelve (df_limpio, reporte) sin modificar el DataFrame original."""
    datos = df.copy()
    for col in COLUMNAS:
        if col not in datos.columns:
            datos[col] = None
    datos = datos[COLUMNAS]
    reporte = {"filas_entrada": int(len(datos))}

    for col in ("sku", "marca", "nombre", "categoria"):
        texto = datos[col].astype(str).str.strip()
        datos[col] = datos[col].where(datos[col].isna(), texto)

    sin_sku = _vacio(datos["sku"])
    reporte["sin_sku"] = int(sin_sku.sum())
    datos = datos[~sin_sku]

    sin_nombre = _vacio(datos["nombre"])
    reporte["sin_nombre"] = int(sin_nombre.sum())
    datos = datos[~sin_nombre]

    datos["precio_cop"] = pd.to_numeric(datos["precio_cop"], errors="coerce")
    precio_malo = datos["precio_cop"].isna() | (datos["precio_cop"] <= 0)
    reporte["precio_invalido"] = int(precio_malo.sum())
    datos = datos[~precio_malo]

    repetidos = datos.duplicated(subset=["sku"], keep="first")
    reporte["duplicados"] = int(repetidos.sum())
    datos = datos[~repetidos]

    marca_vacia = _vacio(datos["marca"])
    reporte["marca_completada"] = int(marca_vacia.sum())
    datos.loc[marca_vacia, "marca"] = MARCA_POR_DEFECTO

    datos["precio_texto"] = datos["precio_cop"].map(formatear_cop)
    datos = datos.reset_index(drop=True)
    reporte["filas_salida"] = int(len(datos))
    reporte["filas_descartadas"] = reporte["filas_entrada"] - reporte["filas_salida"]
    return datos, reporte
