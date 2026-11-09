import { useEffect, useRef, useState } from 'react'
import { geocode } from '../api'
import type { Place } from '../types'

interface Props {
  label: string
  value: Place | null
  onChange: (p: Place | null) => void
}

export default function PlaceInput({ label, value, onChange }: Props) {
  const [text, setText] = useState(value?.label ?? '')
  const [options, setOptions] = useState<Place[]>([])
  const [open, setOpen] = useState(false)
  const [searching, setSearching] = useState(false)
  const timer = useRef<number>(0)
  const ctrl = useRef<AbortController | null>(null)

  useEffect(() => () => {
    window.clearTimeout(timer.current)
    ctrl.current?.abort()
  }, [])

  function onInput(v: string) {
    setText(v)
    onChange(null)
    window.clearTimeout(timer.current)
    ctrl.current?.abort()
    if (v.trim().length < 3) {
      setOptions([])
      return
    }
    timer.current = window.setTimeout(async () => {
      ctrl.current = new AbortController()
      setSearching(true)
      try {
        setOptions(await geocode(v, ctrl.current.signal))
        setOpen(true)
      } catch {
        /* aborted or unavailable: leave previous options */
      } finally {
        setSearching(false)
      }
    }, 300)
  }

  function pick(p: Place) {
    setText(p.label)
    setOptions([])
    setOpen(false)
    onChange(p)
  }

  return (
    <label className="field">
      <span>{label}</span>
      <div className="combo">
        <input
          value={text}
          placeholder="City or address"
          onChange={(e) => onInput(e.target.value)}
          onFocus={() => options.length && setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          aria-invalid={text.length > 0 && !value}
          autoComplete="off"
        />
        {searching && <i className="spinner small" aria-label="Searching" />}
        {open && options.length > 0 && (
          <ul role="listbox">
            {options.map((o, i) => (
              <li key={i} role="option" onMouseDown={() => pick(o)}>
                {o.label}
              </li>
            ))}
          </ul>
        )}
      </div>
    </label>
  )
}
