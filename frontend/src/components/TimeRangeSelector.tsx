export type TimeRange = '1H' | '6H' | '24H' | '7D'

export function TimeRangeSelector({ value, onChange }: { value: TimeRange; onChange: (range: TimeRange) => void }) {
  return (
    <div className="segmented-control" aria-label="Time range">
      {(['1H', '6H', '24H', '7D'] as TimeRange[]).map((range) => (
        <button
          key={range}
          type="button"
          className={range === value ? 'is-active' : ''}
          onClick={() => onChange(range)}
          aria-pressed={range === value}
        >
          {range}
        </button>
      ))}
    </div>
  )
}

