import { useCallback, useState } from 'react'
import { analyze } from './api'
import HeatmapControl from './components/HeatmapControl'
import MapView from './components/MapView'
import RouteCards from './components/RouteCards'
import SearchForm from './components/SearchForm'
import type { AnalyzeRequest, AnalyzeResult } from './types'

export default function App() {
  const [result, setResult] = useState<AnalyzeResult | null>(null)
  const [selectedId, setSelectedId] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [hour, setHour] = useState(0)
  const [showHeat, setShowHeat] = useState(true)
  const [focus, setFocus] = useState<{ lat: number; lon: number; n: number } | null>(null)

  async function run(req: AnalyzeRequest) {
    setLoading(true)
    setError('')
    try {
      const res = await analyze(req)
      setResult(res)
      setSelectedId(res.recommended_id ?? 0)
      // Start the heatmap slider at the departure hour.
      const h = Math.round((new Date(req.departure_time).getTime() - new Date(res.heatmap.start).getTime()) / 3600_000)
      setHour(Math.min(Math.max(h, 0), res.heatmap.hours - 1))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  const onFocus = useCallback((lat: number, lon: number) => setFocus({ lat, lon, n: Date.now() }), [])

  return (
    <div className="app">
      <aside className="panel">
        <h1>Weather-Aware Truck Routing</h1>
        <p className="sub">Pick the safest route for your load, departure time and forecast.</p>
        <SearchForm loading={loading} onSubmit={run} />
        {error && <div className="error" role="alert">{error}</div>}
        {result?.warnings.map((w) => (
          <div className="warn" key={w}>{w}</div>
        ))}
        {result && (
          <RouteCards
            routes={result.routes}
            selectedId={selectedId}
            reason={result.recommendation_reason}
            onSelect={setSelectedId}
            onFocusCheckpoint={onFocus}
          />
        )}
      </aside>
      <main className="stage">
        <MapView
          routes={result?.routes ?? []}
          selectedId={selectedId}
          heatmap={result?.heatmap ?? null}
          hour={hour}
          showHeat={showHeat}
          focus={focus}
          onSelect={setSelectedId}
        />
        {loading && (
          <div className="overlay">
            <i className="spinner" /> Fetching routes and forecasts…
          </div>
        )}
        {result && (
          <HeatmapControl
            start={result.heatmap.start}
            hour={hour}
            max={result.heatmap.hours - 1}
            show={showHeat}
            onHour={setHour}
            onShow={setShowHeat}
          />
        )}
      </main>
    </div>
  )
}
