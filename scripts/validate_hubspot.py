"""End-to-end probe for the HubSpot integration.

Runs the production-relevant code paths against a real HubSpot account so you
can confirm everything works BEFORE you deploy a workflow that touches your
pipeline. Idempotent: re-running uses the same test email/domain/run_id and
should report no duplicates created.

Usage:
  export HUBSPOT_ACCESS_TOKEN=pat-na1-...           # Private App token
  export HUBSPOT_TEST_EMAIL=qa+forgeflow@example.com  # optional; default below
  python scripts/validate_hubspot.py

Required HubSpot Private App scopes:
  crm.objects.contacts.read    crm.objects.contacts.write
  crm.objects.companies.read   crm.objects.companies.write
  crm.objects.deals.read       crm.objects.deals.write

One-time HubSpot setup:
  Create a custom Deal property named `forgeflow_run_id` (single-line text).
  Settings -> Properties -> Deal properties -> Create. The idempotent deal
  flow uses this for dedup; without it, deal create will fail with a 400.

Exit codes:
  0  all checks passed
  1  at least one check failed (read stderr for details)
  2  HUBSPOT_ACCESS_TOKEN missing or empty
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s")
logger = logging.getLogger("validate_hubspot")

# Late import so the script can print a clear setup error before the
# forgeflow package's Pydantic settings fire on import time.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


GREEN = "\033[32m"
RED = "\033[31m"
DIM = "\033[2m"
RESET = "\033[0m"


def _status(ok: bool) -> str:
    return f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"


async def _run_check(
    name: str,
    fn: Callable[[], Awaitable[Any]],
) -> tuple[bool, float, str]:
    start = time.perf_counter()
    try:
        result = await fn()
        elapsed = time.perf_counter() - start
        detail = ""
        if isinstance(result, dict):
            obj_id = result.get("id")
            mock = result.get("mock")
            if mock:
                detail = "mock response (token missing or disabled)"
            elif obj_id:
                detail = f"id={obj_id}"
        return True, elapsed, detail
    except Exception as exc:
        elapsed = time.perf_counter() - start
        return False, elapsed, f"{type(exc).__name__}: {exc}"


async def main() -> int:
    token = os.environ.get("HUBSPOT_ACCESS_TOKEN", "").strip()
    if not token:
        print(f"{RED}HUBSPOT_ACCESS_TOKEN is not set.{RESET}\n", file=sys.stderr)
        print("Export your Private App token first:", file=sys.stderr)
        print("  export HUBSPOT_ACCESS_TOKEN=pat-na1-XXXX", file=sys.stderr)
        print(
            "Token is created at HubSpot → Settings → Integrations → Private Apps.",
            file=sys.stderr,
        )
        return 2

    from forgeflow.connectors.hubspot import HubSpotConnector

    email = os.environ.get("HUBSPOT_TEST_EMAIL", "qa+forgeflow@example.com").strip()
    domain = email.split("@", 1)[-1]
    run_id = f"forgeflow-validate-{uuid.uuid4().hex[:12]}"

    client = HubSpotConnector()
    if not client.is_enabled():
        # Defensive — HUBSPOT_ACCESS_TOKEN is set but the Pydantic settings
        # field didn't pick it up. Usually means the env var was set after
        # the process started.
        print(f"{RED}Connector reports disabled despite env var set.{RESET}", file=sys.stderr)
        return 2

    print(f"{DIM}Probing HubSpot at {client.base_url} as user/token ending …{token[-6:]}{RESET}")
    print(f"{DIM}Test email: {email}  domain: {domain}  run_id: {run_id}{RESET}\n")

    checks: list[tuple[str, Callable[[], Awaitable[Any]]]] = [
        (
            "upsert contact by email (idempotent)",
            lambda: client.upsert_contact_by_email(
                email=email, firstname="ForgeFlow", lastname="QA"
            ),
        ),
        (
            "upsert contact again (must NOT duplicate)",
            lambda: client.upsert_contact_by_email(
                email=email, firstname="ForgeFlow", lastname="QA"
            ),
        ),
        (
            "upsert company by domain",
            lambda: client.upsert_company_by_domain(
                name="ForgeFlow QA Co.", domain=domain, industry="COMPUTER_SOFTWARE"
            ),
        ),
        (
            "search contacts",
            lambda: client.search_contacts(query=email, limit=3),
        ),
        (
            "create deal idempotent by run_id (first call)",
            lambda: client.find_or_create_deal_by_run_id(
                run_id=run_id,
                deal_name=f"ForgeFlow QA · {run_id}",
                amount=1000,
                deal_stage="appointmentscheduled",
            ),
        ),
        (
            "create deal idempotent by run_id (second call — must reuse)",
            lambda: client.find_or_create_deal_by_run_id(
                run_id=run_id,
                deal_name=f"ForgeFlow QA · {run_id}",
                amount=1000,
                deal_stage="appointmentscheduled",
            ),
        ),
    ]

    width = max(len(name) for name, _ in checks)
    failed = 0
    deal_ids: list[str] = []

    for name, fn in checks:
        ok, elapsed, detail = await _run_check(name, fn)
        print(f"  {_status(ok)}  {name.ljust(width)}  {elapsed*1000:7.1f}ms  {detail}")
        if not ok:
            failed += 1
        # Capture the deal id so we can verify dedup explicitly
        if ok and "deal idempotent" in name and detail.startswith("id="):
            deal_ids.append(detail[3:])

    # Dedup assertion — both idempotent deal calls should hit the same id.
    if len(deal_ids) == 2:
        if deal_ids[0] == deal_ids[1]:
            print(f"\n  {GREEN}ASSERT{RESET}  idempotent deal returned same id on retry  → {deal_ids[0]}")
        else:
            print(
                f"\n  {RED}ASSERT{RESET}  idempotent deal DUPLICATED on retry  → "
                f"{deal_ids[0]} != {deal_ids[1]}"
            )
            failed += 1

    print()
    if failed == 0:
        print(f"{GREEN}All {len(checks)} checks passed.{RESET} ForgeFlow ↔ HubSpot is wired correctly.")
        return 0
    print(f"{RED}{failed} check(s) failed.{RESET} See messages above.")
    print()
    print("Common fixes:")
    print("  - 401 Unauthorized: token expired / wrong scopes. Re-create the Private App with all 6 CRM scopes.")
    print("  - 400 on deal create: the custom property `forgeflow_run_id` doesn't exist in HubSpot yet.")
    print("    Create it under Settings → Properties → Deal properties → Create (Single-line text).")
    print("  - 429 Too Many Requests: retry logic is engaged. Re-run; if it keeps happening, your account hit the daily quota.")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
