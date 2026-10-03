import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Copy, ImagePlus, Layers, RefreshCw, Upload, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import {
  cancelSegmentation,
  cancelSimulation,
  createSegmentation,
  createSimulation,
  getLabStatus,
  getSegmentation,
  getSimulation,
  importProfiles,
  isActive,
  listSegmentations,
  listSimulations,
  syncProfiles,
} from '../api/audienceLab'
import type {
  PanelSegmentResult,
  ProfileImportItem,
  Progress,
  Segment,
  Segmentation,
  Simulation,
  Uplift,
  WeightedMetrics,
} from '../api/audienceLab'
import { SENTIMENT_COLORS } from '../charts/theme'
import { Bars, StackBar } from '../components/Bars'
import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { platformLabel } from '../utils/platform'
import { Stat, Stats } from '../components/Stat'
import { Status } from '../components/Status'
import { EmptyState, ErrorState, LoadingState, Notice } from '../components/States'
import { timeAgo } from '../utils/format'
import './audience-lab.css'

const STAGES: Record<string, string> = {
  queued: 'Queued',
  starting: 'Starting',
  discovering_segments: 'Designing segments from a sample of profiles',
  assigning_profiles: 'Placing every profile into a segment',
  building_agents: 'Writing one agent per segment',
  agents_reacting: 'Segment agents are reading the post',
  analysing: 'Combining the reactions',
  retesting_rewrite: 'Scoring the rewritten post',
  completed: 'Done',
}
const VERDICTS: Record<string, string> = {
  post_as_is: 'Post as is',
  minor_edits: 'Minor edits',
  major_rework: 'Major rework',
  do_not_post: 'Do not post',
}
const pct = (value: number | undefined | null, digits = 0) => (value == null ? '–' : `${value.toFixed(digits)}%`)
const signed = (value: number | undefined | null, unit = 'pp') =>
  value == null ? '–' : `${value > 0 ? '+' : ''}${value.toFixed(1)}${unit === '%' ? '%' : ' pp'}`
const errorText = (error: unknown) => (error instanceof Error ? error.message : 'Request failed')

function secondsSince(iso: string | undefined, now: number) {
  if (!iso) return null
  const t = Date.parse(iso)
  return Number.isNaN(t) ? null : Math.max(0, Math.round((now - t) / 1000))
}

function duration(seconds: number | null) {
  if (seconds == null) return '–'
  const m = Math.floor(seconds / 60)
  return m ? `${m}m ${String(seconds % 60).padStart(2, '0')}s` : `${seconds}s`
}

function useNow(active: boolean) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!active) return
    const id = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(id)
  }, [active])
  return now
}

function LiveProgress({ progress, status, onCancel, cancelling }: { progress: Progress; status: string; onCancel?: () => void; cancelling?: boolean }) {
  const now = useNow(true)
  const label = STAGES[progress.stage ?? ''] ?? progress.stage ?? status
  const share = progress.total ? Math.round(((progress.done ?? 0) / progress.total) * 100) : null
  const elapsed = secondsSince(progress.started_at, now)
  const quiet = secondsSince(progress.last_activity_at, now)
  const calls = progress.calls
  const tokens = progress.tokens
  const events = [...(progress.events ?? [])].reverse().slice(0, 8)
  return (
    <div className="lab-progress" role="status" aria-live="polite">
      <div className="lab-progress__head">
        <span className="spinner" aria-hidden="true" />
        <div className="lab-progress__title">
          <strong>{progress.steps ? `Step ${progress.step}/${progress.steps} · ` : ''}{label}</strong>
          <small>{share != null ? `${progress.done}/${progress.total} done · ` : ''}running for {duration(elapsed)}</small>
        </div>
        {onCancel && (
          <button type="button" className="btn btn--sm" onClick={onCancel} disabled={cancelling || progress.cancel_requested}>
            {cancelling || progress.cancel_requested ? 'Cancelling' : 'Cancel'}
          </button>
        )}
      </div>
      <div className="lab-progress__bar"><i style={{ width: `${share ?? 4}%` }} /></div>
      {calls && (
        <div className="lab-progress__stats">
          <span><b>{calls.in_flight}</b> model calls in flight</span>
          <span><b>{calls.finished}</b> finished</span>
          {calls.failed > 0 && <span className="warn"><b>{calls.failed}</b> failed</span>}
          {calls.retries > 0 && <span className="warn"><b>{calls.retries}</b> retries</span>}
          {tokens && <span><b>{(tokens.prompt + tokens.completion).toLocaleString()}</b> tokens{tokens.reasoning ? ` (${tokens.reasoning.toLocaleString()} thinking)` : ''}</span>}
          <span>last activity {quiet == null ? '–' : `${duration(quiet)} ago`}</span>
        </div>
      )}
      {calls && calls.in_flight > 0 && quiet != null && quiet > 60 && (
        <p className="faint" style={{ fontSize: 12.5 }}>Waiting on the model. Large batches can take a few minutes; calls that exceed the timeout are retried.</p>
      )}
      {events.length > 0 && (
        <ol className="lab-log">
          {events.map((e, i) => (
            <li key={`${e.at}-${i}`} className={e.level === 'warn' ? 'warn' : ''}>
              <time>{new Date(e.at).toLocaleTimeString()}</time><span>{e.message}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}

function JobEvents({ progress }: { progress: Progress }) {
  const events = [...(progress.events ?? [])].reverse()
  if (events.length === 0) return null
  return (
    <details className="lab-details">
      <summary>Run log: {duration(progress.elapsed_seconds ?? null)}, {progress.calls?.finished ?? 0} model calls</summary>
      <ol className="lab-log">
        {events.map((e, i) => <li key={`${e.at}-${i}`} className={e.level === 'warn' ? 'warn' : ''}><time>{new Date(e.at).toLocaleTimeString()}</time><span>{e.message}</span></li>)}
      </ol>
    </details>
  )
}

// ---------------------------------------------------------------------------
// Audience data
// ---------------------------------------------------------------------------

function AudienceData() {
  const client = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [message, setMessage] = useState<{ tone: 'ok' | 'error'; text: string } | null>(null)
  const status = useQuery({ queryKey: ['lab', 'status'], queryFn: getLabStatus })
  const refresh = () => client.invalidateQueries({ queryKey: ['lab', 'status'] })
  const sync = useMutation({
    mutationFn: syncProfiles,
    onSuccess: (r) => { setMessage({ tone: 'ok', text: `${r.created} new and ${r.updated} refreshed profiles.` }); void refresh() },
    onError: (e) => setMessage({ tone: 'error', text: errorText(e) }),
  })
  const upload = useMutation({
    mutationFn: importProfiles,
    onSuccess: (r) => { setMessage({ tone: 'ok', text: `Imported ${r.created} new and updated ${r.updated} profiles.` }); void refresh() },
    onError: (e) => setMessage({ tone: 'error', text: errorText(e) }),
  })

  async function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    try {
      const parsed = JSON.parse(await file.text()) as ProfileImportItem[] | { profiles: ProfileImportItem[] }
      const profiles = Array.isArray(parsed) ? parsed : parsed.profiles
      if (!Array.isArray(profiles) || profiles.length === 0) throw new Error('the file must contain a JSON array of profiles')
      upload.mutate(profiles)
    } catch (error) {
      setMessage({ tone: 'error', text: `Could not read ${file.name}: ${errorText(error)}` })
    }
  }

  const data = status.data
  return (
    <Panel className="col-4" title="Audience data" description="Profiles the segments are built from. Collected accounts sync automatically every 15 minutes.">
      {status.isLoading ? <LoadingState /> : status.error ? <ErrorState error={status.error} /> : data && (
        <div style={{ display: 'grid', gap: 14 }}>
          <dl className="kv">
            <dt>Profiles</dt><dd className="num"><b>{data.total_profiles.toLocaleString('en')}</b></dd>
            {Object.entries(data.by_source).map(([source, count]) => <div key={source} style={{ display: 'contents' }}><dt>{source}</dt><dd className="num">{count.toLocaleString('en')}</dd></div>)}
            <dt>Model</dt><dd>{data.api_configured ? data.model_name : <Status status="fail" label="META_MODEL_API_KEY missing" />}</dd>
          </dl>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            <button type="button" className="btn" onClick={() => sync.mutate()} disabled={sync.isPending}><RefreshCw size={13} className={sync.isPending ? 'spin' : ''} /> Sync now</button>
            <button type="button" className="btn" onClick={() => fileRef.current?.click()} disabled={upload.isPending}><Upload size={13} /> Import JSON</button>
            <input ref={fileRef} type="file" accept="application/json,.json" hidden onChange={onFile} />
          </div>
          {message && (message.tone === 'error' ? <Notice tone="error">{message.text}</Notice> : <span className="status status--ok"><i />{message.text}</span>)}
          <details className="lab-details">
            <summary>Import format</summary>
            <pre>{`[{ "source": "crm_2026", "external_ref": "cust-001", "platform": "instagram",
   "attributes": { "age": "25-34", "city": "Pune", "interests": ["fitness"] },
   "sample_texts": ["Loved the last drop!"], "weight": 1 }]`}</pre>
            <p>Any attribute keys work. <code>weight</code> is how many real people a record stands for.</p>
          </details>
        </div>
      )}
    </Panel>
  )
}

// ---------------------------------------------------------------------------
// Composer
// ---------------------------------------------------------------------------

function Composer({ segmentation, platforms, onStarted }: { segmentation: Segmentation | undefined; platforms: string[]; onStarted: (id: string) => void }) {
  const [text, setText] = useState('')
  const [chosenPlatform, setPlatform] = useState<string | null>(null)
  const platform = chosenPlatform ?? platforms[0] ?? 'x'
  const [image, setImage] = useState<string | null>(null)
  const [mediaDescription, setMediaDescription] = useState('')
  const [autoImprove, setAutoImprove] = useState(true)
  const [fileError, setFileError] = useState('')
  const run = useMutation({
    mutationFn: () => createSimulation({
      text, platform, segmentation_id: segmentation?.segmentation_id, image_data_url: image,
      media_description: mediaDescription.trim() || null, auto_improve: autoImprove,
    }),
    onSuccess: (sim) => onStarted(sim.simulation_id),
  })
  const ready = segmentation?.status === 'COMPLETED' && segmentation.segments.length > 0

  function onImage(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    setFileError('')
    if (!file) return
    if (file.size > 5_000_000) { setFileError('Images must be under 5 MB.'); return }
    const reader = new FileReader()
    reader.onload = () => setImage(typeof reader.result === 'string' ? reader.result : null)
    reader.readAsDataURL(file)
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    if (text.trim()) run.mutate()
  }

  return (
    <Panel className="col-8" title="Test a post" description={ready ? `${segmentation!.segments.length} segment agents will react to it, then the reactions are combined and a rewrite is scored.` : 'Build segments below first.'}>
      <form className="lab-composer" onSubmit={submit}>
        <textarea className="textarea" required maxLength={8000} value={text} onChange={(e) => setText(e.target.value)} placeholder="Paste the post you plan to publish" aria-label="Post text" />
        <div className="lab-composer__row">
          <label className="field">Platform
            <select className="select" value={platform} onChange={(e) => setPlatform(e.target.value)}>{(platforms.length ? platforms : ['x']).map((p) => <option key={p} value={p}>{platformLabel(p)}</option>)}</select>
          </label>
          <label className="field lab-grow">Describe any video or media (optional)
            <input className="input" value={mediaDescription} maxLength={2000} onChange={(e) => setMediaDescription(e.target.value)} placeholder="e.g. 15-second clip of the launch event" />
          </label>
          <label className="field">Image (optional)
            <span className="btn"><ImagePlus size={13} /> {image ? 'Replace' : 'Attach'}<input type="file" accept="image/*" hidden onChange={onImage} /></span>
          </label>
        </div>
        {image && (
          <div className="lab-preview">
            <img src={image} alt="Attached post image" />
            <button type="button" className="btn btn--icon btn--sm" aria-label="Remove image" onClick={() => setImage(null)}><X size={13} /></button>
          </div>
        )}
        {fileError && <Notice tone="error">{fileError}</Notice>}
        <div className="lab-composer__submit">
          <label className="check"><input type="checkbox" checked={autoImprove} onChange={(e) => setAutoImprove(e.target.checked)} />Rewrite and re-test</label>
          <button className="btn btn--primary" type="submit" disabled={!ready || run.isPending || !text.trim()}>{run.isPending ? 'Starting' : 'Run test'}</button>
        </div>
        {run.error && <Notice tone="error">{errorText(run.error)}</Notice>}
      </form>
    </Panel>
  )
}

// ---------------------------------------------------------------------------
// Segments
// ---------------------------------------------------------------------------

function SegmentsPanel({ segmentation, onBuilt }: { segmentation: Segmentation | undefined; onBuilt: (id: string) => void }) {
  const [focus, setFocus] = useState('')
  const [minSeg, setMinSeg] = useState('')
  const [maxSeg, setMaxSeg] = useState('')
  const [open, setOpen] = useState<string | null>(null)
  const client = useQueryClient()
  const build = useMutation({
    mutationFn: () => createSegmentation({ focus: focus.trim() || null, min_segments: minSeg ? Number(minSeg) : null, max_segments: maxSeg ? Number(maxSeg) : null }),
    onSuccess: (run) => onBuilt(run.segmentation_id),
  })
  const cancel = useMutation({ mutationFn: cancelSegmentation, onSuccess: () => client.invalidateQueries({ queryKey: ['lab', 'segmentation'] }) })
  const running = isActive(segmentation?.status)
  const segments = segmentation?.segments ?? []

  return (
    <Panel
      flush
      title="Segments"
      description={segmentation?.status === 'COMPLETED' ? `${segments.length} segments from ${segmentation.assigned_count.toLocaleString('en')} of ${segmentation.profile_count.toLocaleString('en')} profiles · built ${segmentation.completed_at ? timeAgo(segmentation.completed_at) : ''}` : 'The model decides how many groups there are and what defines them.'}
    >
      <form className="lab-seg-form" onSubmit={(e) => { e.preventDefault(); build.mutate() }}>
        <label className="field lab-grow">Steer (optional)<input className="input" value={focus} onChange={(e) => setFocus(e.target.value)} placeholder="e.g. split by buying intent" maxLength={1000} /></label>
        <label className="field">Min<input className="input" type="number" min={1} max={30} value={minSeg} onChange={(e) => setMinSeg(e.target.value)} placeholder="auto" style={{ width: 76 }} /></label>
        <label className="field">Max<input className="input" type="number" min={1} max={30} value={maxSeg} onChange={(e) => setMaxSeg(e.target.value)} placeholder="auto" style={{ width: 76 }} /></label>
        <button className="btn" type="submit" disabled={build.isPending || running}><Layers size={13} /> {segmentation ? 'Rebuild' : 'Build segments'}</button>
      </form>
      <div style={{ padding: '0 16px 16px' }}>
        {build.error && <Notice tone="error">{errorText(build.error)}</Notice>}
        {!segmentation ? <EmptyState title="No segments yet" detail="Sync or import profiles, then build segments." />
          : running ? <LiveProgress progress={segmentation.progress} status={segmentation.status} onCancel={() => cancel.mutate(segmentation.segmentation_id)} cancelling={cancel.isPending} />
          : segmentation.status === 'FAILED' || segmentation.status === 'CANCELLED' ? <><Notice tone="error">Segmentation {segmentation.status === 'CANCELLED' ? 'cancelled' : 'failed'}: {segmentation.error}</Notice><JobEvents progress={segmentation.progress} /></>
          : (
            <>
              {segmentation.rationale && <p className="muted" style={{ fontSize: 13, marginBottom: 12, maxWidth: 900 }}>{segmentation.rationale}</p>}
              <div className="lab-segments">
                {segments.map((segment) => <SegmentRow key={segment.segment_id} segment={segment} expanded={open === segment.segment_id} onToggle={() => setOpen(open === segment.segment_id ? null : segment.segment_id)} />)}
              </div>
              <JobEvents progress={segmentation.progress} />
            </>
          )}
      </div>
    </Panel>
  )
}

function SegmentRow({ segment, expanded, onToggle }: { segment: Segment; expanded: boolean; onToggle: () => void }) {
  const persona = segment.persona
  const attrs = Object.entries(segment.attribute_breakdown).slice(0, 6)
  return (
    <div className={`lab-segment ${expanded ? 'is-open' : ''}`}>
      <button type="button" className="lab-segment__head" onClick={onToggle} aria-expanded={expanded}>
        <span className="lab-segment__code num">{segment.code}</span>
        <span style={{ minWidth: 0 }}>
          <span className="row__title">{segment.name}</span>
          <span className="row__meta">{segment.description}</span>
        </span>
        <span className="lab-segment__share">
          <span className="num">{pct(segment.share * 100, 1)}</span>
          <span className="bar__track" style={{ width: 90 }}><span className="bar__fill" style={{ width: `${segment.share * 100}%`, display: 'block' }} /></span>
          <span className="faint num" style={{ fontSize: 12 }}>{segment.member_count} profiles</span>
        </span>
      </button>
      {expanded && (
        <div className="lab-segment__body">
          <div>
            {segment.defining_traits.length > 0 && <p><span className="faint">Traits </span>{segment.defining_traits.join(', ')}</p>}
            {persona && <>
              <p>{persona.summary}</p>
              <p><span className="faint">Who </span>{persona.demographics}</p>
              <p><span className="faint">Engages with </span>{persona.positive_triggers.join(', ')}</p>
              <p><span className="faint">Turned off by </span>{persona.negative_triggers.join(', ')}</p>
              <p><span className="faint">Voice </span>{persona.communication_style}</p>
              <p className="faint">Evidence {persona.evidence_strength} · sarcasm {persona.sarcasm_tendency}</p>
            </>}
          </div>
          {attrs.length > 0 && (
            <dl className="kv" style={{ alignContent: 'start' }}>
              {attrs.map(([key, info]) => <div key={key} style={{ display: 'contents' }}><dt>{key.replaceAll('_', ' ')}</dt><dd>{info.top.slice(0, 3).map((t) => `${t.value} ${t.pct}%`).join(', ')}</dd></div>)}
            </dl>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Results
// ---------------------------------------------------------------------------

const VERDICT_TONE: Record<string, string> = { post_as_is: 'pass', minor_edits: 'warning', major_rework: 'fail', do_not_post: 'fail' }

function ReactionStats({ metrics }: { metrics: WeightedMetrics }) {
  return (
    <Stats label="Weighted reaction">
      <Stat label="Positive" tone="pos" value={metrics.positive ?? null} format={(n) => n.toFixed(1)} unit="%" />
      <Stat label="Neutral" value={metrics.neutral ?? null} format={(n) => n.toFixed(1)} unit="%" />
      <Stat label="Negative" tone="neg" value={metrics.negative ?? null} format={(n) => n.toFixed(1)} unit="%" />
      <Stat label="Sarcastic" tone="sar" value={metrics.sarcastic ?? null} format={(n) => n.toFixed(1)} unit="%" />
      <Stat label="Interested" tone="accent" value={metrics.interested ?? null} format={(n) => n.toFixed(1)} unit="%" />
      <Stat label="Would engage" value={metrics.engage ?? null} format={(n) => n.toFixed(1)} unit="%" />
      <Stat label="Would share" value={metrics.share ?? null} format={(n) => n.toFixed(1)} unit="%" />
    </Stats>
  )
}

function MixTable({ segments }: { segments: PanelSegmentResult[] }) {
  return (
    <div className="table-wrap"><table className="table">
      <thead><tr><th>Segment</th><th className="r">Share</th><th style={{ width: '38%' }}>Reaction mix</th><th className="r">Interested</th><th className="r">Engage</th></tr></thead>
      <tbody>
        {segments.map((result) => {
          const mix = result.reaction?.reaction_mix_pct
          return (
            <tr key={result.segment_id}>
              <td><strong>{result.name}</strong></td>
              <td className="r">{pct(result.share * 100, 1)}</td>
              <td>{mix ? <StackBar label={result.name} parts={(['positive', 'neutral', 'negative', 'sarcastic'] as const).map((key) => ({ key, value: mix[key], label: key, color: SENTIMENT_COLORS[key] }))} /> : <Status status="fail" label={result.error ?? 'Agent failed'} />}</td>
              <td className="r">{pct(result.reaction?.interested_pct)}</td>
              <td className="r">{pct(result.reaction?.engage_pct)}</td>
            </tr>
          )
        })}
      </tbody>
    </table></div>
  )
}

function UpliftPanel({ uplift, improved, original }: { uplift: Uplift | null; improved: string | null; original: string }) {
  const [copied, setCopied] = useState(false)
  if (!uplift) return null
  if (!uplift.available || !improved) return <Panel title="Rewrite"><p className="muted">{uplift.reason ?? 'No rewrite was tested.'}</p></Panel>
  const rows: [string, string][] = [
    ['interested', 'Interested'], ['engage', 'Would engage'], ['share', 'Would share'],
    ['positive', 'Positive'], ['negative', 'Negative'], ['sarcastic', 'Sarcastic'], ['net_sentiment', 'Net sentiment'],
  ]
  const lowerIsBetter = new Set(['negative', 'sarcastic'])
  const before = uplift.before as Record<string, number> | undefined
  const after = uplift.after as Record<string, number> | undefined
  const headlineKey = uplift.relative_pct?.engage != null ? 'engage' : 'interested'
  const headline = uplift.relative_pct?.[headlineKey]
  return (
    <Panel
      title="Rewrite"
      description={`Both versions scored by the same ${uplift.segments_compared} agents. Simulated, not measured engagement.`}
      actions={headline != null && <span className={`delta ${headline >= 0 ? 'delta--up' : 'delta--down'}`} style={{ fontSize: 15 }}>{signed(headline, '%')} {headlineKey === 'engage' ? 'engagement' : 'interest'}</span>}
    >
      <div className="lab-rewrite">
        <div><h3>Original</h3><p>{original}</p></div>
        <div className="is-new">
          <h3>Rewrite <button type="button" className="btn btn--ghost btn--sm" onClick={() => { void navigator.clipboard?.writeText(improved); setCopied(true); window.setTimeout(() => setCopied(false), 1600) }}>{copied ? <><Check size={12} /> Copied</> : <><Copy size={12} /> Copy</>}</button></h3>
          <p>{improved}</p>
        </div>
      </div>
      <div className="grid" style={{ marginTop: 16 }}>
        <div className="col-6">
          <div className="table-wrap"><table className="table">
            <thead><tr><th>Measure</th><th className="r">Original</th><th className="r">Rewrite</th><th className="r">Change</th></tr></thead>
            <tbody>{rows.map(([key, label]) => {
              const delta = uplift.delta_pp?.[key]
              const good = delta == null || delta === 0 ? null : lowerIsBetter.has(key) ? delta < 0 : delta > 0
              return <tr key={key}><td>{label}</td><td className="r">{before?.[key]?.toFixed(1) ?? '–'}</td><td className="r">{after?.[key]?.toFixed(1) ?? '–'}</td><td className={`r delta ${good == null ? 'delta--flat' : good ? 'delta--up' : 'delta--down'}`}>{signed(delta)}</td></tr>
            })}</tbody>
          </table></div>
        </div>
        {uplift.per_segment && uplift.per_segment.length > 0 && (
          <div className="col-6">
            <div className="table-wrap"><table className="table">
              <thead><tr><th>Segment</th><th className="r">Interested</th><th className="r">Engage</th><th className="r">Negative</th></tr></thead>
              <tbody>{uplift.per_segment.map((s) => (
                <tr key={s.code}><td>{s.name}</td>
                  <td className={`r delta ${s.interested_pp > 0 ? 'delta--up' : s.interested_pp < 0 ? 'delta--down' : 'delta--flat'}`}>{signed(s.interested_pp)}</td>
                  <td className={`r delta ${s.engage_pp > 0 ? 'delta--up' : s.engage_pp < 0 ? 'delta--down' : 'delta--flat'}`}>{signed(s.engage_pp)}</td>
                  <td className={`r delta ${s.negative_pp < 0 ? 'delta--up' : s.negative_pp > 0 ? 'delta--down' : 'delta--flat'}`}>{signed(s.negative_pp)}</td>
                </tr>
              ))}</tbody>
            </table></div>
          </div>
        )}
      </div>
    </Panel>
  )
}

function AgentResponses({ segments }: { segments: PanelSegmentResult[] }) {
  return (
    <Panel flush title="Agent responses" description="Each agent speaks for one segment">
      <div className="lab-agents">
        {segments.filter((result) => result.reaction).map((result) => {
          const r = result.reaction!
          return (
            <article key={result.segment_id} className="lab-agent">
              <header><strong>{result.name}</strong><span className="faint" style={{ fontSize: 12 }}>{r.confidence} confidence</span></header>
              <p className="lab-agent__quote">{r.first_impression}</p>
              <ul className="lab-voices">
                {r.sample_reactions.map((s, i) => <li key={i}><i className={`dot dot--${s.tone}`} /><span><span className="faint">{s.voice}</span> {s.text}</span></li>)}
              </ul>
              <dl className="kv" style={{ fontSize: 12.5 }}>
                {r.what_works.length > 0 && <><dt>Works</dt><dd>{r.what_works.join('; ')}</dd></>}
                {r.what_fails.length > 0 && <><dt>Falls flat</dt><dd>{r.what_fails.join('; ')}</dd></>}
                {r.misread_risks.length > 0 && <><dt>Misread risk</dt><dd>{r.misread_risks.join('; ')}</dd></>}
                {r.interested_subgroups.length > 0 && <><dt>Interested</dt><dd>{r.interested_subgroups.map((g) => `${g.who} (${pct(g.share_of_segment_pct)})`).join('; ')}</dd></>}
              </dl>
            </article>
          )
        })}
      </div>
    </Panel>
  )
}

function Results({ sim }: { sim: Simulation }) {
  const client = useQueryClient()
  const cancel = useMutation({ mutationFn: cancelSimulation, onSuccess: () => client.invalidateQueries({ queryKey: ['lab', 'simulation', sim.simulation_id] }) })
  if (isActive(sim.status)) {
    return <Panel title="Running test"><LiveProgress progress={sim.progress} status={sim.status} onCancel={() => cancel.mutate(sim.simulation_id)} cancelling={cancel.isPending} /></Panel>
  }
  if (sim.status === 'FAILED' || sim.status === 'CANCELLED') {
    return <Panel title={sim.status === 'CANCELLED' ? 'Test cancelled' : 'Test failed'}><Notice tone="error">{sim.error}</Notice><JobEvents progress={sim.progress} /></Panel>
  }
  const baseline = sim.baseline
  const analysis = sim.analysis
  if (!baseline) return null
  const interested = baseline.interested_audience
  return (
    <>
      <Panel
        flush
        title={analysis?.headline ?? 'Audience reaction'}
        description={`${platformLabel(sim.platform)} · ${baseline.segments.length} agents${sim.status === 'PARTIAL' ? ' · some agents failed' : ''} · ${sim.model_name}`}
        actions={analysis && <Status status={VERDICT_TONE[analysis.verdict] ?? 'neutral'} label={VERDICTS[analysis.verdict]} />}
      >
        {analysis && <p className="lab-summary">{analysis.summary}</p>}
        <div style={{ padding: '0 16px 12px' }}><ReactionStats metrics={baseline.weighted} /></div>
        <MixTable segments={baseline.segments} />
      </Panel>
      <div className="grid">
        <Panel className="col-6" title="Who is interested" description={`${pct(interested.interested_share_of_audience_pct, 1)} of the simulated audience`}>
          {analysis?.interested_audience_profile && <p style={{ marginBottom: 14, fontSize: 13.5 }}>{analysis.interested_audience_profile}</p>}
          <Bars label="Share of interested audience by segment" items={interested.by_segment.map((s) => ({ label: s.segment, value: s.pct_of_interested, display: pct(s.pct_of_interested) }))} max={100} />
          {Object.keys(interested.attributes).length > 0 && (
            <dl className="kv" style={{ marginTop: 16, fontSize: 12.5 }}>
              {Object.entries(interested.attributes).slice(0, 8).map(([key, values]) => <div key={key} style={{ display: 'contents' }}><dt>{key.replaceAll('_', ' ')}</dt><dd>{values.slice(0, 4).map((v) => `${v.value} ${v.pct.toFixed(0)}%`).join(', ')}</dd></div>)}
            </dl>
          )}
        </Panel>
        {analysis && (
          <Panel className="col-6" title="Recommendations">
            <ol className="lab-recs">
              {analysis.recommendations.map((rec) => (
                <li key={rec.change}>
                  <div><strong>{rec.change}</strong> <span className={`faint lab-priority lab-priority--${rec.priority}`}>{rec.priority} priority</span></div>
                  <p>{rec.rationale}</p>
                  {(rec.segments_helped.length > 0 || rec.segments_at_risk.length > 0) && <p className="faint" style={{ fontSize: 12 }}>{rec.segments_helped.length > 0 && <>Helps {rec.segments_helped.join(', ')}. </>}{rec.segments_at_risk.length > 0 && <>Risk for {rec.segments_at_risk.join(', ')}.</>}</p>}
                </li>
              ))}
            </ol>
            {(analysis.key_insights.length > 0 || analysis.risks.length > 0) && (
              <dl className="kv" style={{ marginTop: 16, fontSize: 12.5 }}>
                {analysis.key_insights.length > 0 && <><dt>Insights</dt><dd><ul className="lab-list">{analysis.key_insights.map((t) => <li key={t}>{t}</li>)}</ul></dd></>}
                {analysis.risks.length > 0 && <><dt>Risks</dt><dd><ul className="lab-list">{analysis.risks.map((t) => <li key={t}>{t}</li>)}</ul></dd></>}
              </dl>
            )}
          </Panel>
        )}
      </div>
      <UpliftPanel uplift={sim.uplift} improved={sim.improved_post} original={sim.post_text} />
      <AgentResponses segments={baseline.segments} />
      <JobEvents progress={sim.progress} />
    </>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function AudienceLabPage() {
  const client = useQueryClient()
  const [segmentationId, setSegmentationId] = useState<string | null>(null)
  const [simulationId, setSimulationId] = useState<string | null>(null)

  const labStatus = useQuery({ queryKey: ['lab', 'status'], queryFn: getLabStatus })
  const runs = useQuery({ queryKey: ['lab', 'segmentations'], queryFn: () => listSegmentations(5) })
  const activeSegId = segmentationId ?? runs.data?.find((r) => r.status !== 'FAILED' && r.status !== 'CANCELLED')?.segmentation_id ?? runs.data?.[0]?.segmentation_id ?? null
  const segmentation = useQuery({
    queryKey: ['lab', 'segmentation', activeSegId],
    queryFn: () => getSegmentation(activeSegId as string),
    enabled: Boolean(activeSegId),
    refetchInterval: (q) => (isActive(q.state.data?.status) ? 2000 : false),
  })
  const history = useQuery({ queryKey: ['lab', 'simulations'], queryFn: () => listSimulations(12) })
  const simulation = useQuery({
    queryKey: ['lab', 'simulation', simulationId],
    queryFn: () => getSimulation(simulationId as string),
    enabled: Boolean(simulationId),
    refetchInterval: (q) => (isActive(q.state.data?.status) ? 2000 : false),
  })
  const simStatus = simulation.data?.status
  useEffect(() => {
    if (simStatus && !isActive(simStatus)) void client.invalidateQueries({ queryKey: ['lab', 'simulations'] })
  }, [simStatus, client])

  return (
    <div className="page audience-lab">
      <PageHeader title="Audience Lab" description="Test a post against AI agents that each represent one segment of your audience" />
      <div className="grid">
        <Composer segmentation={segmentation.data} platforms={labStatus.data?.platforms ?? []} onStarted={(id) => { setSimulationId(id); void client.invalidateQueries({ queryKey: ['lab', 'simulations'] }) }} />
        <AudienceData />
      </div>
      {simulation.error && <ErrorState error={simulation.error} />}
      {simulation.data && <Results sim={simulation.data} />}
      {runs.error ? <ErrorState error={runs.error} /> : <SegmentsPanel segmentation={segmentation.data} onBuilt={(id) => { setSegmentationId(id); void client.invalidateQueries({ queryKey: ['lab'] }) }} />}
      {history.data && history.data.length > 0 && (
        <Panel flush title="Previous tests">
          <div className="table-wrap"><table className="table">
            <thead><tr><th>Post</th><th>Result</th><th>Platform</th><th>When</th></tr></thead>
            <tbody>
              {history.data.map((h) => (
                <tr key={h.simulation_id} className="is-clickable" tabIndex={0} onClick={() => { setSimulationId(h.simulation_id); window.scrollTo?.({ top: 0, behavior: 'smooth' }) }} onKeyDown={(e) => { if (e.key === 'Enter') setSimulationId(h.simulation_id) }} style={h.simulation_id === simulationId ? { background: 'var(--surface-2)' } : undefined}>
                  <td style={{ maxWidth: 420 }}><span className="clamp-2" style={{ color: 'var(--text)' }}>{h.post_text}</span></td>
                  <td>{h.headline ?? <Status status={h.status} />}</td>
                  <td>{platformLabel(h.platform)}</td>
                  <td className="num" style={{ whiteSpace: 'nowrap' }}>{h.created_at ? timeAgo(h.created_at) : '–'}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </Panel>
      )}
    </div>
  )
}
