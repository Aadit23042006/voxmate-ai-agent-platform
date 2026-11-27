import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { BlurView } from "expo-blur";
import AuroraBackground from "../components/AuroraBackground";
import { colors, gradients } from "../theme";
import VoiceAssistantOrb from "../components/VoiceAssistantOrb";
import { ApiError, login, register } from "../services/api";
import { saveSession } from "../services/authStorage";

type Mode = "login" | "register";

// Full-screen Login / Register combined view. Creates a real VoxMate
// account (or signs into an existing one) instead of the old
// auto-registered throwaway demo user. There is no usage cap on the
// backend, so every signed-in account gets unlimited requests.
export default function AuthScreen({
  onAuthenticated,
}: {
  onAuthenticated: (token: string, email: string) => void;
}) {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isRegister = mode === "register";

  const validate = (): string | null => {
    if (!email.trim()) return "Enter your email";
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) return "Enter a valid email";
    if (password.length < 6) return "Password must be at least 6 characters";
    if (isRegister && password !== confirmPassword) return "Passwords don't match";
    return null;
  };

  const onSubmit = async () => {
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const { access_token } = isRegister
        ? await register(email.trim(), password)
        : await login(email.trim(), password);
      await saveSession(access_token, email.trim());
      onAuthenticated(access_token, email.trim());
    } catch (e: unknown) {
      if (e instanceof ApiError) {
        if (e.status === 401) {
          setError("Invalid email or password. Check your details and try again.");
        } else if (e.status === 400 && isRegister) {
          setError("This email is already registered. Please log in instead.");
        } else if (e.status === 422) {
          setError("Please enter a valid email and password.");
        } else {
          setError(`The server could not complete the request (HTTP ${e.status}). Please try again.`);
        }
      } else if (e instanceof Error && e.message === "NETWORK_ERROR") {
        setError("Cannot reach VoxMate server. Check that your phone and computer are on the same Wi-Fi.");
      } else if (e instanceof Error && e.message === "INVALID_AUTH_RESPONSE") {
        setError("The server returned an invalid login response. Please contact support.");
      } else {
        setError("Could not complete sign-in. Please try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuroraBackground style={styles.container}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.brandBlock}>
            <VoiceAssistantOrb state="idle" size={72} />
            <Text style={styles.title}>VoxMate</Text>
            <Text style={styles.subtitle}>
              {isRegister ? "Create your account" : "Welcome back"}
            </Text>
          </View>

          <View style={styles.card}>
            <BlurView intensity={45} tint="dark" style={[StyleSheet.absoluteFill, { borderRadius: 24 }]} />
            <View style={styles.tabRow}>
              <TouchableOpacity
                style={styles.tab}
                onPress={() => {
                  setMode("login");
                  setError(null);
                }}
              >
                {!isRegister ? (
                  <LinearGradient
                    colors={gradients.brand}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                    style={styles.tabActive}
                  >
                    <Text style={styles.tabTextActive}>Log In</Text>
                  </LinearGradient>
                ) : (
                  <Text style={styles.tabText}>Log In</Text>
                )}
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.tab}
                onPress={() => {
                  setMode("register");
                  setError(null);
                }}
              >
                {isRegister ? (
                  <LinearGradient
                    colors={gradients.brand}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                    style={styles.tabActive}
                  >
                    <Text style={styles.tabTextActive}>Register</Text>
                  </LinearGradient>
                ) : (
                  <Text style={styles.tabText}>Register</Text>
                )}
              </TouchableOpacity>
            </View>

            <View style={styles.inputGroup}>
              <Ionicons name="mail-outline" size={18} color="#aaa" style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                value={email}
                onChangeText={setEmail}
                placeholder="Email"
                placeholderTextColor="#777"
                autoCapitalize="none"
                keyboardType="email-address"
                autoCorrect={false}
              />
            </View>

            <View style={styles.inputGroup}>
              <Ionicons name="lock-closed-outline" size={18} color="#aaa" style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                value={password}
                onChangeText={setPassword}
                placeholder="Password"
                placeholderTextColor="#777"
                secureTextEntry={!showPassword}
                autoCapitalize="none"
              />
              <TouchableOpacity onPress={() => setShowPassword((v) => !v)}>
                <Ionicons
                  name={showPassword ? "eye-off-outline" : "eye-outline"}
                  size={18}
                  color="#aaa"
                />
              </TouchableOpacity>
            </View>

            {isRegister && (
              <View style={styles.inputGroup}>
                <Ionicons name="lock-closed-outline" size={18} color="#aaa" style={styles.inputIcon} />
                <TextInput
                  style={styles.input}
                  value={confirmPassword}
                  onChangeText={setConfirmPassword}
                  placeholder="Confirm Password"
                  placeholderTextColor="#777"
                  secureTextEntry={!showPassword}
                  autoCapitalize="none"
                />
              </View>
            )}

            {error && <Text style={styles.errorText}>{error}</Text>}

            <TouchableOpacity onPress={onSubmit} disabled={loading} activeOpacity={0.85}>
              <LinearGradient
                colors={gradients.brand}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.submitButton}
              >
                {loading ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.submitText}>
                    {isRegister ? "Create Account" : "Log In"}
                  </Text>
                )}
              </LinearGradient>
            </TouchableOpacity>

            <Text style={styles.unlimitedNote}>
              <Ionicons name="infinite-outline" size={13} color={colors.cyan} /> Unlimited usage —
              no message or request limits
            </Text>
          </View>

          <TouchableOpacity
            onPress={() => {
              setMode(isRegister ? "login" : "register");
              setError(null);
            }}
          >
            <Text style={styles.switchText}>
              {isRegister ? "Already have an account? " : "New to VoxMate? "}
              <Text style={styles.switchTextBold}>
                {isRegister ? "Log In" : "Create one"}
              </Text>
            </Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </AuroraBackground>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scrollContent: { flexGrow: 1, paddingHorizontal: 24, paddingTop: 80, paddingBottom: 40 },
  brandBlock: { alignItems: "center", marginBottom: 28 },
  title: { color: "#fff", fontSize: 26, fontWeight: "700", marginTop: 12 },
  subtitle: { color: "#aaa", fontSize: 14, marginTop: 4 },
  card: {
    backgroundColor: "rgba(255,255,255,0.04)",
    borderRadius: 24,
    padding: 20,
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.1)",
    overflow: "hidden",
  },
  tabRow: {
    flexDirection: "row",
    backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 14,
    padding: 4,
    marginBottom: 20,
    overflow: "hidden",
  },
  tab: { flex: 1 },
  tabActive: { paddingVertical: 10, borderRadius: 10, alignItems: "center" },
  tabText: { color: "#aaa", fontWeight: "600", fontSize: 14, textAlign: "center", paddingVertical: 10 },
  tabTextActive: { color: "#fff", fontWeight: "600", fontSize: 14 },
  inputGroup: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 14,
    paddingHorizontal: 14,
    marginBottom: 14,
    height: 48,
  },
  inputIcon: { marginRight: 10 },
  input: { flex: 1, color: "#fff", fontSize: 15 },
  errorText: { color: "#FF6B6B", fontSize: 13, marginBottom: 12 },
  submitButton: {
    borderRadius: 14,
    height: 48,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 4,
  },
  submitText: { color: "#fff", fontWeight: "700", fontSize: 15 },
  unlimitedNote: {
    color: colors.cyan,
    fontSize: 12,
    textAlign: "center",
    marginTop: 16,
  },
  switchText: { color: "#aaa", textAlign: "center", marginTop: 24, fontSize: 13 },
  switchTextBold: { color: "#fff", fontWeight: "700" },
});
