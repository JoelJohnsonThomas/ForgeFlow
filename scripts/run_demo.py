"""Demo script — triggers a full sales ops workflow run via the API.

Usage:
  python scripts/run_demo.py                   # Uses "Acme Corp"
  python scripts/run_demo.py "Stripe"          # Specify company
  python scripts/run_demo.py "Stripe" approve  # Auto-approve the proposal
"""

from __future__ import annotations

import asyncio
import os
import sys

import httpx

API_URL = "http://localhost:8000"

# Windows consoles default to cp1252 and choke on the ▶/✓ glyphs below.
# Force UTF-8 so the demo runs cross-platform without PYTHONUTF8=1.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass


def _json_or_text(resp: httpx.Response):
    """Approve/reject may return a non-JSON body on error (e.g. a bare 500).
    Don't let response parsing mask the real status."""
    try:
        return resp.json()
    except ValueError:
        return {"status_code": resp.status_code, "body": resp.text[:200]}


async def _mint_token(client: httpx.AsyncClient, user_id: str) -> str:
    """Obtain a demo JWT. Falls back to FORGEFLOW_TOKEN env if /auth/login
    is disabled (DEV_LOGIN_ENABLED=false in prod-shaped setups)."""
    explicit = os.environ.get("FORGEFLOW_TOKEN")
    if explicit:
        return explicit

    password = os.environ.get("DEV_LOGIN_PASSWORD")
    if not password:
        raise SystemExit(
            "FORGEFLOW_TOKEN or DEV_LOGIN_PASSWORD must be set in the env to "
            "run the demo. See SECURITY_AUDIT.md C-3."
        )
    resp = await client.post(
        f"{API_URL}/auth/login",
        json={"user_id": user_id, "password": password},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


async def run_demo(company: str = "Acme Corp", auto_approve: bool = False) -> None:
    print(f"\n{'='*60}")
    print(f" ForgeFlow Demo — Processing: {company}")
    print(f"{'='*60}\n")

    async with httpx.AsyncClient(timeout=120) as client:
        rep_token = await _mint_token(client, "rep-1")
        mgr_token = await _mint_token(client, "manager-1")
        rep_hdr = {"Authorization": f"Bearer {rep_token}"}
        mgr_hdr = {"Authorization": f"Bearer {mgr_token}"}
        # 1. Trigger workflow
        print("▶ Triggering sales ops workflow...")
        resp = await client.post(
            f"{API_URL}/workflows/run",
            json={"lead_data": {"company_name": company}, "workflow_type": "sales_ops"},
            headers=rep_hdr,
        )

        if resp.status_code != 200:
            print(f"✗ Failed: {resp.status_code} — {resp.text}")
            return

        result = resp.json()
        run_id = result["run_id"]
        thread_id = result["thread_id"]
        status = result["status"]

        print("✓ Run started")
        print(f"  Run ID:    {run_id}")
        print(f"  Thread ID: {thread_id}")
        print(f"  Status:    {status}")

        # 2. Wait and check status
        print("\n⏳ Waiting for workflow to complete...")
        for _ in range(30):
            await asyncio.sleep(2)
            status_resp = await client.get(
                f"{API_URL}/workflows/{run_id}",
                headers=rep_hdr,
            )
            if status_resp.status_code == 200:
                state = status_resp.json()
                print(f"  Stage: {state.get('current_stage', '?')} | Status: {state.get('status', '?')}")
                if state.get("status") in ("completed", "rejected", "pending_approval"):
                    break

        # 3. Handle approval if needed
        if status == "pending_approval" or state.get("status") == "pending_approval":
            print("\n⏸  Workflow paused for human approval")

            pending_resp = await client.get(
                f"{API_URL}/approvals/pending",
                headers=mgr_hdr,
            )
            pending = pending_resp.json()

            if pending:
                token = pending[0]["token"]
                payload = pending[0]["payload"]
                print(f"\n📋 Proposal for {company}:")
                print(f"  Summary: {str(payload.get('executive_summary', 'N/A'))[:200]}...")

                if auto_approve:
                    print("\n✅ Auto-approving proposal...")
                    approve_resp = await client.post(
                        f"{API_URL}/approvals/{token}/approve",
                        json={"note": "Approved via demo script"},
                        headers=mgr_hdr,
                    )
                    if approve_resp.status_code != 200:
                        print(f"  ✗ Approve failed: {approve_resp.status_code} — "
                              f"{approve_resp.text[:200]}")
                    else:
                        print(f"  Result: {_json_or_text(approve_resp)}")
                else:
                    print(f"\n  To approve: POST {API_URL}/approvals/{token}/approve")
                    print(f"  To reject:  POST {API_URL}/approvals/{token}/reject")

        # 4. Show metrics
        metrics_resp = await client.get(f"{API_URL}/metrics/")
        if metrics_resp.status_code == 200:
            metrics = metrics_resp.json()
            print("\n📊 System Metrics:")
            print(f"  Total runs:    {metrics.get('total_runs', 0)}")
            print(f"  Success rate:  {metrics.get('success_rate', 0):.1%}")
            print(f"  Avg cost/run:  ${metrics.get('avg_cost_usd', 0):.4f}")

        print("\n✓ Demo complete! View dashboard at http://localhost:8501")


if __name__ == "__main__":
    company = sys.argv[1] if len(sys.argv) > 1 else "Acme Corp"
    auto_approve = len(sys.argv) > 2 and sys.argv[2].lower() == "approve"
    asyncio.run(run_demo(company, auto_approve))
