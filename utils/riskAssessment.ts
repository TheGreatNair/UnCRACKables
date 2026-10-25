import { API_BASE_URL } from './apiConfig';

export type FishingRisk = {
  zoneName: string;
  riskStatus: 'high' | 'low' | 'needs_more_reference_data';
  message: string;
  dataAsOf: string | null;
  dataAgeDays: number | null;
  currentPeriodApparentFishingHours: number;
  referencePeriodApparentFishingHours: number;
  currentDensityHoursPerKm2PerDay: number;
  referenceDensityHoursPerKm2PerDay: number;
  alertThresholdDensityHoursPerKm2PerDay: number | null;
  activityRatio: number | null;
  alertMultiplier: number;
  daysPerPeriod: number;
  zoneAreaKm2: number;
  source: string;
  limitations: string;
  snapshotNote: string;
};

export async function fetchFishingRisk(): Promise<FishingRisk> {
  const response = await fetch(`${API_BASE_URL}/risk/fishing-activity`);
  if (!response.ok) {
    throw new Error(response.status === 503
      ? 'Risk data is temporarily unavailable. Try again later.'
      : `Could not load the risk assessment (HTTP ${response.status}).`);
  }
  return response.json() as Promise<FishingRisk>;
}
