import { API_BASE_URL } from './apiConfig';

export type TurtleGuardStatus = {
  zone_name: string;
  days_per_period: number;
  zone_area_km2: number;
  current_total_apparent_fishing_hours: number;
  current_density_hours_per_km2_per_day: number;
  reference_total_apparent_fishing_hours: number;
  reference_density_hours_per_km2_per_day: number;
  alert_multiplier: number;
  threshold_density_hours_per_km2_per_day: number | null;
  activity_ratio: number | null;
  risk_status: 'high' | 'low' | 'needs_more_reference_data';
  message: string;
  source: string;
  note: string;
};

export async function fetchTurtleGuardStatus(): Promise<TurtleGuardStatus> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/turtleguard/status`);
  } catch {
    throw new Error('Could not reach TurtleGuard. Check that the backend is running and the API URL is correct.');
  }
  if (!response.ok) {
    throw new Error(`TurtleGuard status is unavailable (HTTP ${response.status}).`);
  }
  return response.json() as Promise<TurtleGuardStatus>;
}
