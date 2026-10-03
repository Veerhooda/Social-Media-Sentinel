export function Segmented<T extends string>({ value, options, onChange, label, disabled }: {
  value: T
  options: readonly T[] | { value: T; label: string }[]
  onChange: (value: T) => void
  label: string
  disabled?: (value: T) => boolean
}) {
  const items = (options as readonly (T | { value: T; label: string })[]).map((option) =>
    typeof option === 'string' ? { value: option, label: option } : option,
  )
  return (
    <div className="segmented" role="group" aria-label={label}>
      {items.map((item) => (
        <button key={item.value} type="button" aria-pressed={item.value === value} disabled={disabled?.(item.value)} onClick={() => onChange(item.value)}>
          {item.label}
        </button>
      ))}
    </div>
  )
}
