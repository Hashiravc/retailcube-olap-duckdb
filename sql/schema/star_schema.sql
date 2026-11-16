-- ============================================================================
-- RetailCube Analytics - Star Schema DDL (Esquema Estrella)
-- Motor: DuckDB
-- Descripcion: Definicion del modelo dimensional para analisis OLAP
-- ============================================================================

-- 1. Dimension Fecha
CREATE TABLE IF NOT EXISTS dim_fecha (
    id_fecha INTEGER PRIMARY KEY,           -- Formato numerico YYYYMMDD
    fecha DATE NOT NULL,
    anio INTEGER NOT NULL,
    trimestre INTEGER NOT NULL,
    nombre_trimestre VARCHAR NOT NULL,      -- Ej: 'T1', 'T2'
    mes INTEGER NOT NULL,
    nombre_mes VARCHAR NOT NULL,            -- Ej: 'Enero', 'Febrero'
    dia INTEGER NOT NULL,
    dia_semana INTEGER NOT NULL,            -- 1 (Lunes) a 7 (Domingo)
    nombre_dia_semana VARCHAR NOT NULL,     -- Ej: 'Lunes', 'Martes'
    es_fin_de_semana BOOLEAN NOT NULL,
    anio_mes VARCHAR NOT NULL               -- Ej: '2011-03'
);

-- 2. Dimension Producto
CREATE TABLE IF NOT EXISTS dim_producto (
    id_producto INTEGER PRIMARY KEY,        -- Clave sustituta (Surrogate Key)
    codigo_stock VARCHAR NOT NULL UNIQUE,   -- Clave natural del catalogo
    descripcion VARCHAR NOT NULL,
    categoria VARCHAR NOT NULL,             -- Segmento general derivado
    precio_unitario_referencia DOUBLE NOT NULL
);

-- 3. Dimension Cliente
CREATE TABLE IF NOT EXISTS dim_cliente (
    id_cliente INTEGER PRIMARY KEY,         -- -1 para cliente anonimo/invitado
    codigo_cliente VARCHAR NOT NULL,        -- 'CLI-XXXXX' o 'INVITADO'
    tipo_cliente VARCHAR NOT NULL,          -- 'REGISTRADO' o 'INVITADO'
    pais_origen VARCHAR NOT NULL
);

-- 4. Dimension Pais
CREATE TABLE IF NOT EXISTS dim_pais (
    id_pais INTEGER PRIMARY KEY,            -- Clave sustituta
    nombre_pais VARCHAR NOT NULL UNIQUE,    -- Clave natural
    codigo_iso VARCHAR NOT NULL,            -- Codigo ISO 2 o 3 letras
    region VARCHAR NOT NULL                 -- Region geografica analitica
);

-- 5. Tabla de Hechos: fact_ventas
-- Granularidad: Una fila por linea de transaccion comercial valida
CREATE TABLE IF NOT EXISTS fact_ventas (
    id_venta BIGINT PRIMARY KEY,            -- Clave primaria sustituta
    numero_factura VARCHAR NOT NULL,        -- Codigo de factura (Transaccion)
    id_fecha INTEGER NOT NULL REFERENCES dim_fecha(id_fecha),
    id_producto INTEGER NOT NULL REFERENCES dim_producto(id_producto),
    id_cliente INTEGER NOT NULL REFERENCES dim_cliente(id_cliente),
    id_pais INTEGER NOT NULL REFERENCES dim_pais(id_pais),
    hora_transaccion VARCHAR NOT NULL,      -- HH:MM:SS
    cantidad INTEGER NOT NULL,              -- Positivo en compras, negativo en devoluciones
    precio_unitario DOUBLE NOT NULL,        -- Precio unitario en GBP (£)
    monto_total DOUBLE NOT NULL,            -- cantidad * precio_unitario (Ventas netas)
    monto_bruto DOUBLE NOT NULL,            -- GREATEST(monto_total, 0)
    monto_cancelacion DOUBLE NOT NULL,      -- ABS(LEAST(monto_total, 0))
    es_cancelacion BOOLEAN NOT NULL,        -- TRUE si es devolucion/cancelacion
    tipo_transaccion VARCHAR NOT NULL       -- 'VENTA_REGULAR' o 'CANCELACION'
);

-- Indices analiticos para acelerar joins y filtros dimensionales en DuckDB
CREATE INDEX IF NOT EXISTS idx_fact_fecha ON fact_ventas(id_fecha);
CREATE INDEX IF NOT EXISTS idx_fact_producto ON fact_ventas(id_producto);
CREATE INDEX IF NOT EXISTS idx_fact_cliente ON fact_ventas(id_cliente);
CREATE INDEX IF NOT EXISTS idx_fact_pais ON fact_ventas(id_pais);
CREATE INDEX IF NOT EXISTS idx_fact_factura ON fact_ventas(numero_factura);
