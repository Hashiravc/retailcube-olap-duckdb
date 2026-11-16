-- ============================================================================
-- Operacion OLAP: SLICE (Corte unidimensional)
-- Descripcion: Fijar una dimension a un unico valor especifico (ej. Pais = 'Germany')
--              y proyectar las medidas sobre las dimensiones restantes
-- Motor: DuckDB
-- ============================================================================

SELECT
    p.nombre_pais,
    f.anio_mes,
    pr.categoria,
    COUNT(DISTINCT v.numero_factura) AS total_transacciones,
    COUNT(DISTINCT v.id_cliente) AS clientes_activos,
    SUM(v.cantidad) AS unidades_vendidas,
    ROUND(SUM(v.monto_total), 2) AS ventas_netas,
    ROUND(SUM(v.monto_cancelacion), 2) AS total_devoluciones,
    ROUND(SUM(v.monto_total) / NULLIF(COUNT(DISTINCT v.numero_factura), 0), 2) AS ticket_promedio
FROM fact_ventas v
JOIN dim_pais p ON v.id_pais = p.id_pais
JOIN dim_fecha f ON v.id_fecha = f.id_fecha
JOIN dim_producto pr ON v.id_producto = pr.id_producto
WHERE p.nombre_pais = 'Germany'
GROUP BY p.nombre_pais, f.anio_mes, pr.categoria
ORDER BY f.anio_mes, ventas_netas DESC;
