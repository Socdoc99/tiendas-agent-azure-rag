# Semantic views

**Status: IMPLEMENTED.**

- `ventas`: monetary totals, ticket counts, average ticket, and time comparisons.
- `venta_lineas`: historical products, units sold, categories, and line sales values.
- `productos`: current inventory, minimum stock, prices, and catalog state.

**Never mix semantic views in one logical query.** Ask separate `query_database` calls when a question spans different grains. Trusted physical joins internal to a view are governed by its definition.

Detailed definitions and business rules are in [docs/SEMANTIC_MODEL.md](../../docs/SEMANTIC_MODEL.md).
