import { RISK_COLORS, fmtDateTime, fmtDuration, routeName } from '../risk'
import type { Route } from '../types'

interface Props {
  routes: Route[]
  selectedId: number
  reason: string
  onSelect: (id: number) => void
  onFocusCheckpoint: (lat: number, lon: number) => void
}

function RiskBar({ route }: { route: Route }) {
  const s = route.summary
  const parts = [s.low_miles, s.moderate_miles, s.high_miles, s.severe_miles, s.no_travel_miles]
  const total = parts.reduce((a, b) => a + b, 0) || 1
  return (
    <div className="riskbar" role="img" aria-label="Miles by risk level">
      {parts.map(
        (v, i) => v > 0 && <span key={i} style={{ width: `${(v / total) * 100}%`, background: RISK_COLORS[i] }} />,
      )}
    </div>
  )
}

export default function RouteCards({ routes, selectedId, reason, onSelect, onFocusCheckpoint }: Props) {
  const selected = routes.find((r) => r.id === selectedId)
  return (
    <div className="cards">
      {routes.map((r) => (
        <button
          key={r.id}
          className={`card ${r.id === selectedId ? 'selected' : ''}`}
          style={{ borderLeftColor: r.color }}
          onClick={() => onSelect(r.id)}
          aria-pressed={r.id === selectedId}
        >
          <div className="card-head">
            <strong>{routeName(r.id)}</strong>
            {r.recommended && <em className="badge">Recommended</em>}
            <span className={`maxrisk r${['Low', 'Moderate', 'High', 'Severe', 'No Travel'].indexOf(r.summary.max_risk)}`}>
              Max: {r.summary.max_risk}
            </span>
          </div>
          <div className="stats">
            <span>{Math.round(r.distance_mi)} mi</span>
            <span>{fmtDuration(r.duration_s)}</span>
            <span>Arrive {fmtDateTime(r.arrival)}</span>
          </div>
          <RiskBar route={r} />
          <div className="stats small">
            <span>Severe {Math.round(r.summary.severe_miles)} mi</span>
            <span>High {Math.round(r.summary.high_miles)} mi</span>
            <span>Avg risk {r.summary.avg_risk.toFixed(2)}</span>
            {r.summary.no_travel_miles > 0 && <b>No Travel {Math.round(r.summary.no_travel_miles)} mi</b>}
          </div>
          {r.recommended && reason && <p className="reason">{reason}</p>}
        </button>
      ))}

      {selected && (
        <details className="checkpoints" open>
          <summary>
            {routeName(selected.id)} checkpoints ({selected.checkpoints.length})
          </summary>
          <table>
            <thead>
              <tr>
                <th>Mile</th>
                <th>ETA</th>
                <th>Wind</th>
                <th>Rain</th>
                <th>Snow</th>
                <th>Risk</th>
              </tr>
            </thead>
            <tbody>
              {selected.checkpoints.map((c) => (
                <tr key={c.mile} onClick={() => onFocusCheckpoint(c.lat, c.lon)}>
                  <td>{Math.round(c.mile)}</td>
                  <td>{fmtDateTime(c.eta)}</td>
                  <td>{c.wind_mph.toFixed(0)} mph</td>
                  <td>{c.rain_in_hr.toFixed(2)}</td>
                  <td>{c.snow_in_hr.toFixed(2)}</td>
                  <td>
                    <span className="dot" style={{ background: RISK_COLORS[c.risk] }} />
                    {c.risk_label}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </div>
  )
}
