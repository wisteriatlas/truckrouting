import { useState } from 'react'
import type { AnalyzeRequest, Place } from '../types'
import PlaceInput from './PlaceInput'

interface Props {
  loading: boolean
  onSubmit: (req: AnalyzeRequest) => void
}

function defaultDeparture(): string {
  const d = new Date(Date.now() + 60 * 60 * 1000)
  d.setMinutes(0, 0, 0)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:00`
}

export default function SearchForm({ loading, onSubmit }: Props) {
  const [origin, setOrigin] = useState<Place | null>(null)
  const [destination, setDestination] = useState<Place | null>(null)
  const [departure, setDeparture] = useState(defaultDeparture)
  const [load, setLoad] = useState('40000')

  const loadNum = Number(load)
  const loadValid = load !== '' && Number.isFinite(loadNum) && loadNum >= 0 && loadNum <= 200000
  const ready = origin && destination && departure && loadValid

  function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!ready) return
    onSubmit({
      origin: { lat: origin.lat, lon: origin.lon },
      destination: { lat: destination.lat, lon: destination.lon },
      departure_time: new Date(departure).toISOString(),
      load_lb: loadNum,
    })
  }

  return (
    <form onSubmit={submit} className="form">
      <PlaceInput label="Origin" value={origin} onChange={setOrigin} />
      <PlaceInput label="Destination" value={destination} onChange={setDestination} />
      <div className="row">
        <label className="field">
          <span>Departure</span>
          <input type="datetime-local" value={departure} onChange={(e) => setDeparture(e.target.value)} required />
        </label>
        <label className="field">
          <span>Load (lb)</span>
          <input
            type="number"
            min={0}
            max={200000}
            step={500}
            value={load}
            onChange={(e) => setLoad(e.target.value)}
            aria-invalid={!loadValid}
          />
        </label>
      </div>
      <button type="submit" disabled={!ready || loading}>
        {loading ? (
          <>
            <i className="spinner" /> Analyzing routes…
          </>
        ) : (
          'Find safest route'
        )}
      </button>
      {!origin && !destination ? null : (!origin || !destination) && (
        <p className="hint">Pick origin and destination from the suggestions.</p>
      )}
    </form>
  )
}
