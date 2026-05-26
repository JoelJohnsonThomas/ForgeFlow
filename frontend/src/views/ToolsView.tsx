/**
 * Tools (MCP) — backend doesn't expose a tool catalog endpoint yet.
 * Static representation of the 4 default tool providers.
 */

const TOOLS = [
  { provider: 'tavily', name: 'web_search', desc: 'Real-time web search via Tavily', badge: 'blue' },
  { provider: 'internal', name: 'scrape_url', desc: 'Fetch + parse arbitrary URL', badge: 'blue' },
  { provider: 'salesforce', name: 'lead.create / .update', desc: 'Mock CRM (swappable for real SFDC)', badge: 'amber' },
  { provider: 'salesforce', name: 'opportunity.stage', desc: 'Move CRM record between stages', badge: 'amber' },
  { provider: 'email', name: 'compose / send', desc: 'Draft + send via SMTP or provider API', badge: 'purple' },
  { provider: 'memory', name: 'recall', desc: 'Semantic recall over pgvector', badge: 'emerald' },
  { provider: 'memory', name: 'store', desc: 'Persist a memory with embedding', badge: 'emerald' },
  { provider: 'hubspot', name: 'contact.create', desc: 'HubSpot connector (env-gated)', badge: 'blue' },
  { provider: 'jira', name: 'issue.create', desc: 'Jira connector (env-gated)', badge: 'blue' },
  { provider: 'github', name: 'issue.create', desc: 'GitHub connector (env-gated)', badge: 'blue' },
  { provider: 'msgraph', name: 'mail.send', desc: 'Microsoft Graph connector', badge: 'blue' },
  { provider: 'servicenow', name: 'incident.create', desc: 'ServiceNow connector', badge: 'blue' },
  { provider: 'quickbooks', name: 'invoice.create', desc: 'QuickBooks connector', badge: 'amber' },
  { provider: 'sap', name: 'sales_order.create', desc: 'SAP S/4 OData connector', badge: 'amber' },
]

export function ToolsView() {
  return (
    <section className="view active" data-screen-label="Tools">
      <div className="page-head">
        <div className="row">
          <div>
            <h1>Tools · MCP</h1>
            <p className="sub">{TOOLS.length} registered tools · served via FastMCP on :8001</p>
          </div>
        </div>
      </div>
      <div className="page-body">
        <div className="panel">
          <div className="panel-body flush">
            <table className="tbl">
              <thead>
                <tr>
                  <th>Provider</th>
                  <th>Tool</th>
                  <th>Description</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {TOOLS.map((t) => (
                  <tr key={`${t.provider}.${t.name}`}>
                    <td>
                      <span className={`badge ${t.badge}`}>{t.provider}</span>
                    </td>
                    <td className="mono">{t.name}</td>
                    <td style={{ color: 'var(--fg-secondary)' }}>{t.desc}</td>
                    <td>
                      <span className="badge emerald">● ready</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  )
}
