# Connector Setup

ForgeFlow's 8 enterprise connectors are exposed to agents as MCP tools. Each is
built on a resilient base ([`forgeflow/connectors/base.py`](../forgeflow/connectors/base.py))
and **degrades gracefully** — with no credentials, a connector returns clearly
labelled mock responses (`{"mock": true, …}`) so demos and CI run without real
accounts. Set the variables below to talk to the real vendor.

All variables are also listed in the [configuration reference](configuration.md).

---

## HubSpot — `sales_ops`

| Variable | Notes |
|---|---|
| `HUBSPOT_ACCESS_TOKEN` | Private App token |
| `HUBSPOT_BASE_URL` | `https://api.hubapi.com` (default) |

**Get it:** HubSpot → Settings → Integrations → **Private Apps** → create an app
with CRM scopes (`crm.objects.contacts.*`, `crm.objects.companies.*`,
`crm.objects.deals.*`) and copy the access token. For the full production runbook
see [sales-ops-production.md](sales-ops-production.md).

## Salesforce — `sales_ops`

| Variable | Notes |
|---|---|
| `SALESFORCE_INSTANCE_URL` | e.g. `https://acme.my.salesforce.com` |
| `SALESFORCE_ACCESS_TOKEN` | OAuth bearer token |
| `SALESFORCE_API_VERSION` | `v59.0` (default) |

**Get it:** acquire a bearer via the `sf` CLI (`sf org display`) or a JWT bearer
flow for headless use. Tokens are short-lived — refresh externally.

## Jira Cloud — `support_ops`

| Variable | Notes |
|---|---|
| `JIRA_BASE_URL` | e.g. `https://acme.atlassian.net` |
| `JIRA_EMAIL` | Atlassian account email (Basic-auth username) |
| `JIRA_API_TOKEN` | From id.atlassian.com |

**Get it:** <https://id.atlassian.com/manage-profile/security/api-tokens> → create
an API token; auth is Basic (`email:token`).

## ServiceNow — incident management

| Variable | Notes |
|---|---|
| `SERVICENOW_INSTANCE_URL` | e.g. `https://acme.service-now.com` |
| `SERVICENOW_USERNAME` | Service-account user (Basic auth) |
| `SERVICENOW_PASSWORD` | Service-account password |

**Get it:** create a dedicated integration user with the `itil` role (Table API
access to `incident` / `change_request`).

## GitHub — DevOps / PR review

| Variable | Notes |
|---|---|
| `GITHUB_TOKEN` | PAT or installation token (`repo` scope; `read:org` for org repo lists) |
| `GITHUB_BASE_URL` | `https://api.github.com` (override for GHES) |
| `GITHUB_DEFAULT_OWNER` | Optional default owner so tool calls can omit it |

**Get it:** GitHub → Settings → Developer settings → **Personal access tokens**.
For GitHub Apps, swap in an installation token — the URL surface is identical.

## SAP S/4HANA — `finance_recon`

| Variable | Notes |
|---|---|
| `SAP_BASE_URL` | e.g. `https://my300000-api.s4hana.cloud.sap` |
| `SAP_USERNAME` / `SAP_PASSWORD` | Technical user / client secret |
| `SAP_CLIENT` | Client number (`100` default) |

**Get it:** a communication/technical user with OData v2 access to the relevant
APIs. The connector handles CSRF token fetch for writes.

## QuickBooks Online — `finance_recon`

| Variable | Notes |
|---|---|
| `QUICKBOOKS_ACCESS_TOKEN` | Intuit OAuth access token (refreshed externally) |
| `QUICKBOOKS_REALM_ID` | Company ID (`realmId` from the OAuth callback) |
| `QUICKBOOKS_ENVIRONMENT` | `sandbox` \| `production` |
| `QUICKBOOKS_MINOR_VERSION` | Intuit API minor version (`65`) |

**Get it:** create an app in the Intuit Developer portal, run the OAuth 2.0 flow
to obtain the access token + `realmId`. Refresh tokens out-of-band.

## Microsoft Graph — HITL approvals (Teams/Outlook/Calendar)

| Variable | Notes |
|---|---|
| `MSGRAPH_ACCESS_TOKEN` | Azure AD OAuth bearer (refreshed via MSAL) |
| `MSGRAPH_TENANT_ID` | Azure AD tenant ID |
| `MSGRAPH_BASE_URL` | `https://graph.microsoft.com/v1.0` (default) |

**Get it:** register an app in Azure AD with the needed Graph scopes
(`Mail.Send`, `Chat.ReadWrite`, `Calendars.ReadWrite`), then acquire a token via
MSAL / client-credentials.

---

## Also configurable

| Integration | Variable(s) | Purpose |
|---|---|---|
| **Slack** (HITL cards) | `SLACK_BOT_TOKEN` (`xoxb-…`), `SLACK_DEFAULT_CHANNEL` | Approval notifications with approve/reject buttons |
| **Tavily** (web search) | `TAVILY_API_KEY` | Real search for the researcher agent (else mock results) |

## Adding a new connector

1. Subclass `BaseConnector` in `forgeflow/connectors/<vendor>.py` (copy
   [`github.py`](../forgeflow/connectors/github.py)).
2. Add its settings to [`forgeflow/config.py`](../forgeflow/config.py) and this page.
3. Add a matching MCP tool router under `forgeflow/mcp/server/tools/` and mount it
   in `forgeflow/mcp/server/main.py`.
