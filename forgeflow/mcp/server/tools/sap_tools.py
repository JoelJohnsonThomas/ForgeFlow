"""MCP tools wrapping SAP S/4HANA OData APIs."""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from forgeflow.connectors.sap import SAPConnector

logger = logging.getLogger(__name__)
router = FastMCP("sap-tools")


def _client() -> SAPConnector:
    return SAPConnector()


@router.tool()
async def sap_get_sales_order(sales_order_id: str) -> dict:
    """Fetch a sales order from S/4HANA by SalesOrder ID."""
    return await _client().get_sales_order(sales_order_id)


@router.tool()
async def sap_search_sales_orders(
    filter_expr: str | None = None, top: int = 25, expand: str | None = None
) -> dict:
    """Search sales orders using OData v2 $filter syntax.

    Example: filter_expr="SalesOrderType eq 'OR' and CreationDate ge datetime'2026-01-01T00:00:00'"
    """
    return await _client().search_sales_orders(
        filter_expr=filter_expr, top=top, expand=expand
    )


@router.tool()
async def sap_get_business_partner(bp_id: str) -> dict:
    """Fetch a business partner (customer / supplier) by BusinessPartner ID."""
    return await _client().get_business_partner(bp_id)


@router.tool()
async def sap_search_business_partners(
    filter_expr: str | None = None, top: int = 25
) -> dict:
    """Search business partners with OData filter syntax."""
    return await _client().search_business_partners(filter_expr=filter_expr, top=top)


@router.tool()
async def sap_get_supplier_invoice(invoice_id: str, fiscal_year: str) -> dict:
    """Fetch a supplier invoice. SAP keys these by (SupplierInvoice, FiscalYear)."""
    return await _client().get_supplier_invoice(invoice_id, fiscal_year)


@router.tool()
async def sap_search_supplier_invoices(
    filter_expr: str | None = None, top: int = 25
) -> dict:
    """List supplier invoices matching an OData filter."""
    return await _client().search_supplier_invoices(filter_expr=filter_expr, top=top)


@router.tool()
async def sap_query_entity_set(
    service: str,
    entity_set: str,
    filter_expr: str | None = None,
    top: int = 25,
    select: str | None = None,
) -> dict:
    """Generic OData reader for any S/4HANA service.

    Example:
      service='API_PURCHASEORDER_PROCESS_SRV'
      entity_set='A_PurchaseOrder'
      filter_expr="PurchaseOrderType eq 'NB'"
    """
    return await _client().query_entity_set(
        service=service, entity_set=entity_set, filter_expr=filter_expr,
        top=top, select=select,
    )
