-- ============================================================================
-- Operacion OLAP: ROLL-UP (Subir en la jerarquia dimensional)
-- Descripcion: Agregacion de ventas a traves de la jerarquia temporal
--              Dia -> Mes -> Trimestre -> Anio
-- Motor: DuckDB
-- ============================================================================

SELECT
    f.anio,
    f.nombre_trimestre,
    f.nombre_mes,
    f.fecha,
    COUNT(DISTINCT v.numero_factura) AS total_transacciones,
    COUNT(DISTINCT v.id_cliente) AS total_clientes,
    SUM(v.cantidad) AS unidades_vendidas,
    ROUND(SUM(v.monto_total), 2) AS ventas_netas,
    ROUND(SUM(v.monto_bruto), 2) AS ventas_brutas,
    ROUND(SUM(v.monto_cancelacion), 2) AS cancelaciones,
    ROUND(SUM(v.monto_total) / NULLIF(COUNT(DISTINCT v.numero_factura), 0), 2) AS ticket_promedio
FROM fact_ventas v
JOIN dim_fecha f ON v.id_fecha = f.id_fecha
GROUP BY ROLLUP (f.anio, f.nombre_trimestre, f.nombre_mes, f.fecha)
ORDER BY
    f.anio NULLS LAST,
    f.nombre_trimestre NULLS LAST,
    f.nombre_mes NULLS LAST,
    f.fecha NULLS LAST;
