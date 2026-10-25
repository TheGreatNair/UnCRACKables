import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildReportLocation,
  captureCurrentLocation,
  LocationCaptureError,
} from '../utils/locationCapture.ts';

function mockDependencies(overrides = {}) {
  const calls = [];
  const dependencies = {
    requestForegroundPermission: async () => {
      calls.push('permission');
      return { status: 'granted', canAskAgain: true };
    },
    areLocationServicesEnabled: async () => {
      calls.push('services');
      return true;
    },
    getCoordinates: async () => {
      calls.push('coordinates');
      return { latitude: 12.8768, longitude: 74.8421 };
    },
    ...overrides,
  };
  return { dependencies, calls };
}

test('requests foreground permission then returns current coordinates', async () => {
  const { dependencies, calls } = mockDependencies();
  assert.deepEqual(await captureCurrentLocation(dependencies), {
    latitude: 12.8768,
    longitude: 74.8421,
  });
  assert.deepEqual(calls, ['permission', 'services', 'coordinates']);
});

test('does not request location when foreground permission is denied', async () => {
  const { dependencies, calls } = mockDependencies({
    requestForegroundPermission: async () => ({ status: 'denied', canAskAgain: true }),
  });
  await assert.rejects(captureCurrentLocation(dependencies), (error) =>
    error instanceof LocationCaptureError && error.code === 'permission-denied',
  );
  assert.deepEqual(calls, []);
});

test('reports disabled location services without requesting a position', async () => {
  const { dependencies, calls } = mockDependencies({ areLocationServicesEnabled: async () => false });
  await assert.rejects(captureCurrentLocation(dependencies), (error) =>
    error instanceof LocationCaptureError && error.code === 'services-disabled',
  );
  assert.deepEqual(calls, ['permission']);
});

test('times out a GPS request that does not resolve', async () => {
  const { dependencies } = mockDependencies({ getCoordinates: () => new Promise(() => {}) });
  await assert.rejects(captureCurrentLocation(dependencies, 5), (error) =>
    error instanceof LocationCaptureError && error.code === 'timeout',
  );
});

test('rejects coordinates outside the valid ranges', async () => {
  for (const coordinates of [
    { latitude: 90.1, longitude: 0 },
    { latitude: 0, longitude: -180.1 },
    { latitude: Number.NaN, longitude: 0 },
  ]) {
    const { dependencies } = mockDependencies({ getCoordinates: async () => coordinates });
    await assert.rejects(captureCurrentLocation(dependencies), (error) =>
      error instanceof LocationCaptureError && error.code === 'invalid-coordinates',
    );
  }
});

test('preset sectors keep their label and never invent coordinates', () => {
  assert.deepEqual(buildReportLocation('preset', 'Panambur'), {
    sector: 'Panambur', locationSource: 'preset', locationName: 'Panambur',
  });
});

test('GPS reports use Current Location and include the captured coordinates', () => {
  assert.deepEqual(buildReportLocation('gps', 'Panambur', {
    latitude: 12.8768,
    longitude: 74.8421,
  }), {
    sector: 'Current Location',
    locationSource: 'gps',
    locationName: 'Current Location',
    latitude: 12.8768,
    longitude: 74.8421,
  });
});
