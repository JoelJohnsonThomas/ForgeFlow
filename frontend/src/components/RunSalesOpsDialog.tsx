import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError } from '../api/client'
import type { RunWorkflowResponse, SalesLeadInput } from '../api/client'
import { useRunSalesOps } from '../api/hooks'
import { useSession } from '../hooks/useSession'
import { openSignIn } from './authEvents'
import '../styles/auth.css'

const INDUSTRIES: NonNullable<SalesLeadInput['industry']>[] = [
  'saas',
  'fintech',
  'healthcare',
  'enterprise',
  'ecommerce',
  'martech',
  'other',
]

/**
 * Trigger a real sales_ops run (POST /workflows/run). The graph executes
 * synchronously — researcher → analyzer → executor — so the request takes
 * 1–2 minutes; the dialog stays open with a progress note, then shows where
 * the run landed (pending approval vs. disqualified/completed).
 */
export function RunSalesOpsDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const session = useSession()
  const run = useRunSalesOps()
  const [company, setCompany] = useState('')
  const [contactName, setContactName] = useState('')
  const [contactEmail, setContactEmail] = useState('')
  const [industry, setIndustry] = useState('')
  const [budget, setBudget] = useState('')
  const [context, setContext] = useState('')
  const [result, setResult] = useState<RunWorkflowResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const firstFieldRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!open) return
    firstFieldRef.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !run.isPending) onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose, run.isPending])

  if (!open) return null

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setResult(null)
    const lead: SalesLeadInput = { company_name: company.trim() }
    if (contactName.trim()) lead.contact_name = contactName.trim()
    if (contactEmail.trim()) lead.contact_email = contactEmail.trim()
    if (industry) lead.industry = industry as SalesLeadInput['industry']
    if (budget.trim()) lead.known_budget_usd = Math.max(0, Math.round(Number(budget)))
    if (context.trim()) lead.additional_context = context.trim().slice(0, 1000)
    try {
      setResult(await run.mutateAsync(lead))
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError('Your session expired — sign in and try again.')
      } else if (err instanceof ApiError && err.status === 403) {
        setError('Your role cannot trigger workflows (viewers are read-only). Sign in as rep-1 or manager-1.')
      } else if (err instanceof ApiError && err.status === 422) {
        setError(`The API rejected the payload: ${err.message.slice(0, 300)}`)
      } else if (err instanceof ApiError && err.status === 504) {
        setError('The run timed out (an LLM or tool call hung). Check Live runs — it may still complete.')
      } else {
        setError(err instanceof Error ? err.message : String(err))
      }
    }
  }

  const close = () => {
    if (run.isPending) return
    setResult(null)
    setError(null)
    onClose()
  }

  return (
    <div className="auth-overlay" onClick={close}>
      <div
        className="auth-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="run-dialog-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="run-dialog-title">Run sales_ops</h2>

        {!session ? (
          <>
            <p className="auth-hint">
              Triggering a workflow calls <code>POST /workflows/run</code>, which needs a signed-in session.
            </p>
            <div className="auth-actions">
              <button type="button" className="btn" onClick={close}>
                Cancel
              </button>
              <button
                type="button"
                className="btn primary"
                onClick={() => {
                  close()
                  openSignIn()
                }}
              >
                Sign in first
              </button>
            </div>
          </>
        ) : result ? (
          <>
            <p className="auth-hint">
              Run <code>{result.run_id.slice(0, 8)}</code> finished the agent pipeline with status{' '}
              <code>{result.status}</code>
              {result.message ? <> — {result.message}</> : null}.
            </p>
            <p className="auth-hint">
              {result.status === 'pending_approval' ? (
                <>
                  The proposal is waiting for a manager in <a href="/console/approvals">Approvals</a>.
                </>
              ) : (
                <>
                  See it in <a href="/console/runs">Live runs</a>. (Leads scoring below 4.0 are disqualified and
                  complete without an approval.)
                </>
              )}
            </p>
            <div className="auth-actions">
              <button type="button" className="btn primary" onClick={close}>
                Done
              </button>
            </div>
          </>
        ) : (
          <>
            <p className="auth-hint">
              Runs the real pipeline: researcher → analyzer (scores the lead; &lt;4.0 disqualifies) → executor
              drafts a proposal → suspends for manager approval. Takes <b>1–2 minutes</b>; costs real LLM tokens.
            </p>
            <form onSubmit={submit}>
              <label>
                <span>Company name (required)</span>
                <input
                  ref={firstFieldRef}
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  required
                  maxLength={256}
                  disabled={run.isPending}
                />
              </label>
              <label>
                <span>Contact name</span>
                <input value={contactName} onChange={(e) => setContactName(e.target.value)} disabled={run.isPending} />
              </label>
              <label>
                <span>Contact email</span>
                <input
                  type="email"
                  value={contactEmail}
                  onChange={(e) => setContactEmail(e.target.value)}
                  disabled={run.isPending}
                />
              </label>
              <label>
                <span>Industry</span>
                <select value={industry} onChange={(e) => setIndustry(e.target.value)} disabled={run.isPending}>
                  <option value="">— optional —</option>
                  {INDUSTRIES.map((i) => (
                    <option key={i} value={i}>
                      {i}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Known budget (USD)</span>
                <input
                  type="number"
                  min={0}
                  step={1000}
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                  disabled={run.isPending}
                />
              </label>
              <label>
                <span>Additional context (richer context → better qualification)</span>
                <textarea
                  rows={3}
                  maxLength={1000}
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  disabled={run.isPending}
                  placeholder="e.g. Series D, 500+ employees, confirmed Q3 budget, champion has signing authority…"
                />
              </label>
              {error && (
                <p className="auth-error" role="alert">
                  {error}
                </p>
              )}
              {run.isPending && (
                <p className="auth-hint" role="status">
                  Running — the supervisor is routing agents (researcher → analyzer → executor). This usually
                  takes 1–2 minutes; leave this open.
                </p>
              )}
              <div className="auth-actions">
                <button type="button" className="btn" onClick={close} disabled={run.isPending}>
                  Cancel
                </button>
                <button type="submit" className="btn primary" disabled={run.isPending || !company.trim()}>
                  {run.isPending ? 'Running…' : 'Run workflow'}
                </button>
              </div>
            </form>
          </>
        )}
      </div>
    </div>
  )
}
