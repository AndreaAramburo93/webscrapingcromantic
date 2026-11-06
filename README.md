# Scraper de precios capilares de Cromantic con flujo DevOps

Proyecto de la Evidencia de aprendizaje 2 (Programación para Análisis de Datos, IU Digital de Antioquia).
Extrae SKU, marca, nombre y precio de la categoría capilar de [Cromantic](https://www.cromantic.com/),
los guarda en CSV y publica un reporte en GitHub Pages. Cada cambio pasa por pruebas automáticas antes de llegar a `main`.

![CI](https://github.com/AndreaAramburo93/cromantic-scraper-devops/actions/workflows/ci.yml/badge.svg)

## Estructura

```
cromantic-scraper-devops/
├── src/cromantic_scraper/
│   ├── scraper.py      # petición GET, lectura de JSON-LD y paginación
│   ├── analysis.py     # estadísticas con pandas
│   ├── report.py       # página HTML del reporte
│   └── __main__.py     # punto de entrada: scraping → CSV → HTML
├── tests/              # pruebas unitarias (pytest) con HTML de ejemplo, sin red
├── data/               # productos_cromantic.csv (respaldo y versión de los datos)
├── notebooks/          # notebook original de la Evidencia 1 (Colab)
├── .github/workflows/
│   ├── ci.yml          # integración continua: flake8 + pytest en cada push y PR
│   └── deploy.yml      # despliegue continuo: scraper + GitHub Pages al llegar a main
├── Dockerfile
├── pyproject.toml
└── requirements*.txt
```

## Ejecutar en local

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pip install -e .

python -m cromantic_scraper --paginas 12   # genera data/productos_cromantic.csv y site/index.html
pytest                                      # corre las pruebas
flake8 src tests                            # revisa estilo PEP 8
```

Con Docker:

```bash
docker build -t cromantic-scraper .
docker run --rm -v "$PWD/data:/app/data" -v "$PWD/site:/app/site" cromantic-scraper
```

## Flujo de trabajo DevOps

Se usa **GitHub Flow**: `main` siempre está estable y todo cambio entra por una rama y un pull request.

1. Se crea una rama desde `main` (`feature/...`, `fix/...`, `docs/...`).
2. Se hacen commits pequeños con mensajes claros (`feat:`, `fix:`, `test:`, `docs:`, `ci:`).
3. Cada `push` dispara **CI** (`ci.yml`): instala dependencias, corre `flake8` y `pytest` en Python 3.10, 3.11 y 3.12.
4. Se abre un pull request hacia `main`. La regla de protección exige que CI esté en verde y una revisión.
5. Al fusionar, se dispara **CD** (`deploy.yml`): repite las pruebas, ejecuta el scraper, guarda el CSV
   actualizado y publica el reporte en GitHub Pages. Al final hace una prueba de humo sobre la URL publicada.
6. CD también corre cada lunes a las 7:00 a. m. (hora Colombia) para refrescar precios.

Si Cromantic no responde desde el servidor de GitHub, el scraper usa el último CSV guardado,
así el sitio nunca queda vacío.

## Configuración en GitHub (una sola vez)

1. Crear el repositorio `cromantic-scraper-devops` (público) y subir el código.
2. **Settings → Pages → Source: GitHub Actions.**
3. **Settings → Branches → Add rule** para `main`: *Require a pull request before merging* y
   *Require status checks to pass* (seleccionar los trabajos `pruebas`).
4. **Settings → Actions → General → Workflow permissions: Read and write.**
5. Copiar en `data/` el `productos_cromantic.csv` descargado de Colab como primer respaldo.

## Comandos de Git usados en el proyecto

```bash
# 1. Repositorio y primer push
git init
git add .
git commit -m "chore: estructura inicial del proyecto"
git branch -M main
git remote add origin https://github.com/AndreaAramburo93/cromantic-scraper-devops.git
git push -u origin main

# 2. Rama para el scraper
git checkout -b feature/scraper
git add src/cromantic_scraper/scraper.py
git commit -m "feat: extracción de productos desde JSON-LD"
git push -u origin feature/scraper      # luego: pull request en GitHub

# 3. Simular un error y revertirlo (rollback)
git commit -am "feat: cambia patrón de paginación"   # commit con error
git log --oneline                                    # ubicar el commit
git revert HEAD                                      # crea un commit que deshace el anterior
git push

# 4. Segunda rama (otro integrante): reporte y visualización
git checkout main && git pull
git checkout -b feature/reporte
git add src/cromantic_scraper/report.py
git commit -m "feat: reporte HTML para GitHub Pages"
git push -u origin feature/reporte

# 5. Resolver un conflicto al actualizar la rama con main
git fetch origin
git merge origin/main        # si hay conflicto, editar el archivo marcado <<<<<<< ======= >>>>>>>
git add archivo_resuelto.py
git commit -m "fix: resuelve conflicto con main"
git push

# 6. Versión estable
git checkout main && git pull
git tag -a v1.0.0 -m "Primera versión estable"
git push origin v1.0.0
```

## Pruebas automatizadas

| Archivo | Qué valida |
| --- | --- |
| `tests/test_scraper.py` | Lectura de ItemList, marca como texto o diccionario, precio en `Offer` y `AggregateOffer`, entidades HTML, JSON roto, corte de paginación cuando una página se repite |
| `tests/test_analysis.py` | Eliminación de SKU repetidos, estadísticas de precio, orden por marca, escape de HTML en el reporte, lectura del CSV del notebook |

Las pruebas usan `tests/fixtures/capilar_pagina1.html`, una página de ejemplo con la misma
estructura JSON-LD del sitio. No dependen de internet, por eso no fallan si la tienda cambia o se cae.

## Uso responsable

El scraper espera 1,5 s entre páginas, se identifica con un User-Agent de navegador y solo lee
datos públicos de precio. Antes de ampliar el alcance hay que revisar `https://www.cromantic.com/robots.txt`
y los términos del sitio.
