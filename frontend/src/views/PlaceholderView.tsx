type Props = {
  title: string
  sub?: string
}

export function PlaceholderView({ title, sub }: Props) {
  return (
    <section className="view active">
      <div className="page-head">
        <div className="row">
          <div>
            <h1>{title}</h1>
            {sub && <p className="sub">{sub}</p>}
          </div>
        </div>
      </div>
      <div className="page-body">
        <div className="panel">
          <div className="panel-body" style={{ padding: 64, textAlign: 'center', color: 'var(--fg-muted)' }}>
            <p style={{ fontFamily: 'var(--font-mono)', fontSize: 11, letterSpacing: '.12em', textTransform: 'uppercase' }}>
              Phase 2 ·  pending
            </p>
            <p style={{ marginTop: 12, fontSize: 13 }}>
              This view ports cleanly from the design but isn't built yet. The Overview view shows what the
              finished components look like.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
