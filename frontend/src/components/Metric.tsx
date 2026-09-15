type Props = { label: string; value: number | string; hint?: string };

export function Metric({ label, value, hint }: Props) {
  return (
    <div className="metric">
      <span className="metric-label">{label}</span>
      <strong>{value}</strong>
      {hint && <span className="metric-hint">{hint}</span>}
    </div>
  );
}

