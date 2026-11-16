-- ============================================================================
-- Operacion OLAP: CUBE (Generacion de todas las combinaciones dimensionales)
-- Descripcion: Agregacion multidimensional completa (2^N agrupaciones)
--              sobre Region geografica, Categoria de producto y Anio
-- Motor: DuckDB (Sintaxis nativa GROUP BY CUBE)
-- ============================================================================

SELECT
    COALESCE(p.region, '--- TODAS LAS REGIONES ---') AS region,
    COALESCE(pr.categoria, '--- TODAS LAS CATEGORIAS ---') AS categoria,
    COALESCE(CAST(f.anio AS VARCHAR), '--- TODOS LOS ANIOS ---') AS anio,
    COUNT(DISTINCT v.numero_factura) AS total_transacciones,
    COUNT(DISTINCT v.id_cliente) AS total_clientes,
    SUM(v.cantidad) AS unidades_vendidas,
    ROUND(SUM(v.monto_total), 2) AS ventas_netas,
    ROUND(SUM(v.monto_cancelacion), 2) AS devoluciones,
    ROUND(SUM(v.monto_total) / NULLIF(COUNT(DISTINCT v.numero_factura), 0), 2) AS ticket_promedio
FROM fact_ventas v
JOIN dim_pais p ON v.id_pais = p.id_pais
JOIN dim_producto pr ON v.id_producto = pr.id_producto
JOIN dim_fecha f ON v.id_fecha = f.id_fecha
WHERE p.region IN ('Reino Unido', 'Europa Occidental', 'Escandinavia')
GROUP BY CUBE (p.region, pr.categoria, f.anio)
ORDER BY
    p.region NULLS LAST,
    pr.categoria NULLS LAST,
    f.anio NULLS LAST;
