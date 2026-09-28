# Semantic model

The only logical views authorized for the initial POS MVP are `ventas`, `venta_lineas`, and `productos`. Their definitions are imported from the validated TiendasON prototype and are the source of truth for query semantics. Do not infer permissions from physical table names.

## `ventas`

**Grain:** one row per active ticket belonging to the authorized establishment.

Use for total sales, ticket count, average ticket, and time comparisons. Total sales are `SUM(total_facturado)`; tickets are `COUNT(*)`; average ticket is `SUM(total_facturado) / NULLIF(COUNT(*), 0)`. Do not reconstruct ticket totals from sale lines. Use the business `fecha` (`SalesDate`), not `CreatedAt`.

## `venta_lineas`

**Grain:** one row per sold product line.

Use for product/category rankings, units, and line sales value. The trusted view follows `SaleDetail -> Sale -> PointOfSale -> Establishment`, and joins catalog details within the establishment/business scope. Physical joins inside the trusted view are allowed; logical joins to another semantic view are not.

## `productos`

**Grain:** one row per active current product at the authorized establishment.

Use for current price, stock, minimum stock, and current catalog metadata. Inventory is controlled only when `controla_inventario = 1`.

- Out of stock: controlled product and `stock_actual <= 0`.
- Negative stock: controlled product and `stock_actual < 0`.
- Below minimum: controlled product, `stock_actual > 0`, and `stock_actual <= stock_minimo`.
- A zero stock value is not an alert when inventory control is disabled.

Do not use current product cost to calculate historical profit or margin. Historical profit, margin, payments, returns, purchases, suppliers, receivables, credit, and employee attribution are outside the approved contract.

## Dates and tenant scope

Business timezone is `America/Bogota`. Relative periods are resolved server-side in that timezone. Use half-open ranges: `fecha >= inicio AND fecha < fin`.

The server constructs an immutable `TenantContext` containing `business_id`, `establishment_id`, and `timezone`. Validate that the establishment belongs to the business. Every physical semantic definition applies both IDs through bound parameters. The model and browser never select or override them.

## Query contract

Each logical statement may reference exactly one distinct semantic view. The validator rejects physical tables/schemas, unknown views, multiple statements, DDL/DML, external access, and system metadata queries. The compiler injects one trusted view as a CTE and tenant parameters. Results use `SQL_MAX_ROWS` (default 200), fetch `max_rows + 1`, and set `truncated` when needed.
