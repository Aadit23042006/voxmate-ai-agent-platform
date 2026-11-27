import React, { useEffect, useState } from "react";
import { View, ActivityIndicator, StyleSheet } from "react-native";
import { StatusBar } from "expo-status-bar";
import AuthScreen from "./src/screens/AuthScreen";
import VoiceScreen from "./src/screens/VoiceScreen";
import HistoryScreen from "./src/screens/HistoryScreen";
import SettingsScreen from "./src/screens/SettingsScreen";
import PlatformScreen from "./src/screens/PlatformScreen";
import { loadToken, loadEmail, clearSession } from "./src/services/authStorage";
import { registerDevicePushToken } from "./src/services/pushNotifications";

export default function App() {
  const [checkingSession, setCheckingSession] = useState(true);
  const [session, setSession] = useState<{ token: string; email: string } | null>(null);
  const [screen, setScreen] = useState<"voice" | "history" | "settings" | "platform">("voice");

  useEffect(() => {
    (async () => {
      const [token, email] = await Promise.all([loadToken(), loadEmail()]);
      if (token && email) setSession({ token, email });
      setCheckingSession(false);
    })();
  }, []);

  useEffect(() => {
    if (!session?.token) return;

    let active = true;
    void registerDevicePushToken(session.token, false)
      .then((result) => {
        if (active && result.registered) {
          console.info("[VoxMate] Push device registration successful.");
        }
      })
      .catch((error: unknown) => {
        const message = error instanceof Error ? error.message : "Unknown error";
        if (active) console.warn("[VoxMate] Push registration:", message);
      });

    return () => {
      active = false;
    };
  }, [session?.token]);

  if (checkingSession) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator color="#fff" size="large" />
      </View>
    );
  }

  return (
    <>
      <StatusBar style="light" />
      {session ? (
        screen === "history" ? (
          <HistoryScreen token={session.token} onBack={() => setScreen("voice")} />
        ) : screen === "settings" ? (
          <SettingsScreen token={session.token} onBack={() => setScreen("voice")} onOpenPlatform={() => setScreen("platform")} />
        ) : screen === "platform" ? (
          <PlatformScreen token={session.token} onBack={() => setScreen("settings")} />
        ) : (
          <VoiceScreen
            token={session.token}
            email={session.email}
            onOpenHistory={() => setScreen("history")}
            onOpenSettings={() => setScreen("settings")}
            onLogout={async () => {
              await clearSession();
              setSession(null);
              setScreen("voice");
            }}
          />
        )
      ) : (
        <AuthScreen onAuthenticated={(token, email) => setSession({ token, email })} />
      )}
    </>
  );
}

const styles = StyleSheet.create({
  loading: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "#030609" },
});
