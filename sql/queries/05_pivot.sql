-- ============================================================================
-- Operacion OLAP: PIVOT (Rotacion de ejes dimensionales)
-- Descripcion: Reorganizar una dimension en columnas para cruzar medidas
--              (ej. Paises en filas y Periodos trimestrales en columnas)
-- Motor: DuckDB (Sintaxis nativa PIVOT)
-- ============================================================================

PIVOT (
    SELECT
        p.nombre_pais,
        f.anio || '-' || f.nombre_trimestre AS periodo,
        v.monto_total
    FROM fact_ventas v
    JOIN dim_pais p ON v.id_pais = p.id_pais
    JOIN dim_fecha f ON v.id_fecha = f.id_fecha
    WHERE p.nombre_pais IN ('United Kingdom', 'Germany', 'France', 'EIRE', 'Spain', 'Netherlands', 'Belgium', 'Switzerland')
)
ON periodo
USING ROUND(SUM(monto_total), 2)
GROUP BY nombre_pais
ORDER BY nombre_pais;
