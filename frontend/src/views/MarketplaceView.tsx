export function MarketplaceView() {
  return (
    <section className="view active" data-screen-label="Marketplace">
      <div className="page-head">
        <div className="row">
          <div>
            <h1>
              Marketplace{' '}
              <span className="badge amber" style={{ fontSize: 11, verticalAlign: 'middle' }}>Preview</span>
            </h1>
            <p className="sub">Community workflow templates you can browse and install</p>
          </div>
        </div>
      </div>
      <div className="page-body">
        <div className="panel">
          <div className="panel-body" style={{ padding: 64, textAlign: 'center', color: 'var(--fg-muted)' }}>
            <p style={{ fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '.12em', textTransform: 'uppercase' }}>
              Coming soon
            </p>
            <p style={{ marginTop: 12, fontSize: 13, maxWidth: 460, marginInline: 'auto', lineHeight: 1.6 }}>
              The API already lists installed templates at{' '}
              <code style={{ color: 'var(--blue-4)' }}>/api/marketplace/templates</code>. A browse-and-install
              experience is in progress. In the meantime, explore the bundled templates on the{' '}
              <a href="/console/workflows" style={{ color: 'var(--blue-4)' }}>Workflows</a> page.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
