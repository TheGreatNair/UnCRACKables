import AsyncStorage from '@react-native-async-storage/async-storage';

export const REPORTS_STORAGE_KEY = '@turtleway/reports';

export type ReportLocationSource = 'gps' | 'preset' | 'manual';

export type FieldReport = {
  id: string;
  sector: string;
  type: string;
  notes: string;
  createdAt: string;
  timestamp: string;
  syncStatus: 'pending' | 'synced';
  reviewStatus: string;
  latitude?: number;
  longitude?: number;
  locationSource?: ReportLocationSource;
  locationName?: string;
  /** Local binding prevents another signed-in account syncing this queued report. */
  syncOwnerId?: string;
};

let writes = Promise.resolve();

export function readReports(): Promise<FieldReport[]> {
  return AsyncStorage.getItem(REPORTS_STORAGE_KEY).then((raw) => {
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) throw new Error('Stored reports are not an array');
    return parsed as FieldReport[];
  });
}

export function updateReports(
  transform: (reports: FieldReport[]) => FieldReport[],
): Promise<FieldReport[]> {
  const operation = writes.then(async () => {
    const current = await readReports();
    const updated = transform(current);
    await AsyncStorage.setItem(REPORTS_STORAGE_KEY, JSON.stringify(updated));
    return updated;
  });
  writes = operation.then(() => undefined, () => undefined);
  return operation;
}
