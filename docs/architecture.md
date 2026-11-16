# Arquitectura del Sistema: RetailCube Analytics

## 1. Visión General
**RetailCube Analytics** es una plataforma analítica OLAP (Online Analytical Processing) moderna de alto rendimiento, diseñada bajo principios de arquitectura desacoplada, almacenamiento columnar y procesamiento in-process con software libre.

```mermaid
flowchart TD
    subgraph S1["1. Fuente de Datos Oficial"]
        UCI["UCI Machine Learning Repository<br/>Online Retail (Chen, 2015)<br/>541,909 transacciones"]
    end

    subgraph S2["2. Pipeline de Ingestión y Calidad (Python)"]
        DL["download_and_ingest.py<br/>- Auditoría de esquema<br/>- Clasificación de devoluciones<br/>- Imputación cliente invitado (-1)"]
        PQ_RAW["clean_retail_transactions.parquet<br/>(4.18 MB)"]
    end

    subgraph S3["3. Capa de Modelado Dimensional"]
        BUILD["build_star_schema.py<br/>Generación de Claves Sustitutas<br/>y Jerarquías"]
        DFECHA["dim_fecha.parquet<br/>(305 fechas)"]
        DPROD["dim_producto.parquet<br/>(3,938 productos)"]
        DCUST["dim_cliente.parquet<br/>(4,372 clientes)"]
        DPAIS["dim_pais.parquet<br/>(38 países)"]
        FVENT["fact_ventas.parquet<br/>(539,392 hechos)"]
    end

    subgraph S4["4. Motor Analítico OLAP"]
        DUCK["DuckDB In-Process Engine<br/>- Vectorized Execution<br/>- Parquet Zero-Copy Querying<br/>- CUBE, ROLLUP, PIVOT, GROUPING SETS"]
    end

    subgraph S5["5. Capa de Presentación (SaaS)"]
        APP["Streamlit Community Cloud<br/>Dashboard Interactivo & Plotly"]
    end

    UCI -->|HTTP Stream| DL
    DL --> PQ_RAW
    PQ_RAW --> BUILD
    BUILD --> DFECHA
    BUILD --> DPROD
    BUILD --> DCUST
    BUILD --> DPAIS
    BUILD --> FVENT
    DFECHA --> DUCK
    DPROD --> DUCK
    DCUST --> DUCK
    DPAIS --> DUCK
    FVENT --> DUCK
    DUCK --> APP
```

---

## 2. Decisiones de Arquitectura

### 2.1 ¿Por qué DuckDB en lugar de un RDBMS tradicional o Cloud Data Warehouse?
1. **Motor Columnar In-Process:** DuckDB opera dentro del mismo proceso que la aplicación Python/Streamlit, eliminando la latencia de red de los sockets cliente-servidor (PostgreSQL/MySQL) y evitando costos de infraestructura de servicios cloud como AWS Redshift o Snowflake.
2. **Ejecución Vectorizada:** Utiliza el modelo de ejecución vectorial Morsel-driven, procesando bloques de datos en registros SIMD de la CPU.
3. **Integración Nativa con Apache Parquet:** Puede escanear y filtrar Parquet con proyección de columnas y "predicate pushdown" directamente desde disco o memoria sin deserialización intermedia.
4. **Soporte SQL Estándar Completo para OLAP:** Dispone de sintaxis nativa para operaciones analíticas avanzadas: `ROLLUP`, `CUBE`, `GROUPING SETS` y `PIVOT`.

---

## 3. Esquema Dimensional (Star Schema)

El diseño sigue las metodologías de Ralph Kimball para Data Warehousing empresarial:

```mermaid
erDiagram
    fact_ventas }|..|| dim_fecha : "id_fecha"
    fact_ventas }|..|| dim_producto : "id_producto"
    fact_ventas }|..|| dim_cliente : "id_cliente"
    fact_ventas }|..|| dim_pais : "id_pais"

    fact_ventas {
        bigint id_venta PK "Surrogate Key"
        varchar numero_factura "Código natural factura"
        int id_fecha FK "YYYYMMDD"
        int id_producto FK "Clave producto"
        int id_cliente FK "Clave cliente (-1 = invitado)"
        int id_pais FK "Clave país"
        varchar hora_transaccion "HH:MM:SS"
        int cantidad "Métrica aditiva"
        double precio_unitario "GBP"
        double monto_total "Ventas netas"
        double monto_bruto "Ventas brutas"
        double monto_cancelacion "Devoluciones"
        boolean es_cancelacion "Flag booleano"
        varchar tipo_transaccion "VENTA_REGULAR / CANCELACION"
    }

    dim_fecha {
        int id_fecha PK "YYYYMMDD"
        date fecha "Fecha calendario"
        int anio "Año"
        int trimestre "1..4"
        varchar nombre_trimestre "T1..T4"
        int mes "1..12"
        varchar nombre_mes "Enero..Diciembre"
        int dia "1..31"
        int dia_semana "1..7"
        varchar nombre_dia_semana "Lunes..Domingo"
        boolean es_fin_de_semana
        varchar anio_mes "YYYY-MM"
    }

    dim_producto {
        int id_producto PK "Surrogate Key"
        varchar codigo_stock UK "StockCode original"
        varchar descripcion "Descripción depurada"
        varchar categoria "Segmento de mercado"
        double precio_unitario_referencia "Mediana de precio"
    }

    dim_cliente {
        int id_cliente PK "-1 = Cliente Invitado"
        varchar codigo_cliente "CLI-XXXX o INVITADO"
        varchar tipo_cliente "REGISTRADO / INVITADO"
        varchar pais_origen "País predominante"
    }

    dim_pais {
        int id_pais PK "Surrogate Key"
        varchar nombre_pais UK "Nombre oficial"
        varchar codigo_iso "ISO 3166-1 alfa-2"
        varchar region "Región geográfica analítica"
    }
```

---

## 4. Reglas de Negocio e Integridad Analítica

1. **Granularidad Explícita:** Cada registro en `fact_ventas` representa una línea transaccional de una factura.
2. **Tratamiento de Clientes Invitados / No Registrados:** El 24.9% de las transacciones del dataset carecen de `CustomerID`. En lugar de descartarlas (lo que destruiría las métricas de ingresos globales), se asignan al cliente dimensional sustituto `id_cliente = -1`, preservando el 100% de la facturación y la integridad referencial.
3. **Manejo de Devoluciones y Cancelaciones:** Las facturas que comienzan con 'C' o cantidades negativas se clasifican con `es_cancelacion = TRUE`. Se generan medidas independientes:
   - $Ventas\_Brutas = \max(monto\_total, 0)$
   - $Monto\_Cancelacion = |\min(monto\_total, 0)|$
   - $Ventas\_Netas = Ventas\_Brutas - Monto\_Cancelacion$
4. **Métricas No Aditivas:**
   - El *Ticket Promedio* nunca se calcula promediando la columna `monto_total`. Se evalúa como:
     $$\text{Ticket Promedio} = \frac{\sum monto\_total}{\text{COUNT(DISTINCT } numero\_factura)}$$
