
import React, { useEffect, useRef, useState } from 'react';
import {
  SafeAreaView,
  AppState,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

import FieldReportScreen from './components/FieldReportScreen';
import ReportHistoryScreen from './components/ReportHistoryScreen';
import NetInfo from '@react-native-community/netinfo';
import { StatusBar } from 'expo-status-bar';
import MapView, { Marker, type Region } from 'react-native-maps';
import { syncPendingReports } from './utils/reportSync';
import { fetchTurtleGuardStatus, type TurtleGuardStatus } from './utils/turtleGuard';
import { getDemoEggRisk, type EggRiskAssessment } from './utils/eggRisk';
import { fetchLiveWeather, WeatherData } from './utils/weather';
const GREEN = '#174D3A';
const CREAM = '#F7F6F0';
const MUTED = '#66766D';
const eggRiskColors = { GREEN: '#18794E', YELLOW: '#9A6700', RED: '#C43131' };

const sectors = [
  { name: 'Sasihithlu Delta', subtitle: 'Delta coast', icon: '🌿', latitude: 13.0688, longitude: 74.7770 },
  { name: 'Tannirbhavi', subtitle: 'Coastal beach', icon: '🌊', latitude: 12.90475, longitude: 74.80967 },
  { name: 'Panambur', subtitle: 'Coastal sector', icon: '🏖️', latitude: 13.0015, longitude: 74.85355 },
];

function sectorRegion(latitude: number, longitude: number): Region {
  return { latitude, longitude, latitudeDelta: 0.065, longitudeDelta: 0.065 };
}

const translations = {
  English: {
    greeting: 'Protecting our coast',
    subtitle: 'Turtle conservation field dashboard',
    sector: 'SELECT BEACH SECTOR',
    risk: 'CURRENT RISK STATUS',
    awaiting: 'Assessment needed',
    riskInfo: 'Run a risk assessment to see an estimated risk level and recommended actions.',
    check: 'Check Beach Risk  →',
    map: 'Beach sectors',
    mapInfo: 'Choose a sector to get started',
    report: 'Quick field report',
    reportInfo: 'Notice turtle activity or a possible threat?',
    reportButton: '+  Record an observation',
    home: 'Home',
    risks: 'Risk',
    reports: 'Reports',
    history: 'History',
    selected: 'Selected sector',
    reported: 'Observation form coming next!',
  },
  Kannada: {
    greeting: 'ನಮ್ಮ ಕರಾವಳಿಯನ್ನು ರಕ್ಷಿಸಿ',
    subtitle: 'ಆಮೆ ಸಂರಕ್ಷಣಾ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್',
    sector: 'ಕಡಲತೀರ ಆಯ್ಕೆಮಾಡಿ',
    risk: 'ಪ್ರಸ್ತುತ ಅಪಾಯದ ಸ್ಥಿತಿ',
    awaiting: 'ಮೌಲ್ಯಮಾಪನ ಅಗತ್ಯ',
    riskInfo: 'ಅಪಾಯದ ಮಟ್ಟ ಮತ್ತು ಶಿಫಾರಸು ಮಾಡಿದ ಕ್ರಮಗಳನ್ನು ನೋಡಲು ಮೌಲ್ಯಮಾಪನ ಮಾಡಿ.',
    check: 'ಅಪಾಯ ಪರಿಶೀಲಿಸಿ  →',
    map: 'ಕಡಲತೀರದ ವಲಯಗಳು',
    mapInfo: 'ಪ್ರಾರಂಭಿಸಲು ಒಂದು ವಲಯ ಆಯ್ಕೆಮಾಡಿ',
    report: 'ತ್ವರಿತ ಕ್ಷೇತ್ರ ವರದಿ',
    reportInfo: 'ಆಮೆಯ ಚಟುವಟಿಕೆ ಅಥವಾ ಅಪಾಯ ಗಮನಿಸಿದ್ದೀರಾ?',
    reportButton: '+  ವೀಕ್ಷಣೆ ದಾಖಲಿಸಿ',
    home: 'ಮುಖಪುಟ',
    risks: 'ಅಪಾಯ',
    reports: 'ವರದಿಗಳು',
    history: 'ಇತಿಹಾಸ',
    selected: 'ಆಯ್ಕೆ ಮಾಡಿದ ವಲಯ',
    reported: 'ವರದಿ ನಮೂನೆ ಮುಂದಿನ ಹಂತದಲ್ಲಿ ಬರಲಿದೆ!',
  },
  Hindi: {
    greeting: 'हमारे तट की रक्षा करें',
    subtitle: 'कछुआ संरक्षण डैशबोर्ड',
    sector: 'समुद्र तट चुनें',
    risk: 'वर्तमान जोखिम स्थिति',
    awaiting: 'जाँच आवश्यक',
    riskInfo: 'जोखिम स्तर और सुझाए गए कदम देखने के लिए आकलन करें।',
    check: 'जोखिम जाँचें  →',
    map: 'समुद्र तट क्षेत्र',
    mapInfo: 'शुरू करने के लिए क्षेत्र चुनें',
    report: 'त्वरित फील्ड रिपोर्ट',
    reportInfo: 'कछुए की गतिविधि या कोई खतरा देखा?',
    reportButton: '+  अवलोकन दर्ज करें',
    home: 'होम',
    risks: 'जोखिम',
    reports: 'रिपोर्ट',
    history: 'इतिहास',
    selected: 'चुना गया क्षेत्र',
    reported: 'रिपोर्ट फ़ॉर्म अगले चरण में आएगा!',
  },
};

type Language = keyof typeof translations;

export default function App() {
  const [language, setLanguage] = useState<Language>('English');
  const [selectedSector, setSelectedSector] = useState('Panambur');
  const [activeTab, setActiveTab] = useState('home');
  const [showRiskInfo, setShowRiskInfo] = useState(false);
  const [risk, setRisk] = useState<TurtleGuardStatus | null>(null);
  const [riskLoading, setRiskLoading] = useState(false);
  const [riskError, setRiskError] = useState<string | null>(null);
  const beachMapRef = useRef<MapView>(null);

  useEffect(() => {
    const sector = sectors.find((item) => item.name === selectedSector);
    if (sector) {
      beachMapRef.current?.animateToRegion(
        sectorRegion(sector.latitude, sector.longitude),
        450,
      );
    }
  }, [selectedSector]);

  // Try syncing when the app starts and whenever network connectivity returns.
  useEffect(() => {
    let mounted = true;
    let syncing = false;

    const trySync = async () => {
      if (syncing) return;

      try {
        const network = await NetInfo.fetch();

        if (
          mounted &&
          network.isConnected &&
          network.isInternetReachable !== false
        ) {
          syncing = true;
          try {
            await syncPendingReports();
          } finally {
            syncing = false;
          }
        }
      } catch (error) {
        console.warn('TurtleWay sync check failed:', error);
      }
    };

    void trySync();

    const unsubscribe = NetInfo.addEventListener((network) => {
      if (
        network.isConnected &&
        network.isInternetReachable !== false
      ) {
        void trySync();
      }
    });

    const appStateSubscription = AppState.addEventListener('change', (state) => {
      if (state === 'active') void trySync();
    });

    return () => {
      mounted = false;
      unsubscribe();
      appStateSubscription.remove();
    };
  }, []);

  const t = translations[language];
  const eggRisk = getDemoEggRisk(selectedSector);

  async function checkRisk() {
    setShowRiskInfo(true);
    setRiskLoading(true);
    setRiskError(null);
    try {
      setRisk(await fetchTurtleGuardStatus());
    } catch (error) {
      setRiskError(error instanceof Error ? error.message : 'Could not load the risk assessment.');
    } finally {
      setRiskLoading(false);
    }
  }

  // Open the field report form.
  if (activeTab === 'reports') {
    return (
      <SafeAreaView style={styles.safe}>
        <StatusBar style="light" />
        <FieldReportScreen
          defaultSector={selectedSector}
          onBack={() => setActiveTab('home')}
        />
      </SafeAreaView>
    );
  }

  // Open saved report history.
  if (activeTab === 'history') {
    return (
      <SafeAreaView style={styles.safe}>
        <StatusBar style="light" />
        <ReportHistoryScreen onBack={() => setActiveTab('home')} />
      </SafeAreaView>
    );
  }

  if (activeTab === 'risk') {
    return (
      <SafeAreaView style={styles.safe}>
        <StatusBar style="light" />
        <ScrollView style={styles.screen} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
          <View style={styles.riskScreenHeader}>
            <Text style={styles.brand}>TurtleWay</Text>
            <Text style={styles.riskScreenTitle}>Risk overview</Text>
            <Text style={styles.riskScreenSubtitle}>Egg and fishing activity risks are shown separately.</Text>
          </View>
          <View style={styles.body}>
            <Text style={styles.eyebrow}>SELECTED BEACH · {selectedSector.toUpperCase()}</Text>
            <EggRiskCard eggRisk={eggRisk} detailed />
            <View style={styles.fishingCard}>
              <View style={styles.riskTop}>
                <View style={styles.fishingIcon}><Text style={styles.riskEmoji}>🎣</Text></View>
                <View style={styles.riskHeading}>
                  <Text style={styles.riskEyebrow}>FISHING ACTIVITY RISK</Text>
                  <Text style={styles.riskTitle}>{riskLoading ? 'Checking…' : risk ? risk.risk_status.replaceAll('_', ' ') : 'Not loaded'}</Text>
                </View>
              </View>
              <Text style={styles.riskDescription}>{risk?.message ?? 'Load the saved TurtleGuard assessment for the regional offshore zone.'}</Text>
              {(showRiskInfo || riskError) && <View style={styles.infoBox}><Text style={styles.infoText}>{riskError ?? (risk ? `${risk.message} Activity ratio: ${risk.activity_ratio ?? 'not available'}×. ${risk.note}` : 'The assessment covers the shared Dakshina Kannada offshore zone, not an individual beach sector.')}</Text></View>}
              <TouchableOpacity accessibilityRole="button" disabled={riskLoading} onPress={() => void checkRisk()} style={styles.riskButton}>
                <Text style={styles.riskButtonText}>{riskLoading ? 'Checking…' : risk ? 'Reload TurtleGuard status' : 'Load TurtleGuard status'}</Text>
              </TouchableOpacity>
              <Text style={styles.disclaimer}>GFW-based regional indicator only; it does not prove activity at this beach or identify vessels. Availability and coverage may be limited.</Text>
            </View>
          </View>
        </ScrollView>
        <BottomNavigation activeTab={activeTab} labels={t} onSelect={(tab) => { setActiveTab(tab); if (tab === 'risk' && !risk) void checkRisk(); }} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="light" />

      <ScrollView
        style={styles.screen}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.header}>
          <View style={styles.brandRow}>
            <View style={styles.logo}>
              <Text style={styles.logoText}>🐢</Text>
            </View>
            <View style={styles.brandText}>
              <Text style={styles.brand}>TurtleWay</Text>
              <Text style={styles.tagline}>
                PREDICT THE DANGER. PROTECT THE TURTLE.
              </Text>
            </View>
          </View>

          <Text style={styles.greeting}>{t.greeting}</Text>
          <Text style={styles.headerSubtitle}>{t.subtitle}</Text>

          <Text style={styles.languageLabel}>LANGUAGE / ಭಾಷೆ / भाषा</Text>
          <View style={styles.languageRow}>
            {(['English', 'Kannada', 'Hindi'] as Language[]).map((lang) => (
              <TouchableOpacity
                key={lang}
                accessibilityRole="button"
                accessibilityState={{ selected: language === lang }}
                onPress={() => setLanguage(lang)}
                style={[
                  styles.languageButton,
                  language === lang && styles.languageSelected,
                ]}
              >
                <Text
                  style={[
                    styles.languageText,
                    language === lang && styles.languageTextSelected,
                  ]}
                >
                  {lang === 'Kannada'
                    ? 'ಕನ್ನಡ'
                    : lang === 'Hindi'
                      ? 'हिन्दी'
                      : 'English'}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <View style={styles.body}>
          <View style={styles.sectionHeader}>
            <Text style={styles.eyebrow}>{t.sector}</Text>
            <View style={styles.demoBadge}>
              <Text style={styles.demoText}>DEMO</Text>
            </View>
          </View>

          <View style={styles.sectorPicker}>
            {sectors.map((sector) => {
              const selected = selectedSector === sector.name;

              return (
                <TouchableOpacity
                  key={sector.name}
                  accessibilityRole="button"
                  accessibilityState={{ selected }}
                  onPress={() => setSelectedSector(sector.name)}
                  style={[
                    styles.sectorOption,
                    selected && styles.sectorActive,
                  ]}
                >
                  <Text style={styles.sectorIcon}>{sector.icon}</Text>
                  <Text
                    style={[
                      styles.sectorName,
                      selected && styles.sectorNameActive,
                    ]}
                  >
                    {sector.name}
                  </Text>
                  <Text
                    style={[
                      styles.sectorSubtitle,
                      selected && styles.sectorSubtitleActive,
                    ]}
                  >
                    {sector.subtitle}
                  </Text>
                  {selected && (
                    <Text style={styles.selectedCheck}>✓ Selected</Text>
                  )}
                </TouchableOpacity>
              );
            })}
          </View>

          <EggRiskCard eggRisk={eggRisk} />

          {activeTab === 'legacy' && risk && <View style={styles.riskCard}>
            <View style={styles.riskTop}>
              <View style={styles.riskIcon}>
                <Text style={styles.riskEmoji}>🛡️</Text>
              </View>
              <View style={styles.riskHeading}>
                <Text style={styles.riskEyebrow}>{t.risk}</Text>
                <Text style={styles.riskTitle}>
                  {riskLoading ? 'Checking…' : risk ? risk.risk_status.replaceAll('_', ' ') : t.awaiting}
                </Text>
              </View>
              <View style={styles.pendingBadge}>
                <Text style={styles.pendingText}>
                  {risk?.risk_status === 'high' ? 'ELEVATED' : risk?.risk_status === 'low' ? 'LOW' : risk ? 'LIMITED DATA' : 'PENDING'}
                </Text>
              </View>
            </View>

            <Text style={styles.riskDescription}>
              {risk?.message ?? t.riskInfo}
            </Text>

            {showRiskInfo && (
              <View style={styles.infoBox}>
                <Text style={styles.infoText}>
                  {riskError ?? (risk
                    ? `${risk.message} Activity ratio: ${risk.activity_ratio ?? 'not available'}×. ${risk.note}`
                    : 'The assessment covers the shared Dakshina Kannada offshore zone, not an individual beach sector.')}
                </Text>
              </View>
            )}

            <TouchableOpacity
              accessibilityRole="button"
              disabled={riskLoading}
              onPress={() => void checkRisk()}
              style={styles.riskButton}
            >
              <Text style={styles.riskButtonText}>{riskLoading ? 'Checking…' : risk ? 'Reload TurtleGuard status' : t.check}</Text>
            </TouchableOpacity>

            <Text style={styles.disclaimer}>
              {risk ? `${risk.source} · ${risk.days_per_period}-day comparison · Prototype calibration` : 'Regional indicator · Select to load the latest saved assessment'}
            </Text>
          </View>}

          <View style={styles.sectionTitleRow}>
            <View>
              <Text style={styles.sectionTitle}>{t.map}</Text>
              <Text style={styles.sectionSubtitle}>{t.mapInfo}</Text>
            </View>
            <Text style={styles.mapEmoji}>🗺️</Text>
          </View>

          <View style={styles.interactiveMapCard}>
            <MapView
              ref={beachMapRef}
              style={styles.interactiveMap}
              initialRegion={{
                latitude: 12.987,
                longitude: 74.815,
                latitudeDelta: 0.22,
                longitudeDelta: 0.13,
              }}
              accessibilityLabel="Map of TurtleWay beach sectors"
            >
              {sectors.map((sector) => (
                <Marker
                  key={sector.name}
                  coordinate={{ latitude: sector.latitude, longitude: sector.longitude }}
                  title={sector.name}
                  description={sector.subtitle}
                  pinColor={selectedSector === sector.name ? GREEN : '#377D6A'}
                  onPress={() => setSelectedSector(sector.name)}
                />
              ))}
            </MapView>
            <View style={styles.mapSelectionBanner}>
              <Text style={styles.mapSelectionLabel}>SELECTED BEACH</Text>
              <Text style={styles.mapSelectionName}>{selectedSector}</Text>
              <Text style={styles.mapSelectionHint}>Tap a marker or a beach sector above to change it.</Text>
            </View>
          </View>

          <View style={styles.reportCard}>
            <View style={styles.reportIcon}>
              <Text style={styles.reportEmoji}>📋</Text>
            </View>
            <Text style={styles.reportTitle}>{t.report}</Text>
            <Text style={styles.reportDescription}>{t.reportInfo}</Text>
            <TouchableOpacity
              accessibilityRole="button"
              onPress={() => setActiveTab('reports')}
              style={styles.reportButton}
            >
              <Text style={styles.reportButtonText}>{t.reportButton}</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.footer}>
            <Text style={styles.footerTurtle}>🐢</Text>
            <Text style={styles.footerText}>
              Every observation helps protect our coast.
            </Text>
          </View>
        </View>
      </ScrollView>

      <View style={styles.bottomBar}>
        {[
          { id: 'home', icon: '⌂', label: t.home },
          { id: 'risk', icon: '◉', label: t.risks },
          { id: 'reports', icon: '▤', label: t.reports },
          { id: 'history', icon: '◷', label: t.history },
        ].map((tab) => (
          <TouchableOpacity
            key={tab.id}
            accessibilityRole="button"
            accessibilityState={{ selected: activeTab === tab.id }}
            onPress={() => {
              setActiveTab(tab.id);
              if (tab.id === 'risk') void checkRisk();
            }}
            style={styles.navItem}
          >
            <Text
              style={[
                styles.navIcon,
                activeTab === tab.id && styles.navIconActive,
              ]}
            >
              {tab.icon}
            </Text>
            <Text
              style={[
                styles.navLabel,
                activeTab === tab.id && styles.navLabelActive,
              ]}
            >
              {tab.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    </SafeAreaView>
  );
}

function EggRiskCard({ eggRisk, detailed = false }: { eggRisk: EggRiskAssessment; detailed?: boolean }) {
  const color = eggRiskColors[eggRisk.tier];
  return (
    <View style={styles.riskCard}>
      <View style={styles.riskTop}>
        <View style={[styles.riskIcon, { backgroundColor: `${color}18` }]}><Text style={styles.riskEmoji}>🥚</Text></View>
        <View style={styles.riskHeading}>
          <Text style={styles.riskEyebrow}>{detailed ? 'TURTLE EGG RISK · DEMO' : 'CURRENT RISK STATUS · TURTLE EGG RISK'}</Text>
          <Text style={[styles.riskTitle, { color }]}>{eggRisk.tier} EGG RISK</Text>
        </View>
        <View style={[styles.tierBadge, { backgroundColor: `${color}20` }]}><Text style={[styles.tierBadgeText, { color }]}>{eggRisk.tier}</Text></View>
      </View>
      <Text style={styles.riskDescription}>{eggRisk.action}</Text>
      {detailed && <View style={styles.eggMetrics}>
        <Text style={styles.eggMetric}>Nest: {eggRisk.nestId}</Text>
        <Text style={styles.eggMetric}>Score: {eggRisk.score.toFixed(1)} / 100</Text>
        <Text style={styles.eggMetric}>Sand: {eggRisk.sandTemperatureC.toFixed(1)} °C</Text>
        <Text style={styles.eggMetric}>Light: {eggRisk.beachLightLux.toFixed(1)} lux</Text>
        <Text style={styles.eggMetric}>Hatch estimate: {eggRisk.daysUntilEmergence} days</Text>
      </View>}
      {!detailed && <Text style={styles.disclaimer}>Demo nest {eggRisk.nestId} · {eggRisk.daysUntilEmergence} days to hatch estimate · {eggRisk.beachLightLux.toFixed(1)} lux</Text>}
    </View>
  );
}

function BottomNavigation({ activeTab, labels, onSelect }: { activeTab: string; labels: typeof translations.English; onSelect: (tab: string) => void }) {
  const tabs = [
    { id: 'home', icon: '⌂', label: labels.home }, { id: 'risk', icon: '◉', label: labels.risks },
    { id: 'reports', icon: '▤', label: labels.reports }, { id: 'history', icon: '◷', label: labels.history },
  ];
  return <View style={styles.bottomBar}>{tabs.map((tab) => <TouchableOpacity key={tab.id} accessibilityRole="button" accessibilityState={{ selected: activeTab === tab.id }} onPress={() => onSelect(tab.id)} style={styles.navItem}>
    <Text style={[styles.navIcon, activeTab === tab.id && styles.navIconActive]}>{tab.icon}</Text>
    <Text style={[styles.navLabel, activeTab === tab.id && styles.navLabelActive]}>{tab.label}</Text>
  </TouchableOpacity>)}</View>;
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: CREAM },
  screen: { flex: 1, backgroundColor: CREAM },
  content: { paddingBottom: 20 },
  header: {
    backgroundColor: GREEN,
    paddingHorizontal: 22,
    paddingTop: 18,
    paddingBottom: 24,
    borderBottomLeftRadius: 28,
    borderBottomRightRadius: 28,
  },
  brandRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  logo: {
    width: 48, height: 48, borderRadius: 16,
    backgroundColor: '#FFFFFF', alignItems: 'center', justifyContent: 'center',
  },
  logoText: { fontSize: 27 },
  brandText: { flex: 1 },
  brand: { fontSize: 25, fontWeight: '800', color: '#FFFFFF', letterSpacing: 0.3 },
  tagline: { fontSize: 9, color: '#D7E8DC', letterSpacing: 0.6, marginTop: 3 },
  greeting: { color: '#FFFFFF', fontSize: 25, fontWeight: '800', marginTop: 25 },
  headerSubtitle: { color: '#D7E8DC', fontSize: 14, marginTop: 6 },
  languageLabel: { color: '#C6DBCC', fontSize: 10, fontWeight: '700', marginTop: 23, marginBottom: 9, letterSpacing: 0.8 },
  languageRow: { flexDirection: 'row', gap: 8 },
  languageButton: {
    flex: 1, paddingVertical: 11, borderRadius: 12,
    borderWidth: 1, borderColor: '#668775', alignItems: 'center',
  },
  languageSelected: { backgroundColor: '#FFFFFF', borderColor: '#FFFFFF' },
  languageText: { color: '#FFFFFF', fontWeight: '600', fontSize: 13 },
  languageTextSelected: { color: GREEN, fontWeight: '800' },
  body: { paddingHorizontal: 18, paddingTop: 23 },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  eyebrow: { color: MUTED, fontSize: 11, fontWeight: '800', letterSpacing: 1 },
  demoBadge: { backgroundColor: '#E1EDE5', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 8 },
  demoText: { color: GREEN, fontSize: 10, fontWeight: '800' },
  sectorPicker: { gap: 9 },
  sectorOption: {
    backgroundColor: '#FFFFFF', borderRadius: 15, borderWidth: 1.5,
    borderColor: '#E6E9E3', padding: 13,
  },
  sectorActive: { borderColor: GREEN, backgroundColor: '#EDF5EF' },
  sectorIcon: { fontSize: 22, marginBottom: 6 },
  sectorName: { fontSize: 15, fontWeight: '800', color: '#24392E' },
  sectorNameActive: { color: GREEN },
  sectorSubtitle: { fontSize: 12, color: MUTED, marginTop: 3 },
  sectorSubtitleActive: { color: GREEN },
  selectedCheck: { color: GREEN, fontSize: 11, fontWeight: '800', marginTop: 7 },
  riskCard: { backgroundColor: '#FFFFFF', borderRadius: 20, padding: 17, marginTop: 22, borderWidth: 1, borderColor: '#E8E8DF' },
  riskTop: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  riskIcon: { width: 46, height: 46, borderRadius: 14, backgroundColor: '#F4F0DF', alignItems: 'center', justifyContent: 'center' },
  riskEmoji: { fontSize: 23 },
  riskHeading: { flex: 1 },
  riskEyebrow: { fontSize: 10, fontWeight: '800', color: MUTED, letterSpacing: 0.7 },
  riskTitle: { fontSize: 18, fontWeight: '800', color: '#28382D', marginTop: 4 },
  tierBadge: { borderRadius: 8, paddingHorizontal: 8, paddingVertical: 5 },
  tierBadgeText: { fontSize: 10, fontWeight: '800' },
  demoNotice: { backgroundColor: '#FFF8E5', borderRadius: 9, padding: 10, marginTop: 12 },
  demoNoticeText: { color: '#745E12', fontSize: 11, fontWeight: '700', lineHeight: 16 },
  eggMetrics: { backgroundColor: '#F4F7F2', borderRadius: 10, padding: 12, marginTop: 12, gap: 5 },
  eggMetric: { color: '#385346', fontSize: 12 },
  riskScreenHeader: { backgroundColor: GREEN, paddingHorizontal: 22, paddingTop: 20, paddingBottom: 25, borderBottomLeftRadius: 28, borderBottomRightRadius: 28 },
  riskScreenTitle: { color: '#FFFFFF', fontSize: 27, fontWeight: '800', marginTop: 18 },
  riskScreenSubtitle: { color: '#D8E8DC', fontSize: 13, marginTop: 6 },
  fishingCard: { backgroundColor: '#FFFFFF', borderRadius: 20, padding: 17, marginTop: 18, borderWidth: 1, borderColor: '#E8E8DF' },
  fishingIcon: { width: 46, height: 46, borderRadius: 14, backgroundColor: '#E9F0F8', alignItems: 'center', justifyContent: 'center' },
  pendingBadge: { backgroundColor: '#FFF1D8', borderRadius: 8, paddingHorizontal: 8, paddingVertical: 5 },
  pendingText: { color: '#875B12', fontSize: 9, fontWeight: '800' },
  riskDescription: { color: MUTED, fontSize: 13, lineHeight: 20, marginTop: 14 },
  infoBox: { backgroundColor: '#EDF5EF', borderRadius: 10, padding: 12, marginTop: 12 },
  infoText: { color: GREEN, fontSize: 12, lineHeight: 18 },
  riskButton: { backgroundColor: GREEN, borderRadius: 13, padding: 15, alignItems: 'center', marginTop: 15 },
  riskButtonText: { color: '#FFFFFF', fontSize: 15, fontWeight: '800' },
  disclaimer: { color: '#8A948D', fontSize: 10, textAlign: 'center', marginTop: 11 },
  sectionTitleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 27, marginBottom: 13 },
  sectionTitle: { fontSize: 20, fontWeight: '800', color: '#20372A' },
  sectionSubtitle: { fontSize: 12, color: MUTED, marginTop: 4 },
  mapEmoji: { fontSize: 25 },
  interactiveMapCard: { borderRadius: 18, overflow: 'hidden', borderWidth: 1, borderColor: '#DCE6D8', backgroundColor: '#FFFFFF' },
  interactiveMap: { height: 260, width: '100%' },
  mapSelectionBanner: { backgroundColor: '#F0EBD9', paddingHorizontal: 14, paddingVertical: 12 },
  mapSelectionLabel: { color: '#73856A', fontSize: 9, fontWeight: '800', letterSpacing: 0.8 },
  mapSelectionName: { color: GREEN, fontSize: 16, fontWeight: '800', marginTop: 2 },
  mapSelectionHint: { color: MUTED, fontSize: 11, marginTop: 3 },
  mapCard: { flexDirection: 'row', borderRadius: 18, overflow: 'hidden', minHeight: 245, borderWidth: 1, borderColor: '#DCE6D8' },
  ocean: { width: '30%', backgroundColor: '#D8EAE7', justifyContent: 'center', alignItems: 'center', padding: 7 },
  oceanText: { color: '#367A78', fontSize: 10, fontWeight: '800', textAlign: 'center', letterSpacing: 1, transform: [{ rotate: '-90deg' }] },
  wave: { fontSize: 13, marginTop: 20 },
  coast: { flex: 1, backgroundColor: '#F0EBD9', padding: 12, justifyContent: 'center' },
  coastLine: { position: 'absolute', left: -5, top: 0, bottom: 0, width: 14, backgroundColor: '#C3D6AC', borderTopRightRadius: 30, borderBottomRightRadius: 30 },
  coastTitle: { fontSize: 9, fontWeight: '800', color: '#73856A', letterSpacing: 0.8, marginBottom: 10 },
  mapLocation: { flexDirection: 'row', alignItems: 'center', gap: 9, paddingVertical: 8 },
  mapDot: { width: 27, height: 27, borderRadius: 14, backgroundColor: '#FFFFFF', borderWidth: 1, borderColor: '#9BAE8E', alignItems: 'center', justifyContent: 'center' },
  mapDotActive: { backgroundColor: GREEN, borderColor: GREEN },
  mapDotNumber: { fontSize: 11, color: GREEN, fontWeight: '800' },
  mapLabel: { flex: 1 },
  mapPlace: { fontSize: 12, color: '#304434', fontWeight: '800' },
  mapHint: { fontSize: 10, color: '#71816E', marginTop: 2 },
  mapNote: { fontSize: 8, color: '#73816F', marginTop: 9 },
  reportCard: { backgroundColor: GREEN, borderRadius: 20, padding: 19, marginTop: 23 },
  reportIcon: { width: 43, height: 43, backgroundColor: '#FFFFFF22', borderRadius: 13, alignItems: 'center', justifyContent: 'center', marginBottom: 12 },
  reportEmoji: { fontSize: 22 },
  reportTitle: { color: '#FFFFFF', fontSize: 21, fontWeight: '800' },
  reportDescription: { color: '#D8E8DC', fontSize: 13, lineHeight: 19, marginTop: 6 },
  reportButton: { backgroundColor: '#FFFFFF', borderRadius: 12, padding: 14, alignItems: 'center', marginTop: 17 },
  reportButtonText: { color: GREEN, fontWeight: '800', fontSize: 14 },
  footer: { alignItems: 'center', paddingVertical: 25, gap: 7 },
  footerTurtle: { fontSize: 23 },
  footerText: { color: MUTED, fontSize: 11, textAlign: 'center' },
  bottomBar: { flexDirection: 'row', backgroundColor: '#FFFFFF', paddingTop: 10, paddingBottom: 8, borderTopWidth: 1, borderTopColor: '#E4E8E1' },
  navItem: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 4, paddingVertical: 3 },
  navIcon: { fontSize: 22, color: '#89968D' },
  navIconActive: { color: GREEN },
  navLabel: { fontSize: 10, color: '#89968D', fontWeight: '600' },
  navLabelActive: { color: GREEN, fontWeight: '800' },
});
