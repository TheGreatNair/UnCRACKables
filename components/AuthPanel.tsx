import React, { useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';
import type { Session } from '@supabase/supabase-js';
import { authConfigured, supabase } from '../utils/supabase';

type Props = { session: Session | null; loading: boolean };

export default function AuthPanel({ session, loading }: Props) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSignUp, setIsSignUp] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');

  async function submit() {
    if (!supabase || busy) return;
    setBusy(true);
    setMessage('');
    try {
      const result = isSignUp
        ? await supabase.auth.signUp({ email: email.trim(), password })
        : await supabase.auth.signInWithPassword({ email: email.trim(), password });
      if (result.error) throw result.error;
      if (isSignUp && !result.data.session) setMessage('Account created. Check your email to confirm, then sign in.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Sign-in failed. Please try again.');
    } finally {
      setBusy(false);
    }
  }

  async function signOut() {
    if (!supabase) return;
    setBusy(true);
    setMessage('');
    const { error } = await supabase.auth.signOut();
    setMessage(error?.message ?? 'Signed out. Any unsynced reports stay on this device.');
    setBusy(false);
  }

  return (
    <View style={styles.card}>
      <Text style={styles.title}>Field account</Text>
      {!authConfigured ? (
        <Text style={styles.body}>Cloud sign-in is not configured. Reports can still be saved offline. Add the Expo Supabase URL and publishable key to the local .env to connect.</Text>
      ) : loading ? (
        <View style={styles.inline}><ActivityIndicator color="#176B45" /><Text style={styles.body}>Restoring secure session…</Text></View>
      ) : session ? (
        <>
          <Text style={styles.body}>Signed in as {session.user.email ?? 'field reporter'}. Pending reports will sync to this account.</Text>
          <TouchableOpacity accessibilityRole="button" disabled={busy} onPress={signOut} style={styles.secondary}><Text style={styles.secondaryText}>{busy ? 'Signing out…' : 'Sign out'}</Text></TouchableOpacity>
        </>
      ) : (
        <>
          <Text style={styles.body}>Sign in to send queued field reports to the protected API.</Text>
          <TextInput autoCapitalize="none" autoComplete="email" keyboardType="email-address" value={email} onChangeText={setEmail} placeholder="Email" placeholderTextColor="#78847B" style={styles.input} />
          <TextInput autoCapitalize="none" autoComplete={isSignUp ? 'new-password' : 'password'} secureTextEntry value={password} onChangeText={setPassword} placeholder="Password" placeholderTextColor="#78847B" style={styles.input} />
          {message ? <Text accessibilityRole="alert" style={styles.message}>{message}</Text> : null}
          <TouchableOpacity accessibilityRole="button" disabled={busy || !email.trim() || password.length < 8} onPress={submit} style={styles.primary}>
            <Text style={styles.primaryText}>{busy ? 'Please wait…' : isSignUp ? 'Create field account' : 'Sign in and sync'}</Text>
          </TouchableOpacity>
          <TouchableOpacity accessibilityRole="button" onPress={() => { setIsSignUp(!isSignUp); setMessage(''); }} style={styles.switch}>
            <Text style={styles.switchText}>{isSignUp ? 'Already registered? Sign in' : 'Need an account? Create one'}</Text>
          </TouchableOpacity>
        </>
      )}
      {message && session ? <Text style={styles.message}>{message}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: '#FFFFFF', borderColor: '#D8E1D9', borderWidth: 1, borderRadius: 16, padding: 16, marginBottom: 20 },
  title: { color: '#163D2B', fontSize: 17, fontWeight: '800', marginBottom: 6 },
  body: { color: '#58665D', fontSize: 13, lineHeight: 19, flex: 1 },
  inline: { flexDirection: 'row', gap: 10, alignItems: 'center' },
  input: { borderWidth: 1, borderColor: '#D8E1D9', borderRadius: 10, padding: 12, color: '#183D2B', marginTop: 10, backgroundColor: '#FBFCFA' },
  primary: { backgroundColor: '#176B45', borderRadius: 11, padding: 13, alignItems: 'center', marginTop: 12 },
  primaryText: { color: '#FFFFFF', fontWeight: '800' },
  secondary: { alignSelf: 'flex-start', backgroundColor: '#E0F0E5', borderRadius: 10, padding: 10, marginTop: 12 },
  secondaryText: { color: '#176B45', fontWeight: '800' },
  switch: { alignSelf: 'center', paddingVertical: 12 },
  switchText: { color: '#176B45', fontWeight: '700' },
  message: { color: '#8D3E2F', fontSize: 12, lineHeight: 17, marginTop: 8 },
});
