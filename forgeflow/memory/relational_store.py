"""RelationalStore — structured memory in PostgreSQL for leads and interactions."""

from __future__ import annotations

import logging

import asyncpg

logger = logging.getLogger(__name__)


class RelationalStore:
    """Reads and writes structured domain data (leads, proposals) from PostgreSQL."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def upsert_lead(self, lead_data: dict) -> str:
        """Insert or update a lead record. Returns the lead UUID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO leads (company_name, contact_name, contact_email, industry,
                                   raw_data, enriched_data, run_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT DO NOTHING
                RETURNING id
                """,
                lead_data.get("company_name", ""),
                lead_data.get("contact_name"),
                lead_data.get("contact_email"),
                lead_data.get("industry"),
                lead_data,
                lead_data.get("enriched_data", {}),
                lead_data.get("run_id"),
            )
            if row:
                return str(row["id"])

            # Conflict — fetch existing
            existing = await conn.fetchrow(
                "SELECT id FROM leads WHERE company_name = $1",
                lead_data.get("company_name"),
            )
            return str(existing["id"]) if existing else ""

    async def update_lead_score(
        self,
        lead_id: str,
        score: float,
        status: str,
        enriched: dict,
    ) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE leads
                SET qualification_score = $2,
                    status = $3,
                    enriched_data = $4,
                    updated_at = now()
                WHERE id = $1
                """,
                lead_id,
                score,
                status,
                enriched,
            )

    async def get_similar_leads(self, industry: str, min_score: float = 6.0) -> list[dict]:
        """Find historical qualified leads in the same industry for pattern matching."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, company_name, industry, qualification_score, status, enriched_data
                FROM leads
                WHERE industry = $1
                  AND qualification_score >= $2
                  AND status != 'disqualified'
                ORDER BY qualification_score DESC
                LIMIT 5
                """,
                industry,
                min_score,
            )
        return [dict(r) for r in rows]

    async def save_proposal(self, proposal_data: dict) -> str:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO proposals (lead_id, run_id, content, pricing, risk_flags)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                proposal_data.get("lead_id"),
                proposal_data.get("run_id"),
                str(proposal_data.get("executive_summary", "")),
                proposal_data.get("pricing_tiers", []),
                proposal_data.get("risk_flags", []),
            )
        return str(row["id"])
