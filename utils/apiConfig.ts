// Override with EXPO_PUBLIC_API_URL when starting Expo. On a physical phone,
// use the computer's current LAN IPv4 address; 127.0.0.1 points to the phone.
export const API_BASE_URL = (
  process.env.EXPO_PUBLIC_API_URL ?? 'http://127.0.0.1:8000'
).replace(/\/$/, '');
