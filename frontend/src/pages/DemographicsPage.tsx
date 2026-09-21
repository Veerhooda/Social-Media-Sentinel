import { Users } from 'lucide-react'
import { PageHeader } from '../components/PageHeader'
import { Panel } from '../components/Panel'
import { EmptyState, ErrorState, LoadingState } from '../components/States'
import { StatusBadge } from '../components/StatusBadge'
import { useDemographics } from '../hooks/useApiQueries'
import type { DimensionDistribution } from '../types/analytics'
import { formatNumber } from '../utils/format'

const DIMENSION_META: Record<string, { title: string; subtitle: string }> = {
  age: {
    title: 'Age Distribution',
    subtitle: 'Broad estimated brackets with explicit unknown handling.',
  },
  geography: {
    title: 'Geographic Distribution',
    subtitle: 'Aggregate of normalized public location strings. Never a precise residence.',
  },
  language: {
    title: 'Language Distribution',
    subtitle: 'Platform-observed codes preferred; text-based identification otherwise.',
  },
  profession: {
    title: 'Professional Interests',
    subtitle: 'Inferred interest sectors, not verified occupations.',
  },
}

function DimensionPanel({ dimension }: { dimension: DimensionDistribution }) {
  const meta = DIMENSION_META[dimension.dimension] ?? {
    title: dimension.dimension,
    subtitle: '',
  }
  const known = dimension.segments.filter((segment) => segment.label !== 'Unknown')
  const unknownShare = dimension.total_subjects
    ? dimension.unknown_count / dimension.total_subjects
    : 0
  return (
    <Panel
      title={meta.title}
      subtitle={`${meta.subtitle} Subjects: ${formatNumber(dimension.total_subjects)}`}
      action={<StatusBadge status={dimension.status} />}
      className="span-6"
    >
      {dimension.status === 'UNAVAILABLE' || dimension.status === 'ERROR' ? (
        <EmptyState
          title={dimension.dimension === 'age' ? 'Age estimates unavailable' : 'Dimension unavailable'}
          detail={
            dimension.dimension === 'age'
              ? 'The current corpus does not contain sufficient validated age evidence.'
              : dimension.detail
          }
        />
      ) : known.length === 0 ? (
        <EmptyState title="Insufficient data" detail={dimension.detail || 'No classifiable evidence for this dimension yet.'} />
      ) : (
        <>
        <div className="distribution-list">
          {known.map((segment) => (
            <div key={segment.label} title={`${formatNumber(segment.count)} subjects${segment.avg_confidence != null ? ` · mean confidence ${segment.avg_confidence.toFixed(2)}` : ''}`}>
              <span>{segment.label}</span>
              <div><i style={{ width: `${Math.max(2, segment.share * 100)}%` }} /></div>
              <b>{(segment.share * 100).toFixed(1)}%</b>
            </div>
          ))}
        </div>
        <p className="dimension-unknown">
          Unknown / insufficient evidence: {formatNumber(dimension.unknown_count)} ({(unknownShare * 100).toFixed(1)}%)
          {known.some((segment) => segment.avg_confidence != null) && ' · mean confidence shown on hover'}
        </p>
        </>
      )}
    </Panel>
  )
}

export function DemographicsPage() {
  const demographics = useDemographics()
  if (demographics.isLoading) return <LoadingState label="Loading aggregate demographics…" />
  if (demographics.error || !demographics.data) return <ErrorState error={demographics.error} />
  const data = demographics.data
  const order = ['age', 'geography', 'language', 'profession']
  return (
    <div className="page-stack">
      <PageHeader
        title="Audience Demographics"
        subtitle={`Aggregate estimates across ${formatNumber(data.total_subjects)} subjects. Estimates only — never personal facts.`}
        actions={<StatusBadge status={data.status} />}
      />
      <div className="insight-callout">
        <Users size={18} />
        <span>{data.detail}. Unknown cohorts are always included, never silently dropped.</span>
      </div>
      <div className="dashboard-grid">
        {order.map((key) =>
          data.dimensions[key] ? <DimensionPanel key={key} dimension={data.dimensions[key]} /> : null,
        )}
      </div>
    </div>
  )
}
