"""Análisis descriptivo de un producto.

Ubica un producto frente a tres referencias: todo el catálogo capilar, su
marca y los productos del mismo tipo (la primera palabra del nombre:
«Cepillo», «Shampoo», «Kit»...). Si hay historial, describe cómo cambió su
precio. Con eso redacta frases que se actualizan solas en cada extracción.
"""

from .scraper import formatear_cop


def tipo_de(nombre):
    """Primera palabra del nombre, como aproximación al tipo de producto."""
    palabras = str(nombre).split()
    return palabras[0].capitalize() if palabras else "Otro"


def _pct(valor):
    return f"{valor:.0f} %"


def perfil_producto(df, hist, sku):
    """Devuelve el análisis de un SKU, o None si no está en el catálogo."""
    fila = df[df["sku"].astype(str) == str(sku)]
    if fila.empty:
        return None
    p = fila.iloc[0]
    precio = float(p["precio_cop"])
    precios = df["precio_cop"].dropna()
    mediana = float(precios.median())

    # Catálogo completo
    percentil = float((precios < precio).mean() * 100)
    razon = precio / mediana if mediana else 0

    # Marca
    marca = df[df["marca"] == p["marca"]].sort_values("precio_cop", ascending=False)
    puesto_marca = int(list(marca["sku"].astype(str)).index(str(sku)) + 1)
    promedio_marca = float(marca["precio_cop"].mean())

    # Tipo de producto
    tipo = tipo_de(p["nombre"])
    mismo_tipo = df[df["nombre"].map(tipo_de) == tipo]
    promedio_tipo = float(mismo_tipo["precio_cop"].mean())
    dif_tipo = (precio / promedio_tipo - 1) * 100 if promedio_tipo else 0

    # Historial de precios
    serie = []
    if hist is not None and len(hist):
        h = hist[hist["sku"].astype(str) == str(sku)].sort_values("fecha")
        serie = [{"fecha": f, "precio": float(v), "precio_texto": formatear_cop(v)}
                 for f, v in zip(h["fecha"], h["precio_cop"])]

    frases = []
    if razon >= 1:
        veces = f"{razon:.1f}".replace(".", ",")
        comparacion = f"equivale a {veces} veces la mediana del catálogo"
    else:
        comparacion = f"cuesta el {_pct(razon * 100)} de la mediana del catálogo"
    frases.append(
        f"Cuesta {formatear_cop(precio)}: es más caro que el {_pct(percentil)} "
        f"de los productos capilares y {comparacion} ({formatear_cop(mediana)}).")

    if len(serie) >= 2:
        valores = [s["precio"] for s in serie]
        bajo, alto = min(valores), max(valores)
        if alto != bajo:
            caida = (1 - bajo / alto) * 100
            frases.append(
                f"Entre el {serie[0]['fecha']} y el {serie[-1]['fecha']} su precio "
                f"varió entre {formatear_cop(bajo)} y {formatear_cop(alto)}: "
                f"una diferencia del {_pct(caida)}.")
            if precio == alto:
                frases.append("El precio actual es el más alto registrado, así que "
                              "hoy no tiene promoción.")
            elif precio == bajo:
                frases.append("El precio actual es el más bajo registrado: "
                              "la promoción sigue activa.")
        else:
            frases.append(f"Su precio no cambió en las {len(serie)} extracciones.")
    else:
        frases.append("Todavía no hay suficientes extracciones para ver la "
                      "evolución de su precio.")

    frases.append(
        f"{p['marca']} tiene {len(marca)} productos en la categoría, con un precio "
        f"promedio de {formatear_cop(promedio_marca)}; este ocupa el puesto "
        f"{puesto_marca} de {len(marca)} por precio dentro de su marca.")

    if len(mismo_tipo) > 1:
        lado = "por encima" if dif_tipo >= 0 else "por debajo"
        frases.append(
            f"Entre los {len(mismo_tipo)} productos de tipo «{tipo}», el promedio es "
            f"{formatear_cop(promedio_tipo)}; este está un {_pct(abs(dif_tipo))} "
            f"{lado} de ese promedio.")
    else:
        frases.append(f"Es el único producto de tipo «{tipo}» en el catálogo.")

    return {
        "sku": str(p["sku"]),
        "marca": p["marca"],
        "nombre": p["nombre"],
        "precio_texto": formatear_cop(precio),
        "percentil": round(percentil),
        "mediana_texto": formatear_cop(mediana),
        "marca_productos": int(len(marca)),
        "marca_promedio_texto": formatear_cop(promedio_marca),
        "puesto_marca": puesto_marca,
        "tipo": tipo,
        "tipo_productos": int(len(mismo_tipo)),
        "tipo_promedio_texto": formatear_cop(promedio_tipo),
        "historial": serie,
        "frases": frases,
    }
