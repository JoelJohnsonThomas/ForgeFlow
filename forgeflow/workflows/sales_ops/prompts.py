"""Prompt templates for the Sales Operations workflow agents."""

from __future__ import annotations

# ------------------------------------------------------------------ #
# Supervisor                                                           #
# ------------------------------------------------------------------ #

SUPERVISOR_ROUTING_TEMPLATE = """
You are supervising a sales qualification workflow.

Current stage: {stage}
Lead: {company_name}
Research collected: {research_count} data points
Latest score: {score}
Errors: {errors}
Approval status: {approval_status}

Decide the next routing step. Options:
- researcher: gather more company intelligence
- analyzer: score and qualify the lead
- executor: draft proposal or execute actions
- human_approval: pause for manager review (only when proposal is ready)
- FINISH: workflow complete or lead disqualified

Routing decision:
"""

# ------------------------------------------------------------------ #
# Researcher                                                           #
# ------------------------------------------------------------------ #

RESEARCHER_COMPANY_QUERY = "site:crunchbase.com OR site:linkedin.com/company {company} funding employees revenue"

RESEARCHER_NEWS_QUERY = "{company} press release announcement funding 2024 OR 2025 OR 2026"

RESEARCHER_TECH_QUERY = "{company} technology stack engineering blog job openings site:linkedin.com OR site:glassdoor.com"

# ------------------------------------------------------------------ #
# Analyzer                                                             #
# ------------------------------------------------------------------ #

ANALYZER_ICP_CRITERIA = """
Ideal Customer Profile (ICP) for ForgeFlow Enterprise AI:

STRONG FIT signals (each adds to score):
  ✓ 200-5000 employees (sweet spot: 500-2000)
  ✓ Series A or later funding (or $5M+ ARR if bootstrapped)
  ✓ Tech-forward: uses cloud infrastructure, APIs, modern stack
  ✓ Engineering team > 10% of workforce
  ✓ Industry: SaaS, FinTech, HealthTech, E-Commerce, Enterprise Software
  ✓ Recent growth signals: hiring, new products, market expansion
  ✓ Decision maker identified with clear budget authority

WEAK FIT signals (each reduces score):
  ✗ Pre-seed or no external funding
  ✗ Traditional/non-tech industry
  ✗ Fewer than 50 employees
  ✗ No engineering team identified
  ✗ Declining growth, layoffs, or restructuring signals
  ✗ Recent acquisition (budget freeze risk)
"""

# ------------------------------------------------------------------ #
# Executor — Proposal                                                  #
# ------------------------------------------------------------------ #

PROPOSAL_TEMPLATE = """
Based on the research and qualification data, draft a personalized sales proposal.

Company: {company}
Qualification Score: {score}/10
Estimated Deal Value: ${deal_value:,}
Key Pain Points Identified: {pain_points}
Research Highlights: {research_highlight}

Write a compelling proposal that:
1. Opens with a highly specific executive summary that references their actual situation
2. Connects our AI workflow automation to their specific growth challenges
3. Proposes 3 pricing tiers (Starter $2k/mo, Growth $8k/mo, Enterprise $25k+/mo)
4. Quantifies ROI with realistic numbers for their company size
5. Lists 3 specific next steps

Tone: confident, consultative, data-driven. Avoid generic sales language.
"""

# ------------------------------------------------------------------ #
# LLM-as-Judge                                                         #
# ------------------------------------------------------------------ #

JUDGE_EVALUATION_PROMPT = """You are an objective AI quality evaluator.

Evaluate the agent's response on four dimensions (all scores 0.0-1.0):

INPUT (what the agent was asked):
{input}

CONTEXT (information the agent had access to):
{context}

OUTPUT (what the agent produced):
{output}

Score the output on:
1. faithfulness: Does the output accurately reflect the context? (0=hallucinated, 1=fully grounded)
2. relevance: Is the output actually useful for the input request? (0=irrelevant, 1=spot-on)
3. coherence: Is the output well-structured and internally consistent? (0=confusing, 1=clear)
4. hallucination_flag: Did the agent invent specific facts (companies, numbers, names) not in context?

Return a JSON object with these exact keys: faithfulness, relevance, coherence, hallucination_flag
"""
