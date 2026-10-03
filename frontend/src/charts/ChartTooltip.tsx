import type { TooltipContentProps } from 'recharts'

type Row = { name?: string | number; value?: unknown; color?: string; dataKey?: unknown }

/** Shared tooltip: label line + one row per series with a colour key and tabular value. */
export function ChartTooltip({ active, payload, label, labelFormatter, valueFormatter }: Partial<TooltipContentProps<number, string>> & {
  valueFormatter?: (value: number, key: string) => string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="chart-tooltip">
      <header>{labelFormatter ? labelFormatter(label, payload) : String(label)}</header>
      {(payload as unknown as Row[]).map((row) => (
        <div key={String(row.dataKey ?? row.name)}>
          <i className="dot" style={{ background: row.color }} />
          {row.name}
          <b>{valueFormatter ? valueFormatter(Number(row.value), String(row.dataKey)) : String(row.value)}</b>
        </div>
      ))}
    </div>
  )
}
