import { AppState, Platform } from 'react-native';
import 'react-native-url-polyfill/auto';
import * as SecureStore from 'expo-secure-store';
import { createClient, SupportedStorage } from '@supabase/supabase-js';

const url = process.env.EXPO_PUBLIC_SUPABASE_URL;
const publishableKey = process.env.EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

export const authConfigured = Boolean(url && publishableKey);

// SecureStore values can be size-limited by the platform. Chunk the serialized
// Supabase session so large JWTs remain in encrypted device storage.
const CHUNK_SIZE = 1700;
const secureStorage: SupportedStorage = {
  async getItem(key) {
    if (Platform.OS === 'web') return globalThis.localStorage?.getItem(key) ?? null;
    const countText = await SecureStore.getItemAsync(`${key}.count`);
    if (!countText) return null;
    const count = Number(countText);
    if (!Number.isInteger(count) || count < 1 || count > 20) return null;
    const chunks = await Promise.all(
      Array.from({ length: count }, (_, index) => SecureStore.getItemAsync(`${key}.${index}`)),
    );
    return chunks.every((chunk) => chunk !== null) ? chunks.join('') : null;
  },
  async setItem(key, value) {
    if (Platform.OS === 'web') {
      globalThis.localStorage?.setItem(key, value);
      return;
    }
    const count = Math.ceil(value.length / CHUNK_SIZE);
    if (count > 20) throw new Error('Authentication session is too large to store securely.');
    const previous = Number(await SecureStore.getItemAsync(`${key}.count`) ?? 0);
    for (let index = 0; index < count; index += 1) {
      await SecureStore.setItemAsync(`${key}.${index}`, value.slice(index * CHUNK_SIZE, (index + 1) * CHUNK_SIZE));
    }
    await SecureStore.setItemAsync(`${key}.count`, String(count));
    for (let index = count; index < previous; index += 1) {
      await SecureStore.deleteItemAsync(`${key}.${index}`);
    }
  },
  async removeItem(key) {
    if (Platform.OS === 'web') {
      globalThis.localStorage?.removeItem(key);
      return;
    }
    const count = Number(await SecureStore.getItemAsync(`${key}.count`) ?? 0);
    await Promise.all(
      Array.from({ length: Math.min(count, 20) }, (_, index) => SecureStore.deleteItemAsync(`${key}.${index}`)),
    );
    await SecureStore.deleteItemAsync(`${key}.count`);
  },
};

export const supabase = authConfigured
  ? createClient(url!, publishableKey!, {
      auth: {
        storage: secureStorage,
        autoRefreshToken: true,
        persistSession: true,
        detectSessionInUrl: false,
      },
    })
  : null;

if (supabase && Platform.OS !== 'web') {
  AppState.addEventListener('change', (state) => {
    if (state === 'active') supabase.auth.startAutoRefresh();
    else supabase.auth.stopAutoRefresh();
  });
}
