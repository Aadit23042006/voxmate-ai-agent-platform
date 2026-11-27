import React, { useCallback, useEffect, useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  Alert,
  Linking,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { BlurView } from "expo-blur";
import AuroraBackground from "../components/AuroraBackground";
import { colors } from "../theme";
import {
  getPreferences,
  updatePreferences,
  getUsageStats,
  deleteAllData,
  Preferences,
  UsageStats,
  API_URL, getGoogleConnectUrl, getGoogleStatus,
  getGitHubStatus, connectGitHub, disconnectGitHub,
} from "../services/api";
import { registerDevicePushToken } from "../services/pushNotifications";

type Props = {
  token: string;
  onBack: () => void;
  onOpenPlatform?: () => void;
};

// Voice/assistant-name/tone picker, usage stats, conversation export, and
// GDPR-style "delete all my data" — same visual language as HistoryScreen
// (blurred cards, same color tokens), no new design system introduced.
export default function SettingsScreen({ token, onBack, onOpenPlatform }: Props) {
  const [prefs, setPrefs] = useState<Preferences | null>(null);
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [nameDraft, setNameDraft] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [googleConnected, setGoogleConnected] = useState(false);
  const [notificationBusy, setNotificationBusy] = useState(false);
  const [githubConnected, setGithubConnected] = useState(false);
  const [githubLogin, setGithubLogin] = useState<string | null>(null);
  const [githubTokenDraft, setGithubTokenDraft] = useState("");
  const [githubBusy, setGithubBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setError(null);
      const [p, s, g, gh] = await Promise.all([
        getPreferences(token), getUsageStats(token),
        getGoogleStatus(token).catch(() => ({ connected: false })),
        getGitHubStatus(token).catch(() => ({ connected: false, login: null })),
      ]);
      setPrefs(p);
      setNameDraft(p.assistant_name);
      setStats(s);
      setGoogleConnected(g.connected);
      setGithubConnected(gh.connected);
      setGithubLogin(gh.login || null);
    } catch (e: any) {
      setError(e?.message ?? "Failed to load settings");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const save = async (patch: Partial<Pick<Preferences, "tts_voice" | "assistant_name" | "tone">>) => {
    if (!prefs) return;
    setSaving(true);
    try {
      const updated = await updatePreferences(token, patch);
      setPrefs(updated);
    } catch (e: any) {
      Alert.alert("Couldn't save", e?.message ?? "Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const connectGoogle = async () => {
    try {
      const { authorization_url } = await getGoogleConnectUrl(token);
      await Linking.openURL(authorization_url);
    } catch (e: any) {
      Alert.alert("Google Calendar & Gmail", e?.message ?? "Google OAuth is not configured yet.");
    }
  };

  const saveGitHub = async () => {
    if (!githubTokenDraft.trim()) {
      Alert.alert("GitHub", "Paste a GitHub fine-grained personal access token.");
      return;
    }
    setGithubBusy(true);
    try {
      const result = await connectGitHub(token, githubTokenDraft.trim());
      setGithubConnected(true);
      setGithubLogin(result.login || null);
      setGithubTokenDraft("");
      Alert.alert("GitHub connected", `Coding Agent can now inspect ${result.login || "your repositories"} and create approved changes.`);
    } catch (e: any) {
      Alert.alert("GitHub connection failed", e?.message ?? "Please check the token.");
    } finally {
      setGithubBusy(false);
    }
  };

  const removeGitHub = () => {
    Alert.alert("Disconnect GitHub?", "The Coding Agent will no longer access your repositories.", [
      { text: "Cancel", style: "cancel" },
      { text: "Disconnect", style: "destructive", onPress: async () => {
        try {
          await disconnectGitHub(token);
          setGithubConnected(false);
          setGithubLogin(null);
        } catch (e: any) {
          Alert.alert("GitHub", e?.message ?? "Could not disconnect.");
        }
      }},
    ]);
  };

  const enableNotifications = async () => {
    setNotificationBusy(true);
    try {
      const result = await registerDevicePushToken(token, true);
      if (!result.registered) {
        throw new Error("Notification permission was not granted. Enable it in Android Settings and retry.");
      }
      Alert.alert("Smart notifications", "VoxMate has successfully registered this device for notifications.");
    } catch (e: any) {
      Alert.alert(
        "Smart notifications",
        e?.message ?? "Could not register this device. Please retry."
      );
    } finally {
      setNotificationBusy(false);
    }
  };

  const onExport = () => {
    // Simplest reliable path on-device: open the export endpoint in the
    // browser (it's protected by the bearer token via query isn't set up,
    // so this just points the user at the API — swap for a proper
    // fetch+share-sheet flow if you want in-app download).
    Linking.openURL(`${API_URL}/account/export`);
  };

  const onDeleteAll = () => {
    Alert.alert(
      "Delete all data?",
      "This permanently deletes every conversation, uploaded document, and reminder. Your login stays active. This can't be undone.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete everything",
          style: "destructive",
          onPress: async () => {
            try {
              await deleteAllData(token);
              Alert.alert("Done", "All your data has been deleted.");
              load();
            } catch (e: any) {
              Alert.alert("Failed", e?.message ?? "Please try again.");
            }
          },
        },
      ]
    );
  };

  return (
    <AuroraBackground style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={onBack} style={styles.backButton}>
          <BlurView intensity={40} tint="dark" style={StyleSheet.absoluteFill} />
          <Ionicons name="chevron-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.title}>Settings</Text>
        <View style={{ width: 40 }} />
      </View>

      {loading ? (
        <ActivityIndicator style={{ marginTop: 40 }} color="#fff" />
      ) : error ? (
        <Text style={styles.errorText}>{error}</Text>
      ) : (
        <ScrollView contentContainerStyle={{ paddingBottom: 24 }}>
          <View style={styles.card}>
            <BlurView intensity={30} tint="dark" style={[StyleSheet.absoluteFill, { borderRadius: 14 }]} />
            <Text style={styles.sectionLabel}>Assistant name</Text>
            <View style={styles.nameRow}>
              <TextInput
                style={styles.nameInput}
                value={nameDraft}
                onChangeText={setNameDraft}
                placeholder="VoxMate"
                placeholderTextColor="#777"
                maxLength={40}
              />
              <TouchableOpacity
                style={styles.saveNameButton}
                disabled={saving || !nameDraft.trim()}
                onPress={() => save({ assistant_name: nameDraft.trim() })}
              >
                <Text style={styles.saveNameText}>Save</Text>
              </TouchableOpacity>
            </View>

            <Text style={[styles.sectionLabel, { marginTop: 18 }]}>Tone</Text>
            <View style={styles.toggleRow}>
              {(["casual", "formal"] as const).map((tone) => (
                <TouchableOpacity
                  key={tone}
                  style={[styles.toggleChip, prefs?.tone === tone && styles.toggleChipActive]}
                  disabled={saving}
                  onPress={() => save({ tone })}
                >
                  <Text style={[styles.toggleChipText, prefs?.tone === tone && styles.toggleChipTextActive]}>
                    {tone === "casual" ? "Casual" : "Formal"}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <Text style={[styles.sectionLabel, { marginTop: 18 }]}>Voice</Text>
            <View style={styles.voiceGrid}>
              {prefs?.available_voices.map((voice) => (
                <TouchableOpacity
                  key={voice}
                  style={[styles.toggleChip, prefs.tts_voice === voice && styles.toggleChipActive]}
                  disabled={saving}
                  onPress={() => save({ tts_voice: voice })}
                >
                  <Text style={[styles.toggleChipText, prefs.tts_voice === voice && styles.toggleChipTextActive]}>
                    {voice}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          {stats && (
            <View style={styles.card}>
              <BlurView intensity={30} tint="dark" style={[StyleSheet.absoluteFill, { borderRadius: 14 }]} />
              <Text style={styles.sectionLabel}>Usage</Text>
              <View style={styles.statsGrid}>
                <StatItem label="Sessions" value={stats.total_sessions} />
                <StatItem label="Messages" value={stats.total_messages} />
                <StatItem label="Code runs" value={stats.code_executions} />
                <StatItem label="Docs uploaded" value={stats.documents_uploaded} />
                <StatItem label="Searches" value={stats.searches_run} />
              </View>
            </View>
          )}

          <View style={styles.card}>
            <BlurView intensity={30} tint="dark" style={[StyleSheet.absoluteFill, { borderRadius: 14 }]} />
            <Text style={styles.sectionLabel}>Productivity integrations</Text>
            <TouchableOpacity style={styles.rowButton} onPress={connectGoogle}>
              <Ionicons name="logo-google" size={18} color="#EDEDED" />
              <Text style={styles.rowButtonText}>{googleConnected ? "Google Calendar + Gmail connected" : "Connect Google Calendar + Gmail"}</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.rowButton} onPress={enableNotifications} disabled={notificationBusy}>
              {notificationBusy ? <ActivityIndicator color="#fff" /> : <Ionicons name="notifications-outline" size={18} color="#EDEDED" />}
              <Text style={styles.rowButtonText}>Enable smart notifications</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.card}>
            <BlurView intensity={30} tint="dark" style={[StyleSheet.absoluteFill, { borderRadius: 14 }]} />
            <Text style={styles.sectionLabel}>Developer capabilities</Text>
            <TouchableOpacity style={styles.rowButton} onPress={onOpenPlatform}>
              <Ionicons name="apps-outline" size={18} color="#EDEDED" />
              <Text style={styles.rowButtonText}>Open Platform — Agents, Marketplace & Analytics</Text>
            </TouchableOpacity>
            <Text style={styles.helperText}>
              GitHub powers the Coding Agent. Read operations run automatically; branch, file and PR changes always ask for your approval.
            </Text>
            {githubConnected ? (
              <TouchableOpacity style={styles.rowButton} onPress={removeGitHub}>
                <Ionicons name="logo-github" size={18} color="#EDEDED" />
                <Text style={styles.rowButtonText}>Connected{githubLogin ? ` as ${githubLogin}` : ""} — Disconnect</Text>
              </TouchableOpacity>
            ) : (
              <>
                <TextInput
                  style={styles.tokenInput}
                  value={githubTokenDraft}
                  onChangeText={setGithubTokenDraft}
                  placeholder="GitHub fine-grained token"
                  placeholderTextColor="#777"
                  secureTextEntry
                  autoCapitalize="none"
                  autoCorrect={false}
                />
                <TouchableOpacity style={styles.rowButton} onPress={saveGitHub} disabled={githubBusy}>
                  {githubBusy ? <ActivityIndicator color="#fff" /> : <Ionicons name="logo-github" size={18} color="#EDEDED" />}
                  <Text style={styles.rowButtonText}>Connect GitHub</Text>
                </TouchableOpacity>
              </>
            )}
          </View>

          <View style={styles.card}>
            <BlurView intensity={30} tint="dark" style={[StyleSheet.absoluteFill, { borderRadius: 14 }]} />
            <Text style={styles.sectionLabel}>Your data</Text>
            <TouchableOpacity style={styles.rowButton} onPress={onExport}>
              <Ionicons name="download-outline" size={18} color="#EDEDED" />
              <Text style={styles.rowButtonText}>Export conversations</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.rowButton} onPress={onDeleteAll}>
              <Ionicons name="trash-outline" size={18} color={colors.error} />
              <Text style={[styles.rowButtonText, { color: colors.error }]}>Delete all my data</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      )}
    </AuroraBackground>
  );
}

function StatItem({ label, value }: { label: string; value: number }) {
  return (
    <View style={styles.statItem}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, paddingTop: 60, paddingHorizontal: 16 },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 16,
  },
  backButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "rgba(255,255,255,0.06)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.12)",
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },
  title: { color: "#fff", fontSize: 18, fontWeight: "700" },
  errorText: { color: colors.error, marginTop: 24, textAlign: "center" },
  card: {
    backgroundColor: "rgba(255,255,255,0.04)",
    borderRadius: 14,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.08)",
    padding: 14,
    marginBottom: 12,
    overflow: "hidden",
  },
  sectionLabel: { color: "#aaa", fontSize: 12, fontWeight: "600", textTransform: "uppercase" },
  helperText: { color: "#8f8f9f", fontSize: 12, lineHeight: 18, marginTop: 8, marginBottom: 8 },
  tokenInput: {
    color: "#fff", fontSize: 14, backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, marginTop: 6, marginBottom: 4,
  },
  nameRow: { flexDirection: "row", alignItems: "center", marginTop: 8, gap: 8 },
  nameInput: {
    flex: 1,
    color: "#fff",
    fontSize: 15,
    backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  saveNameButton: {
    backgroundColor: "rgba(124,77,255,0.30)",
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 9,
  },
  saveNameText: { color: "#fff", fontWeight: "600", fontSize: 13 },
  toggleRow: { flexDirection: "row", marginTop: 8, gap: 8 },
  voiceGrid: { flexDirection: "row", flexWrap: "wrap", marginTop: 8, gap: 8 },
  toggleChip: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 10,
    backgroundColor: "rgba(255,255,255,0.06)",
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
  },
  toggleChipActive: { backgroundColor: "rgba(124,77,255,0.30)", borderColor: "rgba(124,77,255,0.65)" },
  toggleChipText: { color: "#aaa", fontSize: 13 },
  toggleChipTextActive: { color: "#fff", fontWeight: "600" },
  statsGrid: { flexDirection: "row", flexWrap: "wrap", marginTop: 10, gap: 16 },
  statItem: { minWidth: "40%" },
  statValue: { color: "#fff", fontSize: 20, fontWeight: "700" },
  statLabel: { color: "#888", fontSize: 12, marginTop: 2 },
  rowButton: { flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 12 },
  rowButtonText: { color: "#EDEDED", fontSize: 14, fontWeight: "600" },
});
