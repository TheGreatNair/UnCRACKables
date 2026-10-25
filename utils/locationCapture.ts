import type { ReportLocationSource } from './reportStorage';

export type CapturedCoordinates = {
  latitude: number;
  longitude: number;
};

export type LocationFailureCode =
  | 'permission-denied'
  | 'services-disabled'
  | 'timeout'
  | 'invalid-coordinates';

export class LocationCaptureError extends Error {
  readonly code: LocationFailureCode;

  constructor(code: LocationFailureCode) {
    super(code);
    this.name = 'LocationCaptureError';
    this.code = code;
  }
}

type CaptureDependencies = {
  requestForegroundPermission: () => Promise<{ status: string; canAskAgain: boolean }>;
  areLocationServicesEnabled: () => Promise<boolean>;
  getCoordinates: () => Promise<CapturedCoordinates>;
};

export async function captureCurrentLocation(
  dependencies: CaptureDependencies,
  timeoutMs = 15_000,
): Promise<CapturedCoordinates> {
  const permission = await dependencies.requestForegroundPermission();
  if (permission.status !== 'granted') {
    throw new LocationCaptureError('permission-denied');
  }

  if (!(await dependencies.areLocationServicesEnabled())) {
    throw new LocationCaptureError('services-disabled');
  }

  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new LocationCaptureError('timeout')), timeoutMs);
  });

  try {
    const coordinates = await Promise.race([dependencies.getCoordinates(), timeout]);
    if (
      !Number.isFinite(coordinates.latitude) || coordinates.latitude < -90 || coordinates.latitude > 90 ||
      !Number.isFinite(coordinates.longitude) || coordinates.longitude < -180 || coordinates.longitude > 180
    ) {
      throw new LocationCaptureError('invalid-coordinates');
    }
    return coordinates;
  } finally {
    if (timer !== undefined) clearTimeout(timer);
  }
}

export function buildReportLocation(
  source: 'gps' | 'preset',
  sector: string,
  coordinates?: CapturedCoordinates | null,
): {
  sector: string;
  locationSource: ReportLocationSource;
  locationName: string;
  latitude?: number;
  longitude?: number;
} {
  if (source === 'preset') {
    return { sector, locationSource: 'preset', locationName: sector };
  }
  if (!coordinates) throw new LocationCaptureError('invalid-coordinates');
  return {
    sector: 'Current Location',
    locationSource: 'gps',
    locationName: 'Current Location',
    latitude: coordinates.latitude,
    longitude: coordinates.longitude,
  };
}
