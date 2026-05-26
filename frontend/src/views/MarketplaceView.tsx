export function MarketplaceView() {
  return (
    <section className="view active" data-screen-label="Marketplace">
      <div className="page-head">
        <div className="row">
          <div>
            <h1>Marketplace</h1>
            <p className="sub">Community workflow templates · /marketplace/templates</p>
          </div>
        </div>
      </div>
      <div className="page-body">
        <div className="panel">
          <div className="panel-body" style={{ padding: 64, textAlign: 'center', color: 'var(--fg-muted)' }}>
            <p style={{ fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '.12em', textTransform: 'uppercase' }}>
              Coming soon
            </p>
            <p style={{ marginTop: 12, fontSize: 13 }}>
              Backend lists installed templates at <code style={{ color: 'var(--blue-4)' }}>/marketplace/templates</code>.
              A browse + install flow ships in the next iteration.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
