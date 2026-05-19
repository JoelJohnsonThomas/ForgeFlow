"""Seed the database with sample leads and users for demos."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import asyncpg

SAMPLE_LEADS = [
    {"company": "Stripe", "industry": "fintech", "score": 9.1, "status": "proposed"},
    {"company": "Snowflake", "industry": "saas", "score": 8.7, "status": "qualified"},
    {"company": "Vercel", "industry": "saas", "score": 8.2, "status": "qualified"},
    {"company": "Retool", "industry": "enterprise", "score": 7.5, "status": "qualified"},
    {"company": "Linear", "industry": "saas", "score": 7.1, "status": "qualified"},
    {"company": "LocalPlumber", "industry": "other", "score": 1.2, "status": "disqualified"},
    {"company": "FamilyBakery", "industry": "other", "score": 0.8, "status": "disqualified"},
    {"company": "GrowthCo", "industry": "saas", "score": 5.5, "status": "raw"},
    {"company": "MidCorp", "industry": "enterprise", "score": 4.8, "status": "raw"},
    {"company": "NewFintech", "industry": "fintech", "score": 6.9, "status": "qualified"},
]


async def seed():
    import os
    dsn = os.environ.get("POSTGRES_SYNC_URL", "postgresql://forgeflow:forgeflow@localhost:5432/forgeflow")
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=3)

    print("Seeding leads...")
    for lead in SAMPLE_LEADS:
        run_id = str(uuid.uuid4())
        lead_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())

        # Create a fake workflow run
        async with pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO workflow_runs
                      (id, thread_id, workflow_type, status, input_data, total_tokens, total_cost_usd)
                    VALUES ($1, $2, 'sales_ops', $3, $4, $5, $6)
                    """,
                    uuid.UUID(run_id),
                    uuid.UUID(thread_id),
                    "completed" if lead["status"] != "raw" else "running",
                    {"company_name": lead["company"]},
                    800,
                    0.0012,
                )
                await conn.execute(
                    """
                    INSERT INTO leads
                      (id, run_id, company_name, industry, qualification_score, status)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    uuid.UUID(lead_id),
                    uuid.UUID(run_id),
                    lead["company"],
                    lead["industry"],
                    lead["score"],
                    lead["status"],
                )
                print(f"  ✓ {lead['company']} (score={lead['score']}, status={lead['status']})")
            except Exception as e:
                print(f"  ✗ {lead['company']}: {e}")

    await pool.close()
    print("Seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed())
