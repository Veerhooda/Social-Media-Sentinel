import { Bars } from '../components/Bars'
import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { Stat, Stats } from '../components/Stat'
import { EmptyState, ErrorState, LoadingState } from '../components/States'
import { useDemographics } from '../hooks/useApiQueries'
import type { DimensionDistribution } from '../types/analytics'
import { formatNumber, pct, sentenceCase } from '../utils/format'

const share = (ratio: number) => (ratio > 0 && ratio < 0.01 ? '<1%' : pct(ratio, 0))

const TITLES: Record<string, string> = { age: 'Age bracket', geography: 'Country', language: 'Language', profession: 'Professional sector' }

function DimensionPanel({ dimension }: { dimension: DimensionDistribution }) {
  const known = dimension.segments.filter((segment) => segment.label !== 'Unknown')
  const coverage = dimension.total_subjects ? 1 - dimension.unknown_count / dimension.total_subjects : 0
  const confidence = known.filter((segment) => segment.avg_confidence != null)
  const meanConfidence = confidence.length ? confidence.reduce((sum, segment) => sum + (segment.avg_confidence ?? 0) * segment.count, 0) / confidence.reduce((sum, segment) => sum + segment.count, 0) : null
  return (
    <Panel
      className="col-6"
      title={TITLES[dimension.dimension] ?? sentenceCase(dimension.dimension)}
      description={`${pct(coverage, 0)} of accounts have enough evidence${meanConfidence != null ? ` · mean confidence ${pct(meanConfidence, 0)}` : ''}`}
    >
      {dimension.status === 'UNAVAILABLE' || dimension.status === 'ERROR' ? (
        <EmptyState title="Not available" detail={dimension.detail} />
      ) : known.length === 0 ? (
        <EmptyState title="Not enough evidence yet" detail={dimension.detail} />
      ) : (
        <Bars
          label={TITLES[dimension.dimension] ?? dimension.dimension}
          items={known.slice(0, 10).map((segment) => ({ label: segment.label, value: segment.count, display: share(segment.count / Math.max(1, dimension.total_subjects - dimension.unknown_count)) }))}
        />
      )}
    </Panel>
  )
}

export function DemographicsPage() {
  const demographics = useDemographics()
  if (demographics.isLoading) return <div className="page"><LoadingState label="Loading demographics" /></div>
  if (demographics.error || !demographics.data) return <div className="page"><ErrorState error={demographics.error} /></div>
  const data = demographics.data
  const order = ['geography', 'language', 'profession', 'age']
  const covered = (key: string) => {
    const dimension = data.dimensions[key]
    return dimension ? dimension.total_subjects - dimension.unknown_count : null
  }
  return (
    <div className="page">
      <PageHeader title="Demographics" description={`Aggregate estimates inferred from public profile text and posts of ${formatNumber(data.total_subjects)} accounts. Shares are of accounts with evidence.`} />
      <Stats label="Coverage">
        <Stat label="Accounts" value={data.total_subjects} />
        {order.map((key) => <Stat key={key} label={`With ${TITLES[key]?.toLowerCase() ?? key}`} value={covered(key)} meta={data.dimensions[key] ? pct((covered(key) ?? 0) / Math.max(1, data.total_subjects), 0) : undefined} />)}
      </Stats>
      <div className="grid">
        {order.map((key) => (data.dimensions[key] ? <DimensionPanel key={key} dimension={data.dimensions[key]} /> : null))}
      </div>
      <p className="faint" style={{ fontSize: 12.5 }}>{data.detail}. Individual estimates are never shown; groups with too few accounts are withheld.</p>
    </div>
  )
}
