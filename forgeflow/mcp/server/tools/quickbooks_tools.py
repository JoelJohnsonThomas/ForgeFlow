"""MCP tools wrapping QuickBooks Online — used by finance_recon."""

from __future__ import annotations

import logging
from typing import Any

from fastmcp import FastMCP

from forgeflow.connectors.quickbooks import QuickBooksConnector

logger = logging.getLogger(__name__)
router = FastMCP("quickbooks-tools")


def _client() -> QuickBooksConnector:
    return QuickBooksConnector()


@router.tool()
async def quickbooks_query(sql: str) -> dict:
    """Run a QBO query (SQL-like syntax).

    Examples:
      "select * from Customer where Active=true MAXRESULTS 50"
      "select * from Invoice where MetaData.CreateTime >= '2026-01-01' MAXRESULTS 100"
    """
    return await _client().query(sql)


@router.tool()
async def quickbooks_create_customer(
    display_name: str,
    primary_email: str | None = None,
    company_name: str | None = None,
) -> dict:
    """Create a QBO customer record."""
    return await _client().create_customer(
        display_name=display_name,
        primary_email=primary_email,
        company_name=company_name,
    )


@router.tool()
async def quickbooks_get_customer(customer_id: str) -> dict:
    """Fetch a QBO customer by Id."""
    return await _client().get_customer(customer_id)


@router.tool()
async def quickbooks_create_invoice(
    customer_id: str,
    line_items: list[dict[str, Any]],
    txn_date: str | None = None,
    due_date: str | None = None,
    memo: str | None = None,
) -> dict:
    """Create an invoice with line items.

    Each line_item must include Amount, DetailType, and SalesItemLineDetail
    with ItemRef.value pointing to a QBO Item ID.
    """
    return await _client().create_invoice(
        customer_id=customer_id,
        line_items=line_items,
        txn_date=txn_date,
        due_date=due_date,
        memo=memo,
    )


@router.tool()
async def quickbooks_list_accounts(account_type: str | None = None) -> dict:
    """List Chart of Accounts. Filter by AccountType (Bank, Income, Expense, etc.)."""
    return await _client().list_accounts(account_type=account_type)


@router.tool()
async def quickbooks_create_journal_entry(
    lines: list[dict[str, Any]],
    txn_date: str | None = None,
    private_note: str | None = None,
) -> dict:
    """Post a journal entry. Debit lines must equal credit lines in total amount.

    Used by the finance_recon workflow to post adjusting entries after a
    reconciliation has been approved.
    """
    return await _client().create_journal_entry(
        lines=lines, txn_date=txn_date, private_note=private_note
    )
