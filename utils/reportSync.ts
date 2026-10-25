import { API_BASE_URL } from './apiConfig';
import { FieldReport, readReports, updateReports } from './reportStorage';
import { supabase } from './supabase';

let activeSync: Promise<void> | null = null;
let syncRequestedAgain = false;
const listeners = new Set<() => void>();

export function subscribeToReportChanges(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function notifyReportChanges() {
  listeners.forEach((listener) => listener());
}

export function syncPendingReports(): Promise<void> {
  if (activeSync) {
    syncRequestedAgain = true;
    return activeSync;
  }

  activeSync = (async () => {
    await performSync();
    // A report may have been saved while the first pass was reading/sending.
    if (syncRequestedAgain) {
      syncRequestedAgain = false;
      await performSync();
    }
  })().finally(() => { activeSync = null; });
  return activeSync;
}

async function performSync(): Promise<void> {
  if (!supabase) return;
  const { data: sessionData, error: sessionError } = await supabase.auth.getSession();
  if (sessionError || !sessionData.session?.access_token) return;
  const session = sessionData.session;
  let reports: FieldReport[];
  try {
    reports = await readReports();
  } catch (error) {
    console.warn('TurtleWay could not read locally saved reports:', error);
    return;
  }

  for (const report of reports) {
    if (report.syncStatus === 'synced') continue;
    if (report.syncOwnerId && report.syncOwnerId !== session.user.id) continue;

    // Existing anonymous/offline reports are claimed once, before network I/O.
    // Later accounts on this device cannot submit another user's queued data.
    if (!report.syncOwnerId) {
      await updateReports((latest) => latest.map((item) => item.id === report.id && !item.syncOwnerId
        ? { ...item, syncOwnerId: session.user.id }
        : item));
      report.syncOwnerId = session.user.id;
      notifyReportChanges();
    }

    try {
      const sendReport = (accessToken: string) => fetch(`${API_BASE_URL}/reports`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${accessToken}` },
        body: JSON.stringify({
          id: report.id,
          sector: report.sector,
          type: report.type,
          notes: report.notes ?? '',
          timestamp: report.timestamp || report.createdAt,
          syncStatus: 'pending',
          reviewStatus: report.reviewStatus || 'not_reviewed',
          latitude: report.latitude,
          longitude: report.longitude,
          locationSource: report.locationSource,
          locationName: report.locationName,
        }),
      });
      let response = await sendReport(session.access_token);
      if (response.status === 401) {
        const refreshed = await supabase.auth.refreshSession();
        if (refreshed.error || !refreshed.data.session?.access_token) continue;
        response = await sendReport(refreshed.data.session.access_token);
      }

      if (!response.ok) {
        console.warn(`TurtleWay report ${report.id} sync failed: HTTP ${response.status}`);
        continue;
      }

      const result = await response.json();
      if (result?.success !== true || result?.report?.id !== report.id) {
        console.warn(`TurtleWay report ${report.id} sync was not confirmed by the server.`);
        continue;
      }

      await updateReports((latest) => latest.map((item) =>
        item.id === report.id && item.syncStatus !== 'synced'
          ? { ...item, syncStatus: 'synced', syncOwnerId: session.user.id }
          : item,
      ));
      notifyReportChanges();
    } catch (error) {
      console.warn(`TurtleWay report ${report.id} sync failed; it remains saved on this device:`, error);
    }
  }

  await refreshOwnReports(session.access_token, session.user.id);
}

type ServerReport = {
  id: string;
  sector: string;
  type: string;
  notes: string;
  timestamp: string;
  latitude?: number | null;
  longitude?: number | null;
  locationSource?: FieldReport['locationSource'] | null;
  locationName?: string | null;
  reviewStatus: string;
};

async function refreshOwnReports(initialToken: string, ownerId: string): Promise<void> {
  if (!supabase) return;
  const load = (token: string) => fetch(`${API_BASE_URL}/reports?limit=100`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  try {
    let response = await load(initialToken);
    if (response.status === 401) {
      const refreshed = await supabase.auth.refreshSession();
      if (refreshed.error || !refreshed.data.session?.access_token) return;
      response = await load(refreshed.data.session.access_token);
    }
    if (!response.ok) {
      console.warn(`TurtleWay report refresh failed: HTTP ${response.status}`);
      return;
    }
    const serverReports = await response.json() as ServerReport[];
    await updateReports((localReports) => {
      const localById = new Map(localReports.map((report) => [report.id, report]));
      const remoteIds = new Set(serverReports.map((report) => report.id));
      const merged: FieldReport[] = serverReports.map((remote) => ({
        ...localById.get(remote.id),
        id: remote.id,
        sector: remote.sector,
        type: remote.type,
        notes: remote.notes,
        timestamp: remote.timestamp,
        createdAt: remote.timestamp,
        syncStatus: 'synced',
        reviewStatus: remote.reviewStatus,
        latitude: remote.latitude ?? undefined,
        longitude: remote.longitude ?? undefined,
        locationSource: remote.locationSource ?? undefined,
        locationName: remote.locationName ?? undefined,
        syncOwnerId: ownerId,
      }));
      return [...merged, ...localReports.filter((report) => !remoteIds.has(report.id))];
    });
    notifyReportChanges();
  } catch (error) {
    console.warn('TurtleWay could not refresh reports from the server:', error);
  }
}
