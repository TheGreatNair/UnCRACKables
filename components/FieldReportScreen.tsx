
import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  Alert,
  ActivityIndicator,
} from "react-native";
import * as Location from 'expo-location';
import { syncPendingReports } from '../utils/reportSync';
import { FieldReport, ReportLocationSource, updateReports } from '../utils/reportStorage';
import { buildReportLocation, captureCurrentLocation, LocationCaptureError } from '../utils/locationCapture';

const TYPES = [
  "Turtle sighting",
  "Nest found",
  "Hatchlings spotted",
  "Beach disturbance",
  "Other",
];

const SECTORS = [
  "Sasihithlu Delta",
  "Tannirbhavi",
  "Panambur",
];

type CapturedLocation = { latitude: number; longitude: number };

type Props = {
  onBack: () => void;
  defaultSector?: string;
};

export default function FieldReportScreen({
  onBack,
  defaultSector = SECTORS[0],
}: Props) {
  const [sector, setSector] = useState(defaultSector);
  const [type, setType] = useState(TYPES[0]);
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [locationSource, setLocationSource] = useState<ReportLocationSource>('preset');
  const [gpsLocation, setGpsLocation] = useState<CapturedLocation | null>(null);
  const [locationLoading, setLocationLoading] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);

  async function useCurrentLocation() {
    if (locationLoading) return;
    setLocationSource('gps');
    setGpsLocation(null);
    setLocationError(null);
    setLocationLoading(true);

    try {
      const coordinates = await captureCurrentLocation({
        requestForegroundPermission: Location.requestForegroundPermissionsAsync,
        areLocationServicesEnabled: Location.hasServicesEnabledAsync,
        getCoordinates: async () => {
          const current = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
          return { latitude: current.coords.latitude, longitude: current.coords.longitude };
        },
      });
      setGpsLocation(coordinates);
    } catch (error) {
      if (error instanceof LocationCaptureError && error.code === 'permission-denied') {
        setLocationError(
          'Location permission was denied. Allow access or choose a coastal sector.',
        );
      } else if (error instanceof LocationCaptureError && error.code === 'services-disabled') {
        setLocationError('Location services are turned off. Turn them on in device Settings, then retry.');
      } else if (error instanceof LocationCaptureError && error.code === 'timeout') {
        setLocationError('Location is taking too long. Move to an open area and retry, or choose a coastal sector.');
      } else if (error instanceof LocationCaptureError && error.code === 'invalid-coordinates') {
        setLocationError('The device returned invalid coordinates. Please retry or choose a coastal sector.');
      } else if (error && typeof error === 'object' && 'canAskAgain' in error && error.canAskAgain === false) {
        setLocationError('Location permission is disabled for TurtleWay. Change it in device Settings or choose a coastal sector.');
      } else {
        setLocationError('Could not get your location. Check device settings and retry, or choose a coastal sector.');
      }
    } finally {
      setLocationLoading(false);
    }
  }

  function choosePresetSector(item: string) {
    setSector(item);
    setLocationSource('preset');
    setGpsLocation(null);
    setLocationError(null);
  }

  async function saveReport() {
    if (saving) return;

    setSaving(true);

    try {
      const createdAt = new Date().toISOString();
      const gpsSelected = locationSource === 'gps';
      if (gpsSelected && !gpsLocation) {
        Alert.alert('Location needed', 'Get your current location or choose a coastal sector before saving.');
        return;
      }
      const reportLocation = buildReportLocation(
        locationSource === 'gps' ? 'gps' : 'preset',
        sector,
        gpsLocation,
      );
      const report: FieldReport = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        ...reportLocation,
        type,
        notes: notes.trim(),
        createdAt,
        timestamp: createdAt,
        syncStatus: "pending",
        reviewStatus: "not_reviewed",
      };

      await updateReports((existing) => [report, ...existing]);
      // Local persistence completes first. Network work runs in the background.
      void syncPendingReports();

      Alert.alert(
        "Report saved",
        "Saved on this device. It has not yet been sent to the conservation authority.",
        [{ text: "OK", onPress: onBack }]
      );
    } catch {
      Alert.alert(
        "Could not save",
        "Please try again. Make sure your device has enough storage."
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
    >
      <TouchableOpacity onPress={onBack} style={styles.back}>
        <Text style={styles.backText}>← Back to dashboard</Text>
      </TouchableOpacity>

      <Text style={styles.eyebrow}>TURTLEWAY FIELD TOOLS</Text>
      <Text style={styles.title}>New field report</Text>
      <Text style={styles.subtitle}>
        Record what you observe. Reports are saved on this device first.
      </Text>

      <Text style={styles.label}>Report location</Text>
      <View style={styles.locationModes}>
        <TouchableOpacity
          accessibilityRole="button"
          accessibilityState={{ selected: locationSource === 'gps' }}
          disabled={locationLoading}
          onPress={useCurrentLocation}
          style={[styles.locationMode, locationSource === 'gps' && styles.locationModeSelected]}
        >
          <Text style={[styles.locationModeText, locationSource === 'gps' && styles.locationModeTextSelected]}>
            Use Current Location
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          accessibilityRole="button"
          accessibilityState={{ selected: locationSource === 'preset' }}
          disabled={locationLoading}
          onPress={() => {
            setLocationSource('preset');
            setGpsLocation(null);
            setLocationError(null);
          }}
          style={[styles.locationMode, locationSource === 'preset' && styles.locationModeSelected]}
        >
          <Text style={[styles.locationModeText, locationSource === 'preset' && styles.locationModeTextSelected]}>
            Choose a Coastal Sector
          </Text>
        </TouchableOpacity>
      </View>

      {locationSource === 'preset' ? (
        <View style={styles.options}>
          {SECTORS.map((item) => (
            <TouchableOpacity
              key={item}
              accessibilityRole="button"
              accessibilityState={{ selected: sector === item }}
              onPress={() => choosePresetSector(item)}
              style={[styles.option, sector === item && styles.selected]}
            >
              <Text style={[styles.optionText, sector === item && styles.selectedText]}>{item}</Text>
            </TouchableOpacity>
          ))}
          <Text style={styles.locationHint}>Location source: predefined coastal sector</Text>
        </View>
      ) : (
        <View style={styles.gpsCard}>
          {locationLoading ? (
            <View style={styles.gpsMessageRow}>
              <ActivityIndicator color="#176B45" />
              <Text style={styles.gpsMessage}>Getting your current location…</Text>
            </View>
          ) : gpsLocation ? (
            <>
              <Text style={styles.gpsSuccess}>GPS location captured</Text>
              <Text style={styles.coordinates}>Latitude: {gpsLocation.latitude.toFixed(6)}</Text>
              <Text style={styles.coordinates}>Longitude: {gpsLocation.longitude.toFixed(6)}</Text>
              <TouchableOpacity accessibilityRole="button" onPress={useCurrentLocation} style={styles.retryButton}>
                <Text style={styles.retryButtonText}>Refresh GPS location</Text>
              </TouchableOpacity>
            </>
          ) : (
            <>
              <Text style={styles.gpsMessage}>Your location is only used for this report.</Text>
              {locationError ? <Text accessibilityRole="alert" style={styles.locationError}>{locationError}</Text> : null}
              <TouchableOpacity accessibilityRole="button" onPress={useCurrentLocation} style={styles.retryButton}>
                <Text style={styles.retryButtonText}>{locationError ? 'Retry GPS location' : 'Get GPS location'}</Text>
              </TouchableOpacity>
            </>
          )}
        </View>
      )}

      <Text style={styles.label}>What did you observe?</Text>
      <View style={styles.options}>
        {TYPES.map((item) => (
          <TouchableOpacity
            key={item}
            onPress={() => setType(item)}
            style={[
              styles.option,
              type === item && styles.selected,
            ]}
          >
            <Text
              style={[
                styles.optionText,
                type === item && styles.selectedText,
              ]}
            >
              {item}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={styles.label}>Additional notes (optional)</Text>
      <TextInput
        value={notes}
         onChangeText={setNotes}
        placeholder="Describe the observation..."
        placeholderTextColor="#758078"
        multiline
        textAlignVertical="top"
        style={styles.input}
      />

      <View style={styles.notice}>
        <Text style={styles.noticeText}>
          ✓ Works without internet{"\n"}
          ✓ Saved on this device{"\n"}
          ⏳ Stored safely on this device
        </Text>
      </View>

      <TouchableOpacity
        onPress={saveReport}
        disabled={saving || locationLoading || (locationSource === 'gps' && !gpsLocation)}
        style={[styles.saveButton, saving && styles.disabled]}
      >
        <Text style={styles.saveText}>
          {saving ? "Saving..." : "Save field report"}
        </Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F5F7F2" },
  content: { padding: 20, paddingBottom: 40 },
  back: { paddingVertical: 12, marginBottom: 12 },
  backText: { color: "#176B45", fontSize: 16, fontWeight: "600" },
  eyebrow: {
    color: "#387653",
    fontSize: 12,
    fontWeight: "800",
    letterSpacing: 1.5,
  },
  title: {
    color: "#163D2B",
    fontSize: 29,
    fontWeight: "800",
    marginTop: 8,
  },
  subtitle: {
    color: "#58665D",
    fontSize: 15,
    lineHeight: 22,
    marginTop: 8,
    marginBottom: 26,
  },
  label: {
    color: "#163D2B",
    fontSize: 16,
    fontWeight: "700",
    marginBottom: 10,
    marginTop: 12,
  },
  options: { gap: 9, marginBottom: 14 },
  locationModes: { gap: 9, marginBottom: 12 },
  locationMode: {
    backgroundColor: '#FFFFFF', borderColor: '#D8E1D9', borderWidth: 1,
    borderRadius: 12, padding: 14,
  },
  locationModeSelected: { backgroundColor: '#E0F0E5', borderColor: '#28754C', borderWidth: 2 },
  locationModeText: { color: '#34443A', fontSize: 14, fontWeight: '700' },
  locationModeTextSelected: { color: '#165C38' },
  locationHint: { color: '#66766D', fontSize: 12, marginTop: 2 },
  gpsCard: { backgroundColor: '#FFFFFF', borderColor: '#D8E1D9', borderWidth: 1, borderRadius: 12, padding: 14, marginBottom: 14 },
  gpsMessageRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  gpsMessage: { color: '#34443A', fontSize: 13, lineHeight: 19 },
  gpsSuccess: { color: '#176B45', fontSize: 14, fontWeight: '800', marginBottom: 8 },
  coordinates: { color: '#34443A', fontSize: 13, lineHeight: 20, fontVariant: ['tabular-nums'] },
  locationError: { color: '#8D3E2F', fontSize: 13, lineHeight: 19, marginTop: 8 },
  retryButton: { alignSelf: 'flex-start', backgroundColor: '#E0F0E5', borderRadius: 10, paddingHorizontal: 12, paddingVertical: 9, marginTop: 10 },
  retryButtonText: { color: '#176B45', fontSize: 13, fontWeight: '800' },
  option: {
    backgroundColor: "#FFFFFF",
    borderColor: "#D8E1D9",
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
  },
  selected: {
    backgroundColor: "#E0F0E5",
    borderColor: "#28754C",
    borderWidth: 2,
  },
  optionText: { color: "#34443A", fontSize: 15 },
  selectedText: { color: "#165C38", fontWeight: "700" },
  input: {
    minHeight: 110,
    borderWidth: 1,
    borderColor: "#D8E1D9",
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    padding: 14,
    fontSize: 15,
    color: "#183D2B",
    marginBottom: 18,
  },
  notice: {
    backgroundColor: "#E8F2E9",
    padding: 14,
    borderRadius: 12,
    marginBottom: 20,
  },
  noticeText: {
    color: "#28563A",
    fontSize: 14,
    lineHeight: 24,
  },
  saveButton: {
    backgroundColor: "#176B45",
    borderRadius: 14,
    padding: 17,
    alignItems: "center",
  },
  disabled: { opacity: 0.6 },
  saveText: { color: "#FFFFFF", fontSize: 16, fontWeight: "800" },
});
