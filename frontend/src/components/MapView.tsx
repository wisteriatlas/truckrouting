import * as maplibregl from 'maplibre-gl'
import type { GeoJSONSource, MapGeoJSONFeature, MapMouseEvent } from 'maplibre-gl'
import type * as GeoJSON from 'geojson'
import 'maplibre-gl/dist/maplibre-gl.css'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { useEffect, useMemo, useRef } from 'react'
import { RISK_COLORS, fmtDateTime, routeName } from '../risk'
import type { HeatmapData, Route } from '../types'

interface Props {
  routes: Route[]
  selectedId: number
  heatmap: HeatmapData | null
  hour: number
  showHeat: boolean
  focus: { lat: number; lon: number; n: number } | null
  onSelect: (id: number) => void
}

maplibregl.setWorkerUrl(workerUrl)

type FC = GeoJSON.FeatureCollection
const EMPTY: FC = { type: 'FeatureCollection', features: [] }

const STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '© OpenStreetMap contributors',
    },
  },
  layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
}

const riskMatch = (prop: string): maplibregl.ExpressionSpecification => [
  'match', ['get', prop],
  0, RISK_COLORS[0], 1, RISK_COLORS[1], 2, RISK_COLORS[2], 3, RISK_COLORS[3], RISK_COLORS[4],
]

export default function MapView({ routes, selectedId, heatmap, hour, showHeat, focus, onSelect }: Props) {
  const el = useRef<HTMLDivElement>(null)
  const map = useRef<maplibregl.Map | null>(null)
  const ready = useRef(false)
  const markers = useRef<maplibregl.Marker[]>([])
  const onSelectRef = useRef(onSelect)
  const raf = useRef(0)
  onSelectRef.current = onSelect

  // Static GeoJSON derived from the analysis result.
  const routeFC = useMemo<FC>(() => ({
    type: 'FeatureCollection',
    features: routes.map((r) => ({
      type: 'Feature',
      properties: { id: r.id, color: r.color, selected: r.id === selectedId ? 1 : 0, rec: r.recommended ? 1 : 0 },
      geometry: { type: 'LineString', coordinates: r.geometry },
    })),
  }), [routes, selectedId])

  const cpFC = useMemo<FC>(() => ({
    type: 'FeatureCollection',
    features: routes.flatMap((r) =>
      r.checkpoints.map((c) => ({
        type: 'Feature' as const,
        properties: {
          route: r.id, color: r.color, selected: r.id === selectedId ? 1 : 0, risk: c.risk,
          label: c.risk_label, mile: c.mile, eta: c.eta, wind: c.wind_mph, rain: c.rain_in_hr, snow: c.snow_in_hr,
        },
        geometry: { type: 'Point' as const, coordinates: [c.lon, c.lat] },
      })),
    ),
  }), [routes, selectedId])

  const heatFC = (h: HeatmapData | null, hr: number): FC =>
    !h ? EMPTY : {
      type: 'FeatureCollection',
      features: h.points.map(([lat, lon, scores]) => ({
        type: 'Feature' as const,
        properties: { w: scores[Math.min(hr, scores.length - 1)] },
        geometry: { type: 'Point' as const, coordinates: [lon, lat] },
      })),
    }

  const setData = (id: string, data: FC) => {
    if (ready.current) (map.current?.getSource(id) as GeoJSONSource | undefined)?.setData(data)
  }

  // Create the map once.
  useEffect(() => {
    const m = new maplibregl.Map({ container: el.current!, style: STYLE, center: [-96, 38.5], zoom: 3.6 })
    map.current = m
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')

    m.on('load', () => {
      m.addSource('heat', { type: 'geojson', data: EMPTY })
      m.addSource('routes', { type: 'geojson', data: EMPTY })
      m.addSource('cps', { type: 'geojson', data: EMPTY })

      // Smooth "heatmap": large blurred circles coloured by risk level, so the colour
      // always means the real risk level (a density heatmap would inflate where points overlap).
      m.addLayer({
        id: 'heat', type: 'circle', source: 'heat',
        paint: {
          'circle-radius': ['interpolate', ['exponential', 2], ['zoom'], 3, 14, 6, 60, 9, 260, 12, 900],
          'circle-blur': 1,
          'circle-color': riskMatch('w'),
          'circle-opacity': ['match', ['get', 'w'], 0, 0.28, 1, 0.5, 0.62],
        },
      })
      m.addLayer({
        id: 'route-casing', type: 'line', source: 'routes',
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': '#fff', 'line-width': ['case', ['==', ['get', 'selected'], 1], 9, 6], 'line-opacity': 0.9 },
      })
      m.addLayer({
        id: 'route-line', type: 'line', source: 'routes',
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: {
          'line-color': ['get', 'color'],
          'line-width': ['case', ['==', ['get', 'selected'], 1], 5, 3],
          'line-opacity': ['case', ['==', ['get', 'selected'], 1], 1, 0.65],
        },
      })
      m.addLayer({
        id: 'cps', type: 'circle', source: 'cps',
        paint: {
          'circle-radius': ['case', ['==', ['get', 'selected'], 1], 6, 3.5],
          'circle-color': riskMatch('risk'),
          'circle-stroke-color': '#fff',
          'circle-stroke-width': ['case', ['==', ['get', 'selected'], 1], 2, 1],
        },
      })

      m.on('click', 'route-line', (e: MapMouseEvent & { features?: MapGeoJSONFeature[] }) => {
        const f = e.features?.[0]
        if (f) onSelectRef.current(Number(f.properties.id))
      })
      m.on('click', 'cps', (e: MapMouseEvent & { features?: MapGeoJSONFeature[] }) => {
        const f = e.features?.[0] as MapGeoJSONFeature | undefined
        if (!f) return
        const p = f.properties
        const coords = (f.geometry as GeoJSON.Point).coordinates as [number, number]
        new maplibregl.Popup({ offset: 10 })
          .setLngLat(coords)
          .setHTML(
            `<strong>${routeName(Number(p.route))} · mile ${Math.round(Number(p.mile))}</strong><br/>` +
            `ETA ${fmtDateTime(String(p.eta))}<br/>` +
            `Wind ${Number(p.wind).toFixed(0)} mph · Rain ${Number(p.rain).toFixed(2)} in/hr · Snow ${Number(p.snow).toFixed(2)} in/hr<br/>` +
            `<b style="color:${RISK_COLORS[Number(p.risk)]}">${p.label}</b>`,
          )
          .addTo(m)
      })
      for (const id of ['route-line', 'cps']) {
        m.on('mouseenter', id, () => (m.getCanvas().style.cursor = 'pointer'))
        m.on('mouseleave', id, () => (m.getCanvas().style.cursor = ''))
      }
      ready.current = true
      // Push any data that arrived before the style finished loading.
      setData('routes', routeFC)
      setData('cps', cpFC)
      setData('heat', heatFC(heatmap, hour))
      m.setLayoutProperty('heat', 'visibility', showHeat ? 'visible' : 'none')
    })

    return () => {
      ready.current = false
      m.remove()
      map.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => setData('routes', routeFC), [routeFC])
  useEffect(() => setData('cps', cpFC), [cpFC])

  // Slider updates are coalesced to one repaint per frame.
  useEffect(() => {
    cancelAnimationFrame(raf.current)
    raf.current = requestAnimationFrame(() => setData('heat', heatFC(heatmap, hour)))
    return () => cancelAnimationFrame(raf.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [heatmap, hour])

  useEffect(() => {
    if (ready.current) map.current?.setLayoutProperty('heat', 'visibility', showHeat ? 'visible' : 'none')
  }, [showHeat])

  // Fit view and place origin/destination markers when a new analysis arrives.
  useEffect(() => {
    const m = map.current
    markers.current.forEach((mk) => mk.remove())
    markers.current = []
    if (!m || routes.length === 0) return
    const bounds = new maplibregl.LngLatBounds()
    routes.forEach((r) => r.geometry.forEach((c) => bounds.extend(c)))
    m.fitBounds(bounds, { padding: 60, duration: 800 })
    const first = routes[0].geometry
    const mk = (c: [number, number], text: string, color: string) =>
      new maplibregl.Marker({ color }).setLngLat(c).setPopup(new maplibregl.Popup().setText(text)).addTo(m)
    markers.current = [mk(first[0], 'Origin', '#16a34a'), mk(first[first.length - 1], 'Destination', '#dc2626')]
    // Only refit when the set of routes changes, not on selection.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routes.map((r) => r.id + ':' + r.distance_mi).join('|')])

  useEffect(() => {
    if (focus) map.current?.flyTo({ center: [focus.lon, focus.lat], zoom: Math.max(map.current.getZoom(), 8), duration: 600 })
  }, [focus])

  return <div ref={el} className="map" />
}
