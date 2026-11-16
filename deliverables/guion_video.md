# Guion Técnico del Video Demostrativo: RetailCube Analytics

## Metadatos para Publicación en YouTube
- **Título Sugerido:**  
  `RetailCube Analytics: Solución OLAP con DuckDB, Python y Streamlit (Demo Completa)`
- **Título Alternativo:**  
  `Construyendo un Motor OLAP con DuckDB, Parquet y Streamlit | Proyecto Académico`
- **Duración Máxima:** 5:00 minutos
- **Resolución Recomendada:** 1080p a 60 FPS
- **Idioma de Narración:** Español

### Descripción para YouTube:
```text
Demostración técnica de RetailCube Analytics, una plataforma analítica completa de Procesamiento Analítico en Línea (OLAP) desarrollada con DuckDB, Apache Parquet, Python y Streamlit sobre el dataset histórico oficial de UCI Online Retail (539,392 transacciones).

En este video de 5 minutos explicamos:
0:00 - Presentación del problema analítico y objetivos
0:30 - Arquitectura desacoplada y Modelo Estrella (Star Schema)
1:00 - Demostración de operaciones OLAP: Roll-up, Drill-down, Slice, Dice y Pivot
2:15 - Agregaciones avanzadas con SQL nativo: CUBE y GROUPING SETS en DuckDB
3:00 - Automatización CI/CD con GitHub Actions y control de calidad
3:40 - Demostración en vivo de la aplicación desplegada en Streamlit Community Cloud
4:30 - Resultados de rendimiento, conclusiones y software libre

🔗 Repositorio GitHub: https://github.com/Hashiravc/retailcube-olap-duckdb
🌐 Dashboard en Vivo: https://retailcube-olap-duckdb.streamlit.app
📝 Artículo en DEV.to: https://dev.to

#DataEngineering #OLAP #DuckDB #Python #Streamlit #DataWarehouse #SQL
```

---

## Estructura y Guion Minuto a Minuto

```
+---------------+--------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Minuto        | Pantalla / Escena                    | Locución y Puntos Clave                                                                                                                                                                                                                  |
+---------------+--------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| 0:00 - 0:30   | Diapositiva de Portada / Dashboard   | "Hola a todos. Bienvenidos a la presentación de RetailCube Analytics. En este proyecto abordamos el desafío de analizar más de medio millón de transacciones históricas de comercio electrónico sin recurrir a costosos servicios cloud..." |
| 0:30 - 1:00   | Diagrama de Arquitectura y Mermaid   | "Nuestra arquitectura se basa en software libre. Ingerimos los datos de UCI Online Retail, limpiamos cancelaciones y clientes no registrados, y construimos un Esquema Estrella formal con Ralph Kimball..."                         |
| 1:00 - 2:15   | Sección 'Explorador OLAP' (Demo 1)   | "Pasemos a las operaciones OLAP en vivo. Primero, ROLL-UP agrega ventas en la jerarquía temporal. Luego DRILL-DOWN desciende a los días de mayor venta. Con SLICE fijamos un país, con DICE subcubos y con PIVOT matrices..."       |
| 2:15 - 3:00   | Sección 'Explorador OLAP' (Demo 2)   | "DuckDB brilla especialmente en operaciones analíticas avanzadas. Con GROUP BY CUBE generamos todas las combinaciones 2^N entre región, categoría y año. Y con GROUPING SETS calculamos agregaciones selectivas en un solo barrido..."|
| 3:00 - 3:40   | Pestaña de GitHub Actions / Código   | "La calidad está asegurada mediante dos flujos automatizados en GitHub Actions: un pipeline de CI que valida 17 pruebas con pytest, y un pipeline de datos que genera los archivos Parquet evitando ejecuciones infinitas..."         |
| 3:40 - 4:30   | Navegación por la App Desplegada     | "Aquí vemos la aplicación en vivo en Streamlit Community Cloud. Las tarjetas ejecutivas muestran £9.77M en ventas netas tras descontar devoluciones. El mapa geográfico y los rankings responden en menos de 50 milisegundos..."     |
| 4:30 - 5:00   | Diapositiva de Cierre & Repositorio  | "En conclusión, DuckDB y Parquet democratizan el análisis OLAP empresarial con tiempos de respuesta sub-segundo y cero costo de infraestructura. Enlaces al repositorio y artículo en la descripción. ¡Muchas gracias!"               |
+---------------+--------------------------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
```

---

## Consultas SQL Específicas a Mostrar en Pantalla

### 1. ROLL-UP (1:10)
```sql
SELECT f.anio, f.nombre_trimestre, f.nombre_mes,
       ROUND(SUM(v.monto_total), 2) AS ventas_netas
FROM fact_ventas v
JOIN dim_fecha f ON v.id_fecha = f.id_fecha
GROUP BY ROLLUP (f.anio, f.nombre_trimestre, f.nombre_mes);
```

### 2. PIVOT Nativo en DuckDB (2:00)
```sql
PIVOT (
    SELECT p.nombre_pais, f.anio || '-' || f.nombre_trimestre AS periodo, v.monto_total
    FROM fact_ventas v
    JOIN dim_pais p ON v.id_pais = p.id_pais
    JOIN dim_fecha f ON v.id_fecha = f.id_fecha
) ON periodo USING ROUND(SUM(monto_total), 2)
GROUP BY nombre_pais;
```

### 3. CUBE Multidimensional (2:30)
```sql
SELECT p.region, pr.categoria, f.anio, ROUND(SUM(v.monto_total), 2) AS ventas_netas
FROM fact_ventas v
JOIN dim_pais p ON v.id_pais = p.id_pais
JOIN dim_producto pr ON v.id_producto = pr.id_producto
JOIN dim_fecha f ON v.id_fecha = f.id_fecha
GROUP BY CUBE (p.region, pr.categoria, f.anio);
```
