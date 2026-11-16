-- ============================================================================
-- Operacion OLAP: DRILL-DOWN (Bajar en la jerarquia dimensional)
-- Descripcion: Desglosar ventas desde el nivel macro (Anio/Trimestre)
--              hacia el nivel detallado (Mes, Dia) para un periodo especifico
-- Motor: DuckDB
-- ============================================================================

-- Consulta parametrizable para explorar el detalle temporal de un anio/trimestre especifico
SELECT
    f.anio,
    f.nombre_trimestre,
    f.nombre_mes,
    f.dia,
    f.nombre_dia_semana,
    COUNT(DISTINCT v.numero_factura) AS total_transacciones,
    COUNT(DISTINCT v.id_cliente) AS total_clientes,
    SUM(v.cantidad) AS unidades_vendidas,
    ROUND(SUM(v.monto_total), 2) AS ventas_netas,
    ROUND(SUM(v.monto_total) / NULLIF(COUNT(DISTINCT v.numero_factura), 0), 2) AS ticket_promedio
FROM fact_ventas v
JOIN dim_fecha f ON v.id_fecha = f.id_fecha
WHERE f.anio = 2011 AND f.trimestre = 4
GROUP BY f.anio, f.nombre_trimestre, f.mes, f.nombre_mes, f.dia, f.nombre_dia_semana
ORDER BY f.mes, f.dia;
