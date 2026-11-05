"""Extracción de productos de Cromantic a partir de sus bloques JSON-LD.

Las funciones de lectura (parse_*) reciben HTML como texto y no hacen
peticiones de red. Así se pueden probar en el pipeline de CI con archivos
de ejemplo, sin depender de que el sitio esté disponible.
"""

import html
import json
import logging
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.cromantic.com/"
# Patrón de paginación. Verificar en el navegador cómo numera el sitio
# sus páginas (por ejemplo ?page=2) antes de cambiarlo.
URL_PAGINACION = "https://www.cromantic.com/capilar?page={pagina}"
MARCA_POR_DEFECTO = "Cromantic"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def obtener_marca(producto):
    """Devuelve el nombre de la marca, venga como diccionario o como texto."""
    marca = producto.get("brand", {})
    if isinstance(marca, dict):
        return marca.get("name") or MARCA_POR_DEFECTO
    if isinstance(marca, str) and marca.strip():
        return marca.strip()
    return MARCA_POR_DEFECTO


def obtener_precio(producto):
    """Devuelve el precio como float, o None si no está disponible."""
    ofertas = producto.get("offers", {})
    if isinstance(ofertas, list) and ofertas:
        ofertas = ofertas[0]
    if isinstance(ofertas, dict):
        valor = (
            ofertas.get("lowPrice")
            or ofertas.get("price")
            or ofertas.get("highPrice")
        )
        if valor not in (None, ""):
            try:
                return float(valor)
            except (TypeError, ValueError):
                return None
    return None


def formatear_cop(precio):
    """Convierte 49900.0 en '$49.900'."""
    if precio is None:
        return "No disponible"
    return f"${precio:,.0f}".replace(",", ".")


def armar_registro(producto, categoria):
    """Construye el diccionario de un producto con las columnas finales."""
    nombre = html.unescape(producto.get("name", "No disponible"))
    sku = str(producto.get("sku") or producto.get("@id") or "No disponible")
    marca = html.unescape(obtener_marca(producto))
    precio = obtener_precio(producto)
    return {
        "sku": sku,
        "marca": marca,
        "nombre": nombre,
        "precio_cop": precio,
        "precio_texto": formatear_cop(precio),
        "categoria": categoria,
    }


def parse_productos(contenido_html, categoria="Belleza"):
    """Lee los bloques JSON-LD (ItemList o Product) de una página."""
    soup = BeautifulSoup(contenido_html, "html.parser")
    productos = []
    for script in soup.find_all("script", type="application/ld+json"):
        if not script.string:
            continue
        try:
            datos = json.loads(script.string)
        except json.JSONDecodeError as error:
            logger.warning("Bloque JSON-LD inválido: %s", error)
            continue
        bloques = datos if isinstance(datos, list) else [datos]
        for bloque in bloques:
            if not isinstance(bloque, dict):
                continue
            tipo = bloque.get("@type")
            if tipo == "ItemList":
                for envoltura in bloque.get("itemListElement", []):
                    producto = envoltura.get("item", {})
                    if producto:
                        productos.append(armar_registro(producto, categoria))
            elif tipo == "Product":
                productos.append(armar_registro(bloque, categoria))
    return productos


def descargar(url, sesion=None, timeout=10):
    """Hace la petición GET y devuelve el HTML, o None si falla."""
    cliente = sesion or requests
    try:
        respuesta = cliente.get(url, headers=HEADERS, timeout=timeout)
    except requests.RequestException as error:
        logger.error("Error de red en %s: %s", url, error)
        return None
    if respuesta.status_code != 200:
        logger.warning("%s respondió %s", url, respuesta.status_code)
        return None
    return respuesta.text


def scrape_paginado(paginas=12, patron=URL_PAGINACION, pausa=1.5,
                    categoria="Capilar", obtener_html=descargar):
    """Recorre las páginas de una categoría y consolida productos únicos.

    Se detiene en cuanto una página no aporta SKU nuevos: eso indica que el
    sitio está devolviendo la misma página o que se acabó el catálogo.
    """
    vistos = set()
    resultado = []
    for pagina in range(1, paginas + 1):
        contenido = obtener_html(patron.format(pagina=pagina))
        if contenido is None:
            continue
        nuevos = [p for p in parse_productos(contenido, categoria)
                  if p["sku"] not in vistos]
        logger.info("Página %s: %s productos nuevos", pagina, len(nuevos))
        if not nuevos:
            logger.info("Sin productos nuevos; fin de la paginación.")
            break
        for producto in nuevos:
            vistos.add(producto["sku"])
            resultado.append(producto)
        if pausa:
            time.sleep(pausa)
    return resultado
