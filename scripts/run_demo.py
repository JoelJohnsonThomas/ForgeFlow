"""Demo script — triggers a full sales ops workflow run via the API.

Usage:
  python scripts/run_demo.py                   # Uses "Acme Corp"
  python scripts/run_demo.py "Stripe"          # Specify company
  python scripts/run_demo.py "Stripe" approve  # Auto-approve the proposal
"""

from __future__ import annotations

import asyncio
import sys

import httpx

API_URL = "http://localhost:8000"


async def run_demo(company: str = "Acme Corp", auto_approve: bool = False) -> None:
    print(f"\n{'='*60}")
    print(f" ForgeFlow Demo — Processing: {company}")
    print(f"{'='*60}\n")

    async with httpx.AsyncClient(timeout=120) as client:
        # 1. Trigger workflow
        print("▶ Triggering sales ops workflow...")
        resp = await client.post(
            f"{API_URL}/workflows/run",
            json={"lead_data": {"company_name": company}, "workflow_type": "sales_ops"},
            headers={"X-Role": "sales_rep", "X-User-Id": "demo-user"},
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
                headers={"X-Role": "sales_rep"},
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
                headers={"X-Role": "manager"},
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
                        headers={"X-Role": "manager"},
                    )
                    print(f"  Result: {approve_resp.json()}")
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
