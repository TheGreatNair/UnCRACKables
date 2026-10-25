export type EggRiskTier = 'GREEN' | 'YELLOW' | 'RED';

export type EggRiskInput = {
  sector: string;
  nestId: string;
  sandTemperatureC: number;
  beachLightLux: number;
  daysUntilEmergence: number;
};

export type EggRiskAssessment = EggRiskInput & {
  score: number;
  tier: EggRiskTier;
  action: string;
};

// Fixed demonstration inputs only. They are not sourced from live sensors or APIs.
const DEMO_NESTS: Record<string, EggRiskInput> = {
  'Sasihithlu Delta': { sector: 'Sasihithlu Delta', nestId: 'DEMO-SAS-001', sandTemperatureC: 30.1, beachLightLux: 0.2, daysUntilEmergence: 14 },
  Tannirbhavi: { sector: 'Tannirbhavi', nestId: 'DEMO-TAN-001', sandTemperatureC: 30.6, beachLightLux: 0.7, daysUntilEmergence: 4 },
  Panambur: { sector: 'Panambur', nestId: 'DEMO-PAN-001', sandTemperatureC: 31.2, beachLightLux: 1.2, daysUntilEmergence: 1 },
};

export function calculateEggRisk(input: EggRiskInput): EggRiskAssessment {
  const z = -4.5 + 3.869 * input.beachLightLux + 1.494 * (input.sandTemperatureC - 29) - 1.161 * input.daysUntilEmergence;
  const score = Math.round((1 / (1 + Math.exp(-z))) * 1000) / 10;
  const tier: EggRiskTier = ((input.daysUntilEmergence >= 0 && input.daysUntilEmergence <= 2 && input.beachLightLux >= 1.0) || input.sandTemperatureC >= 33.5)
    ? 'RED'
    : ((input.daysUntilEmergence >= 0 && input.daysUntilEmergence <= 4) || score >= 40) ? 'YELLOW' : 'GREEN';
  const action = tier === 'RED' ? 'Light curfew recommended: reduce nearby artificial light before hatch time.'
    : tier === 'YELLOW' ? 'Standby advisory: hatching is approaching; check beach lighting.'
      : 'Nominal demo conditions: continue routine nest protection.';
  return { ...input, score, tier, action };
}

export function getDemoEggRisk(sector: string): EggRiskAssessment {
  return calculateEggRisk(DEMO_NESTS[sector] ?? DEMO_NESTS.Panambur);
}
