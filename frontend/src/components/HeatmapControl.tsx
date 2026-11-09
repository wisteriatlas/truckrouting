import { useEffect, useState } from 'react'
import { RISK_COLORS, RISK_LABELS } from '../risk'

interface Props {
  start: string
  hour: number
  max: number
  show: boolean
  onHour: (h: number) => void
  onShow: (v: boolean) => void
}

export default function HeatmapControl({ start, hour, max, show, onHour, onShow }: Props) {
  const [playing, setPlaying] = useState(false)
  const when = new Date(new Date(start).getTime() + hour * 3600_000)

  useEffect(() => {
    if (!playing) return
    const t = window.setInterval(() => onHour(hour >= max ? 0 : hour + 1), 450)
    return () => window.clearInterval(t)
  }, [playing, hour, max, onHour])

  return (
    <div className="heat-control">
      <div className="heat-top">
        <label className="toggle">
          <input type="checkbox" checked={show} onChange={(e) => onShow(e.target.checked)} /> Weather heatmap
        </label>
        <button type="button" className="ghost" onClick={() => setPlaying((p) => !p)} disabled={!show}>
          {playing ? 'Pause' : 'Play'}
        </button>
        <strong>
          +{hour} h · {when.toLocaleString([], { weekday: 'short', hour: 'numeric' })}
        </strong>
      </div>
      <input
        type="range"
        min={0}
        max={max}
        value={hour}
        disabled={!show}
        onChange={(e) => onHour(Number(e.target.value))}
        aria-label="Forecast hour"
      />
      <div className="legend">
        {RISK_LABELS.map((l, i) => (
          <span key={l}>
            <i style={{ background: RISK_COLORS[i] }} />
            {l}
          </span>
        ))}
      </div>
    </div>
  )
}
