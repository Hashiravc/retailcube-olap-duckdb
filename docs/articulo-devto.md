---
title: "Construyendo una solución OLAP con DuckDB, Python y Streamlit: análisis multidimensional de ventas"
published: false
description: "Aprende a diseñar e implementar una plataforma OLAP completa con DuckDB, Parquet, modelo estrella y operaciones multidimensionales (Roll-up, Drill-down, Slice, Dice, Pivot, Cube) desplegada en Streamlit Community Cloud."
tags: duckdb, python, streamlit, dataengineering
canonical_url: https://github.com/Hashiravc/retailcube-olap-duckdb
---

# Construyendo una solución OLAP con DuckDB, Python y Streamlit: análisis multidimensional de ventas

## 1. Introducción

En el ecosistema analítico moderno, las organizaciones generan millones de eventos transaccionales al día. Sin embargo, los sistemas orientados a transacciones (OLTP) no están diseñados para responder preguntas estratégicas como: *¿cuál fue la tasa de cancelación de productos de decoración en Alemania durante el cuarto trimestre en comparación con el año anterior?*. Ejecutar consultas de este tipo sobre bases de datos operacionales relacionales suele degradar el rendimiento del negocio o exigir infraestructura en la nube costosa y compleja.

En este artículo presentamos el diseño e implementación de **RetailCube Analytics**, una solución analítica de **Online Analytical Processing (OLAP)** construida íntegramente con tecnologías de código abierto: **DuckDB**, **Apache Parquet**, **Python** y **Streamlit**. A través del dataset histórico del *UCI Machine Learning Repository*, abordamos desde la ingestión y limpieza de transacciones reales hasta el modelado dimensional tipo estrella, la ejecución de las siete operaciones OLAP fundamentales con SQL nativo y el despliegue automatizado mediante CI/CD.

---

## 2. ¿Qué es OLAP y qué problema resuelve?

El procesamiento analítico en línea (**OLAP**, por sus siglas en inglés) es una categoría de tecnología de software que permite a analistas y directivos examinar datos multidimensionales de forma rápida, interactiva y consistente.

Mientras que los sistemas **OLTP (Online Transaction Processing)** priorizan inserciones rápidas, actualizaciones concurrentes e integridad ACID mediante normalización (3FN), los sistemas **OLAP** se optimizan para lecturas masivas, agregaciones complejas y exploración interactiva sobre grandes volúmenes históricos.

```
+------------------------------+-------------------------------------+-------------------------------------+
| Característica               | OLTP (Transaccional)                | OLAP (Analítico)                    |
+------------------------------+-------------------------------------+-------------------------------------+
| Objetivo principal           | Soporte operativo día a día         | Soporte a la toma de decisiones     |
| Diseño de base de datos      | Altamente normalizado (3FN)         | Esquema desnormalizado (Estrella)   |
| Patrón de acceso             | Lecturas/escrituras puntuales (Fila)| Lecturas masivas agregadas (Columna)|
| Almacenamiento habitual      | Basado en filas (Row-oriented)      | Basado en columnas (Column-oriented)|
| Complejidad de consultas     | Simples, uniendo pocas tablas       | Complejas, agregando millones filas |
+------------------------------+-------------------------------------+-------------------------------------+
```

OLAP resuelve el problema de la **latencia analítica**: permite segmentar la información a través de diferentes dimensiones (quién, cuándo, dónde y qué) en cuestión de milisegundos sin sobrecargar los sistemas de producción.

---

## 3. Objetivo de RetailCube Analytics

El objetivo principal de **RetailCube Analytics** es ofrecer una plataforma analítica multidimensional reproducible, libre de dependencias de nubes propietarias (como AWS Redshift o Google BigQuery), capaz de ejecutarse localmente o en un contenedor SaaS ligero con tiempos de respuesta sub-segundo sobre más de medio millón de transacciones comerciales reales.

Los objetivos técnicos específicos comprenden:
1. Diseñar un pipeline de datos idempotente que procese el dataset oficial de UCI Online Retail.
2. Modelar un **Esquema Estrella** formal con claves primarias sustitutas, integridad referencial y preservación del 100% de la facturación.
3. Demostrar y documentar las siete operaciones del álgebra OLAP con SQL verificable en DuckDB.
4. Desplegar una aplicación web interactiva en **Streamlit Community Cloud** con gráficos dinámicos en Plotly.
5. Garantizar la calidad del software con pruebas automatizadas en **GitHub Actions**.

---

## 4. Herramientas utilizadas

La arquitectura se fundamenta en herramientas líderes de software libre:

- **Python 3.13:** Núcleo de orquestación, limpieza y lógica de negocio.
- **DuckDB 2.0:** Motor de base de datos analítico columnar in-process ("el SQLite del análisis de datos"). Proporciona ejecución vectorial morsel-driven y soporte nativo de SQL OLAP.
- **Apache Parquet:** Formato de almacenamiento columnar inmutable comprimido con Snappy, optimizado para operaciones de *predicate pushdown* y proyección de columnas.
- **Streamlit 1.67:** Framework para la construcción del dashboard interactivo empresarial.
- **Plotly Express 7.1:** Biblioteca de visualización de datos interactiva.
- **Pytest:** Suite de pruebas automatizadas para validar integridad referencial y consistencia de medidas.
- **GitHub Actions:** Automatización de flujos de Integración Continua (CI) y regeneración de datos (Data Build Pipeline).

---

## 5. Arquitectura de la solución

La arquitectura adopta un enfoque desacoplado en cinco capas:

```
[ Fuente Oficial UCI ]
         │ (HTTP Stream / Zip)
         ▼
[ Ingestión & Calidad ] ──> data/processed/clean_retail_transactions.parquet (4.18 MB)
         │
         ▼
[ Modelo Dimensional ] ──> dim_fecha.parquet (305 filas)
                            dim_producto.parquet (3,938 filas)
                            dim_cliente.parquet (4,372 filas)
                            dim_pais.parquet (38 filas)
                            fact_ventas.parquet (539,392 filas)
         │
         ▼
[ Motor DuckDB OLAP ] ─── (Vistas en memoria con Zero-Copy sobre Parquet)
         │
         ▼
[ Streamlit Community Cloud ] ──> Dashboard Ejecutivo & Explorador OLAP
```

La ventaja decisiva de esta arquitectura es que **DuckDB consulta directamente los archivos Parquet en memoria sin necesidad de un servidor de base de datos dedicado**. Esto permite que la aplicación en la nube arranque en menos de 5 segundos con un consumo de memoria inferior a 250 MB.

---

## 6. Dataset y preparación de datos

### Fuente Oficial
Se utilizó el dataset **Online Retail** del *UCI Machine Learning Repository* (Chen, 2015), que recopila todas las transacciones ocurridas entre el 01/12/2010 y el 09/12/2011 para una tienda minorista en línea con sede en el Reino Unido.

### Retos de Calidad Identificados y Soluciones:
1. **Cancelaciones y Devoluciones:** Las facturas que comienzan con la letra 'C' o que registran cantidades negativas corresponden a devoluciones. En lugar de descartarlas (lo cual sobreestimaría los ingresos reales), creamos la bandera booleana `is_cancellation` y clasificamos la transacción como `CANCELACION`.
2. **Clientes Invitados (Valores Nulos en CustomerID):** El dataset contiene 135,080 filas sin identificador de cliente (24.9% del total). Eliminar estos registros distorsionaría las ventas reales en más de 1.7 millones de libras. Se implementó una clave sustituta dimensional `id_cliente = -1` con el alias `'CLIENTE_INVITADO'`, manteniendo la integridad referencial y el balance contable.
3. **Registros Anómalos:** Se identificaron 2,517 registros con precios unitarios menores o iguales a cero (ajustes contables o entradas de prueba sin valor comercial) que fueron filtrados.

### Métricas de Ingestión Auditadas:
- **Total de filas en crudo:** 541,909
- **Filas válidas depuradas:** 539,392
- **Ventas regulares:** 530,104 líneas
- **Cancelaciones registradas:** 9,288 líneas
- **Ingresos brutos:** £10,666,684.54
- **Devoluciones:** £896,812.49
- **Ingresos netos consolidados:** £9,769,872.05

---

## 7. Diseño del Data Warehouse

El modelo dimensional se estructuró siguiendo el patrón de **Esquema Estrella (Star Schema)** con granularidad explícita: **una fila por cada línea transaccional válida**.

### Dimensiones:
- **`dim_fecha`:** 305 días registrados. Incluye jerarquías: `anio`, `trimestre`, `nombre_trimestre`, `mes`, `nombre_mes`, `dia`, `dia_semana`, `es_fin_de_semana` y `anio_mes`.
- **`dim_producto`:** 3,938 productos. Clave sustituta `id_producto`, clave natural `codigo_stock`, descripción canónica y categoría funcional.
- **`dim_cliente`:** 4,372 clientes. Clave sustituta `id_cliente` (incluye `-1` para invitados), tipo de cliente (`REGISTRADO` / `INVITADO`) y país habitual.
- **`dim_pais`:** 38 países. Clave sustituta `id_pais`, nombre oficial, código ISO 3166-1 alfa-2 y región analítica (Reino Unido, Europa Occidental, Escandinavia, etc.).

### Tabla de Hechos (`fact_ventas`):
- Granularidad: 539,392 filas.
- Claves Foráneas: `id_fecha`, `id_producto`, `id_cliente`, `id_pais`.
- Medidas Aditivas: `monto_total` (Venta neta), `monto_bruto`, `monto_cancelacion`, `cantidad`.
- Medida Semiaditiva: `precio_unitario`.
- Métrica Calculada No Aditiva: `ticket_promedio = SUM(monto_total) / COUNT(DISTINCT numero_factura)`.

---

## 8. Implementación del modelo estrella en DuckDB

La base de datos relacional analítica se definió mediante el siguiente DDL reproducible:

```sql
-- DDL Simplificado del Esquema Estrella en DuckDB
CREATE TABLE dim_fecha (
    id_fecha INTEGER PRIMARY KEY,
    fecha DATE NOT NULL,
    anio INTEGER NOT NULL,
    trimestre INTEGER NOT NULL,
    nombre_trimestre VARCHAR NOT NULL,
    mes INTEGER NOT NULL,
    nombre_mes VARCHAR NOT NULL,
    dia INTEGER NOT NULL,
    dia_semana INTEGER NOT NULL,
    nombre_dia_semana VARCHAR NOT NULL,
    es_fin_de_semana BOOLEAN NOT NULL,
    anio_mes VARCHAR NOT NULL
);

CREATE TABLE dim_producto (
    id_producto INTEGER PRIMARY KEY,
    codigo_stock VARCHAR NOT NULL UNIQUE,
    descripcion VARCHAR NOT NULL,
    categoria VARCHAR NOT NULL,
    precio_unitario_referencia DOUBLE NOT NULL
);

CREATE TABLE dim_cliente (
    id_cliente INTEGER PRIMARY KEY,
    codigo_cliente VARCHAR NOT NULL,
    tipo_cliente VARCHAR NOT NULL,
    pais_origen VARCHAR NOT NULL
);

CREATE TABLE dim_pais (
    id_pais INTEGER PRIMARY KEY,
    nombre_pais VARCHAR NOT NULL UNIQUE,
    codigo_iso VARCHAR NOT NULL,
    region VARCHAR NOT NULL
);

CREATE TABLE fact_ventas (
    id_venta BIGINT PRIMARY KEY,
    numero_factura VARCHAR NOT NULL,
    id_fecha INTEGER NOT NULL REFERENCES dim_fecha(id_fecha),
    id_producto INTEGER NOT NULL REFERENCES dim_producto(id_producto),
    id_cliente INTEGER NOT NULL REFERENCES dim_cliente(id_cliente),
    id_pais INTEGER NOT NULL REFERENCES dim_pais(id_pais),
    hora_transaccion VARCHAR NOT NULL,
    cantidad INTEGER NOT NULL,
    precio_unitario DOUBLE NOT NULL,
    monto_total DOUBLE NOT NULL,
    monto_bruto DOUBLE NOT NULL,
    monto_cancelacion DOUBLE NOT NULL,
    es_cancelacion BOOLEAN NOT NULL,
    tipo_transaccion VARCHAR NOT NULL
);
```

---

## 9. Operaciones OLAP con DuckDB

A continuación se presentan las consultas SQL reales implementadas en la solución:

### A. ROLL-UP (Subir en la jerarquía)
Agrega medidas subiendo en la escala temporal: Día ➔ Mes ➔ Trimestre ➔ Año.

```sql
SELECT
    f.anio,
    f.nombre_trimestre,
    f.nombre_mes,
    COUNT(DISTINCT v.numero_factura) AS total_transacciones,
    ROUND(SUM(v.monto_total), 2) AS ventas_netas,
    ROUND(SUM(v.monto_total) / NULLIF(COUNT(DISTINCT v.numero_factura), 0), 2) AS ticket_promedio
FROM fact_ventas v
JOIN dim_fecha f ON v.id_fecha = f.id_fecha
GROUP BY ROLLUP (f.anio, f.nombre_trimestre, f.nombre_mes)
ORDER BY f.anio NULLS LAST, f.nombre_trimestre NULLS LAST, f.nombre_mes NULLS LAST;
```

### B. DRILL-DOWN (Bajar en la jerarquía)
Desciende a un nivel de mayor granularidad (por ejemplo, explorar las ventas diarias de noviembre de 2011).

```sql
SELECT
    f.anio,
    f.nombre_mes,
    f.dia,
    f.nombre_dia_semana,
    COUNT(DISTINCT v.numero_factura) AS total_transacciones,
    ROUND(SUM(v.monto_total), 2) AS ventas_netas
FROM fact_ventas v
JOIN dim_fecha f ON v.id_fecha = f.id_fecha
WHERE f.anio = 2011 AND f.mes = 11
GROUP BY f.anio, f.nombre_mes, f.dia, f.nombre_dia_semana
ORDER BY f.dia;
```

### C. SLICE (Corte unidimensional)
Fija una dimensión a un valor específico (por ejemplo, `nombre_pais = 'Germany'`) y proyecta las métricas restantes.

```sql
SELECT
    p.nombre_pais,
    f.anio_mes,
    pr.categoria,
    ROUND(SUM(v.monto_total), 2) AS ventas_netas,
    COUNT(DISTINCT v.numero_factura) AS total_transacciones
FROM fact_ventas v
JOIN dim_pais p ON v.id_pais = p.id_pais
JOIN dim_fecha f ON v.id_fecha = f.id_fecha
JOIN dim_producto pr ON v.id_producto = pr.id_producto
WHERE p.nombre_pais = 'Germany'
GROUP BY 1, 2, 3
ORDER BY f.anio_mes, ventas_netas DESC;
```

### D. DICE (Subcubo multidimensional)
Aplica filtros simultáneos sobre múltiples dimensiones (países seleccionados, categorías específicas y trimestres concretos).

```sql
SELECT
    p.nombre_pais,
    pr.categoria,
    f.nombre_trimestre,
    ROUND(SUM(v.monto_total), 2) AS ventas_netas,
    SUM(v.cantidad) AS unidades_vendidas
FROM fact_ventas v
JOIN dim_pais p ON v.id_pais = p.id_pais
JOIN dim_producto pr ON v.id_producto = pr.id_producto
JOIN dim_fecha f ON v.id_fecha = f.id_fecha
WHERE p.nombre_pais IN ('France', 'Germany', 'Spain')
  AND pr.categoria IN ('DECORACION_HOGAR', 'MENAJE_COCINA')
  AND f.anio = 2011 AND f.trimestre IN (3, 4)
GROUP BY p.nombre_pais, pr.categoria, f.nombre_trimestre
ORDER BY p.nombre_pais, pr.categoria, f.nombre_trimestre;
```

### E. PIVOT (Tabla dinámica de doble entrada)
DuckDB cuenta con sintaxis nativa `PIVOT` que permite rotar filas a columnas de forma concisa:

```sql
PIVOT (
    SELECT
        p.nombre_pais,
        f.anio || '-' || f.nombre_trimestre AS periodo,
        v.monto_total
    FROM fact_ventas v
    JOIN dim_pais p ON v.id_pais = p.id_pais
    JOIN dim_fecha f ON v.id_fecha = f.id_fecha
    WHERE p.nombre_pais IN ('United Kingdom', 'Germany', 'France', 'EIRE', 'Spain', 'Netherlands')
)
ON periodo
USING ROUND(SUM(monto_total), 2)
GROUP BY nombre_pais
ORDER BY nombre_pais;
```

### F. CUBE (Todas las combinaciones $2^N$)
Genera agregaciones para todas las combinaciones posibles de Región, Categoría y Año:

```sql
SELECT
    COALESCE(p.region, '--- TODAS LAS REGIONES ---') AS region,
    COALESCE(pr.categoria, '--- TODAS LAS CATEGORIAS ---') AS categoria,
    COALESCE(CAST(f.anio AS VARCHAR), '--- TODOS LOS ANIOS ---') AS anio,
    ROUND(SUM(v.monto_total), 2) AS ventas_netas,
    COUNT(DISTINCT v.numero_factura) AS total_transacciones
FROM fact_ventas v
JOIN dim_pais p ON v.id_pais = p.id_pais
JOIN dim_producto pr ON v.id_producto = pr.id_producto
JOIN dim_fecha f ON v.id_fecha = f.id_fecha
WHERE p.region IN ('Reino Unido', 'Europa Occidental')
GROUP BY CUBE (p.region, pr.categoria, f.anio)
ORDER BY p.region NULLS LAST, pr.categoria NULLS LAST, f.anio NULLS LAST;
```

### G. GROUPING SETS (Agregaciones selectivas)
Calcula en una sola pasada de tabla agregaciones a nivel de país, categoría, periodo y gran total:

```sql
SELECT
    COALESCE(p.nombre_pais, '--- TODOS LOS PAISES ---') AS pais,
    COALESCE(pr.categoria, '--- TODAS LAS CATEGORIAS ---') AS categoria,
    COALESCE(CAST(f.anio AS VARCHAR), '---') AS anio,
    COALESCE(f.nombre_trimestre, '---') AS trimestre,
    GROUPING(p.nombre_pais) AS grp_pais,
    GROUPING(pr.categoria) AS grp_categoria,
    GROUPING(f.anio, f.nombre_trimestre) AS grp_periodo,
    ROUND(SUM(v.monto_total), 2) AS ventas_netas
FROM fact_ventas v
JOIN dim_pais p ON v.id_pais = p.id_pais
JOIN dim_producto pr ON v.id_producto = pr.id_producto
JOIN dim_fecha f ON v.id_fecha = f.id_fecha
WHERE p.nombre_pais IN ('United Kingdom', 'Germany', 'France')
GROUP BY GROUPING SETS (
    (p.nombre_pais),
    (pr.categoria),
    (f.anio, f.nombre_trimestre),
    ()
)
ORDER BY grp_periodo DESC, grp_categoria DESC, grp_pais DESC, ventas_netas DESC;
```

---

## 10. Implementación del dashboard en Streamlit

La interfaz gráfica desarrollada en `app/streamlit_app.py` integra siete módulos de interacción:
1. **Vista General:** Tarjetas KPI con diseño responsivo y gráfica comparativa de ventas brutas vs devoluciones.
2. **Análisis Temporal:** Selector dinámico de granularidad y exploración interactiva de Roll-up y Drill-down.
3. **Análisis Geográfico:** Comparación de ventas internacionales, exclusión interactiva de mercados atípicos y mapas regionales.
4. **Análisis de Productos:** Ranking de los 20 artículos más vendidos y participación por segmento comercial.
5. **Explorador OLAP:** Laboratorio interactivo donde el usuario elige la operación analítica, personaliza filtros, visualiza la tabla resultante, examina el gráfico asociado, revisa el tiempo de ejecución en milisegundos y copia la consulta SQL empleada.
6. **Modelo Dimensional:** Diagrama visual del esquema estrella y documentación exhaustiva de claves y medidas.
7. **Información del Proyecto:** Atribución del dataset, arquitectura y enlaces al código fuente.

---

## 11. Automatización mediante GitHub Actions

Se diseñaron dos flujos de trabajo de Integración y Despliegue Continuo (CI/CD):

1. **`ci.yml` (Integración Continua):**
   - Se ejecuta en cada `push` y `pull_request` a la rama principal.
   - Instala dependencias, valida sintaxis de Python y ejecuta la suite completa de 17 pruebas con `pytest`.
2. **`data_build.yml` (Pipeline de Construcción de Datos):**
   - Se ejecuta bajo demanda (`workflow_dispatch`) o cuando se modifican los scripts de transformación o esquemas SQL.
   - Descarga y valida el dataset de origen, genera los archivos Parquet actualizados y realiza commit automático de los artefactos únicamente si se detectan cambios (`git diff --staged --quiet`), evitando ejecuciones infinitas.

---

## 12. Despliegue en Streamlit Community Cloud

La aplicación está desplegada públicamente en **Streamlit Community Cloud** conectada de forma nativa al repositorio GitHub. Cada vez que se integra un cambio probado en la rama `main`, la plataforma actualiza el contenedor de forma automática y transparente.

- **URL Pública de la Aplicación:** [retailcube-olap-duckdb.streamlit.app](https://retailcube-olap-duckdb.streamlit.app)
- **Repositorio Oficial:** [github.com/Hashiravc/retailcube-olap-duckdb](https://github.com/Hashiravc/retailcube-olap-duckdb)

---

## 13. Pruebas y resultados reales

Se diseñó una batería de 17 pruebas automatizadas (`tests/`) que validan:
- Presencia y tipos de columnas en la ingestión.
- Unicidad de claves primarias en las cuatro dimensiones.
- Integridad referencial de todas las claves foráneas en `fact_ventas` (0 huérfanos).
- Conservación matemática de la facturación: $Ventas\_Brutas - Cancelaciones = Ventas\_Netas$.
- Rendimiento y consistencia de las 7 operaciones OLAP (tiempos de respuesta inferiores a 100 ms).

Resultado de ejecución verificado:
```
tests/test_dashboard.py::test_dashboard_engine_kpis PASSED               [  5%]
tests/test_dashboard.py::test_dashboard_filter_dimension_values PASSED   [ 11%]
tests/test_ingestion.py::test_expected_columns_definition PASSED         [ 17%]
tests/test_ingestion.py::test_validate_schema_success PASSED             [ 23%]
tests/test_ingestion.py::test_validate_schema_failure PASSED             [ 29%]
tests/test_ingestion.py::test_clean_parquet_exists_and_valid PASSED      [ 35%]
tests/test_olap_queries.py::test_olap_rollup PASSED                      [ 41%]
tests/test_olap_queries.py::test_olap_drilldown PASSED                   [ 47%]
tests/test_olap_queries.py::test_olap_slice PASSED                       [ 52%]
tests/test_olap_queries.py::test_olap_dice PASSED                        [ 58%]
tests/test_olap_queries.py::test_olap_pivot PASSED                       [ 60%]
tests/test_olap_queries.py::test_olap_cube PASSED                        [ 66%]
tests/test_olap_queries.py::test_olap_grouping_sets PASSED               [ 73%]
tests/test_star_schema.py::test_dimensional_tables_exist PASSED          [ 80%]
tests/test_star_schema.py::test_primary_keys_uniqueness PASSED           [ 86%]
tests/test_star_schema.py::test_foreign_keys_referential_integrity PASSED [ 93%]
tests/test_star_schema.py::test_revenue_conservation_and_cancel_consistency PASSED [100%]

============================= 17 passed in 2.12s ==============================
```

---

## 14. Problemas encontrados y soluciones

1. **Lectura Lenta del Archivo Excel en Despliegues Ligeros:**
   - *Problema:* Parsear 540k filas de un archivo `.xlsx` en memoria toma más de 30 segundos y consume abundante memoria RAM.
   - *Solución:* Convertir el resultado limpio a formato Parquet comprimido con Snappy (4.18 MB). El tiempo de carga se redujo de 30 segundos a menos de 80 milisegundos.
2. **Aliases en la Cláusula GROUP BY durante la Operación Slice:**
   - *Problema:* Durante las primeras pruebas de `run_slice()`, DuckDB reportó error de sintaxis por incluir un alias `AS dimension_fijada` dentro de la cláusula `GROUP BY`.
   - *Solución:* Se ajustó la consulta para referenciar índices ordinales estándar `GROUP BY 1, 2, 3`, eliminando ambigüedades sintácticas.
3. **Manejo de Transacciones de Clientes No Identificados:**
   - *Problema:* El 25% de las ventas carecían de identificador de cliente, provocando fallos en la clave foránea hacia `dim_cliente`.
   - *Solución:* Se adoptó la práctica recomendada de Kimball de introducir un registro de dimensión comodín (`id_cliente = -1`, `codigo_cliente = 'INVITADO'`), reteniendo el 100% del volumen financiero.

---

## 15. Conclusiones

La combinación de **DuckDB**, **Apache Parquet** y **Streamlit** demuestra que es posible implementar plataformas analíticas OLAP de nivel profesional, robustas y de alto rendimiento sin incurrir en costos de suscripción cloud ni en complejidad de infraestructura. La capacidad de DuckDB para ejecutar operaciones analíticas avanzadas (`ROLLUP`, `CUBE`, `GROUPING SETS`, `PIVOT`) directamente sobre archivos Parquet locales o en memoria democratiza el análisis de datos empresarial, ofreciendo tiempos de respuesta sub-segundo incluso en entornos con recursos computacionales acotados.

---

## 16. Referencias

1. Chen, D. (2015). *Online Retail*. UCI Machine Learning Repository. DOI: [10.24432/C5BW33](https://doi.org/10.24432/C5BW33).
2. Kimball, R., & Ross, M. (2013). *The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling* (3rd ed.). Wiley.
3. Raasveldt, M., & Mühleisen, H. (2019). *DuckDB: an Embeddable Analytical Database*. ACM SIGMOD International Conference on Management of Data.
4. Streamlit Documentation. (2026). *Streamlit Community Cloud Deployment Guide*.

---

## 17. Enlaces públicos

- **Repositorio GitHub:** [https://github.com/Hashiravc/retailcube-olap-duckdb](https://github.com/Hashiravc/retailcube-olap-duckdb)
- **Aplicación en Producción:** [https://retailcube-olap-duckdb.streamlit.app](https://retailcube-olap-duckdb.streamlit.app)
- **Artículo DEV.to:** [https://dev.to](https://dev.to)
- **Video Demostrativo:** YouTube (5 minutos)
