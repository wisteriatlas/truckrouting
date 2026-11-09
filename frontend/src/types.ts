export interface Place {
  label: string
  lat: number
  lon: number
}

export interface Checkpoint {
  mile: number
  lat: number
  lon: number
  eta: string
  wind_mph: number
  rain_in_hr: number
  snow_in_hr: number
  risk: number
  risk_label: string
}

export interface RouteSummary {
  no_travel_miles: number
  severe_miles: number
  high_miles: number
  moderate_miles: number
  low_miles: number
  avg_risk: number
  max_risk: string
}

export interface Route {
  id: number
  color: string
  distance_mi: number
  duration_s: number
  arrival: string
  geometry: [number, number][]
  checkpoints: Checkpoint[]
  summary: RouteSummary
  recommended: boolean
}

export interface HeatmapData {
  start: string
  hours: number
  points: [number, number, number[]][]
}

export interface AnalyzeResult {
  routes: Route[]
  recommended_id: number | null
  recommendation_reason: string
  heatmap: HeatmapData
  warnings: string[]
}

export interface AnalyzeRequest {
  origin: { lat: number; lon: number }
  destination: { lat: number; lon: number }
  departure_time: string
  load_lb: number
}
