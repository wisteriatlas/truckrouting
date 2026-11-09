export const RISK_LABELS = ['Low', 'Moderate', 'High', 'Severe', 'No Travel']
export const RISK_COLORS = ['#22c55e', '#eab308', '#f97316', '#dc2626', '#1f2937']

export const routeName = (id: number) => `Route ${String.fromCharCode(65 + id)}`

export function fmtDuration(seconds: number): string {
  const m = Math.round(seconds / 60)
  const h = Math.floor(m / 60)
  return h ? `${h} h ${m % 60} min` : `${m} min`
}

export function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}
