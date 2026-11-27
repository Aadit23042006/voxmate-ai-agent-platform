import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  Alert,
  Image,
  Linking,
  Platform,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { BlurView } from "expo-blur";
import AuroraBackground from "../components/AuroraBackground";
import VoiceAssistantOrb from "../components/VoiceAssistantOrb";
import { useVoiceSession } from "../hooks/useVoiceSession";
import {
  ensureMicPermission,
  configureAudioSession,
  useAudioRecorder,
  useAudioRecorderState,
  RecordingPresets,
  readRecordingAsBase64,
} from "../services/audio";
import { takePhoto, pickImageFromLibrary, pickDocument, Attachment } from "../services/attachments";
import AttachMenu from "../components/AttachMenu";
import { getSearchHistory, SearchHistoryItem } from "../services/api";
import { colors, gradients, timeGreeting } from "../theme";
import * as FileSystem from "expo-file-system/legacy";
import * as SecureStore from "expo-secure-store";

const AGENT_LABELS: Record<string, string> = {
  math: "🧮 Math agent",
  document: "📄 Document agent",
  coding: "💻 Coding agent",
  general: "💬 General assistant",
};

type QuickAction = {
  key: string;
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
};

const QUICK_ACTIONS: QuickAction[] = [
  { key: "talk", label: "Talk", icon: "mic-outline" },
  { key: "research", label: "Research", icon: "globe-outline" },
  { key: "documents", label: "Documents", icon: "document-text-outline" },
  { key: "code", label: "Code", icon: "code-slash-outline" },
  { key: "screen", label: "Screen", icon: "scan-outline" },
  { key: "tasks", label: "Tasks", icon: "checkbox-outline" },
  { key: "meeting", label: "Meeting", icon: "people-outline" },
];

function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins} minute${mins === 1 ? "" : "s"} ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;
  return new Date(iso).toLocaleDateString();
}

type Props = {
  token: string;
  email: string;
  onLogout: () => void;
  onOpenHistory: () => void;
  onOpenSettings: () => void;
};

// Signed-in home + chat screen: greeting and voice orb when the
// conversation is empty, quick-action shortcuts, recent activity pulled
// from search history, then the live transcript once a conversation
// starts. Voice (press-and-hold mic), typed messages, and attachments
// (photo/file via the (+) menu) all still work as before — this pass
// restyles the whole surface to the "Futuristic Neon + Premium Minimal"
// design system and adds the greeting/quick-actions/recent-activity
// layout from the design brief.
export default function VoiceScreen({ token, email, onLogout, onOpenHistory, onOpenSettings }: Props) {
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [attachment, setAttachment] = useState<Attachment | null>(null);
  const [attachMenuVisible, setAttachMenuVisible] = useState(false);
  const [recent, setRecent] = useState<SearchHistoryItem[]>([]);
  const {
    connect, sendMessage, sendVoiceMessage, sendImage, sendFile,
    connected, transcript, busy, agentPlan, confirmation, confirmTool, meeting, startMeeting, endMeeting,
  } = useVoiceSession(token);

  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const recorderState = useAudioRecorderState(recorder);

  // Android does not allow an Expo app to write directly to the public Download
  // directory with a normal file:// path. We use Android's Storage Access
  // Framework once to grant access to Download, remember that URI, and then
  // every subsequent JPG/JPEG download is written there without another picker.
  const downloadGeneratedImage = async (image: { data: string; mimeType: string; filename: string }) => {
    try {
      const safeName = image.filename.replace(/[^a-zA-Z0-9._-]/g, "_");
      const fallbackName = `voxmate-image-${Date.now()}.jpg`;
      let filename = safeName || fallbackName;

      // Generated images are intended to be JPG/JPEG downloads. Make sure a
      // missing/incorrect extension does not create a file without a usable
      // image extension.
      if (!/\\.(jpe?g)$/i.test(filename)) {
        filename = filename.replace(/\\.[^.]*$/, "") + ".jpg";
      }

      if (Platform.OS === "android") {
        const STORAGE_KEY = "voxmate.android.download.directoryUri";
        const { StorageAccessFramework } = FileSystem;

        let downloadUri = await SecureStore.getItemAsync(STORAGE_KEY);

        const saveToDirectory = async (directoryUri: string) => {
          const mimeType = /\\.jpe?g$/i.test(filename) ? "image/jpeg" : (image.mimeType || "image/jpeg");
          let fileUri: string;

          try {
            fileUri = await StorageAccessFramework.createFileAsync(
              directoryUri,
              filename,
              mimeType
            );
          } catch {
            // If a file with the same name already exists, create a unique
            // filename instead of falling back to the app Documents folder.
            const dot = filename.lastIndexOf(".");
            const stem = dot > 0 ? filename.slice(0, dot) : filename;
            const ext = dot > 0 ? filename.slice(dot) : ".jpg";
            fileUri = await StorageAccessFramework.createFileAsync(
              directoryUri,
              `${stem}-${Date.now()}${ext}`,
              mimeType
            );
          }

          await StorageAccessFramework.writeAsStringAsync(
            fileUri,
            image.data,
            { encoding: FileSystem.EncodingType.Base64 }
          );

          return fileUri;
        };

        if (downloadUri) {
          try {
            await saveToDirectory(downloadUri);
            Alert.alert("Image downloaded", `Saved to the phone's Download folder as ${filename}.`);
            return;
          } catch {
            // Permission may have been revoked or the folder may no longer
            // exist. Clear the stale URI and request it again below.
            await SecureStore.deleteItemAsync(STORAGE_KEY);
            downloadUri = null;
          }
        }

        // Open the Android folder picker directly at the public Download
        // folder. The user only needs to grant this once.
        const suggestedDownloadUri = StorageAccessFramework.getUriForDirectoryInRoot("Download");
        const permission = await StorageAccessFramework.requestDirectoryPermissionsAsync(
          suggestedDownloadUri
        );

        if (!permission.granted) {
          throw new Error("Download folder access was not granted.");
        }

        downloadUri = permission.directoryUri;

        // Only remember the permission if the selected folder is actually
        // Android's Download directory.
        if (!/Download/i.test(downloadUri)) {
          throw new Error("Please select the phone's Download folder.");
        }

        await SecureStore.setItemAsync(STORAGE_KEY, downloadUri);
        await saveToDirectory(downloadUri);

        Alert.alert("Image downloaded", `Saved to the phone's Download folder as ${filename}.`);
        return;
      }

      // iOS has no Android-style public Download directory. Keep the existing
      // app Documents fallback there.
      const localPath = `${FileSystem.documentDirectory}${filename}`;
      await FileSystem.writeAsStringAsync(localPath, image.data, {
        encoding: FileSystem.EncodingType.Base64,
      });
      Alert.alert("Image downloaded", `Saved as ${filename} in VoxMate's Documents.`);
    } catch (err: any) {
      Alert.alert("Download failed", err?.message || "Could not save the generated image.");
    }
  };

  const orbState = !connected
    ? "connecting"
    : recorderState.isRecording
    ? "listening"
    : busy
    ? "speaking"
    : "idle";

  const orbLabel =
    orbState === "connecting"
      ? "Connecting…"
      : orbState === "listening"
      ? "Listening…"
      : orbState === "speaking"
      ? "Thinking…"
      : "Tap to speak";
  const orbSublabel =
    orbState === "connecting"
      ? "Setting up your session"
      : orbState === "listening"
      ? "Speak naturally"
      : orbState === "speaking"
      ? "Processing your request"
      : "Ask anything with voice, images, or text";

  useEffect(() => {
    (async () => {
      const granted = await ensureMicPermission();
      if (!granted) {
        Alert.alert("Microphone permission denied", "Voice input won't work without it — you can still type.");
        return;
      }
      await configureAudioSession();
    })();
  }, []);

  useEffect(() => {
    connect();
  }, [token, connect]);

  useEffect(() => {
    if (!confirmation) return;
    Alert.alert(
      "Confirmation required",
      `${confirmation.reason || `VoxMate wants to run ${confirmation.tool}.`}\n\nArguments: ${JSON.stringify(confirmation.arguments || {})}`,
      [
        { text: "Reject", style: "cancel", onPress: () => confirmTool(false) },
        { text: "Approve", onPress: () => confirmTool(true) },
      ],
      { cancelable: false }
    );
  }, [confirmation, confirmTool]);

  useEffect(() => {
    getSearchHistory(token)
      .then((items) => setRecent(items.slice(0, 3)))
      .catch(() => {
        // Recent activity is a decorative shortcut — a fetch failure here
        // shouldn't block or error out the rest of the home screen.
      });
  }, [token]);

  const onSend = () => {
    if (busy) return;
    const caption = input.trim();

    if (attachment) {
      if (attachment.kind === "image") {
        sendImage(attachment.base64, attachment.mimeType, caption);
      } else {
        sendFile(attachment.base64, attachment.mimeType, attachment.fileName, caption);
      }
      setAttachment(null);
      setInput("");
      return;
    }

    if (!caption) return;
    sendMessage(caption);
    setInput("");
  };

  const startRecording = async () => {
    if (busy) return;
    await recorder.prepareToRecordAsync();
    recorder.record();
  };

  const stopRecordingAndSend = async () => {
    if (!recorderState.isRecording) return;
    await recorder.stop();
    const uri = recorder.uri;
    if (!uri) return;

    try {
      const base64Audio = await readRecordingAsBase64(uri);

      // If a file/photo is staged (picked via the attach menu) it was being
      // silently dropped here — this path never looked at `attachment`, only
      // the text Send button did. Forward it first (so it lands in RAG /
      // gets analyzed) before sending the spoken question about it.
      if (attachment) {
        if (attachment.kind === "image") {
          sendImage(attachment.base64, attachment.mimeType, "");
        } else {
          sendFile(attachment.base64, attachment.mimeType, attachment.fileName, "");
        }
        setAttachment(null);
      }

      sendVoiceMessage(base64Audio, "audio/m4a");
    } catch (err: any) {
      // Previously a failure here (e.g. a huge attachment blowing past the
      // WebSocket frame size) threw silently — nothing sent, no feedback,
      // and the socket sometimes got torn down with no visible error.
      setError(err?.message || "Failed to send your message. Please try again.");
    }
  };

  const onAttachPress = () => setAttachMenuVisible(true);

  const onQuickAction = (key: string) => {
    switch (key) {
      case "talk":
        Alert.alert("Ready when you are", "Press and hold the microphone button below to talk.");
        return;
      case "research":
        setInput("Research about ");
        return;
      case "documents":
        setAttachMenuVisible(true);
        return;
      case "code":
        setInput("Write code to ");
        return;
      case "screen":
        setAttachMenuVisible(true);
        return;
      case "tasks":
        setInput("Add a task: ");
        return;
      case "meeting":
        if (meeting?.status === "recording") endMeeting();
        else startMeeting("Voice Meeting");
        return;
    }
  };

  const hasContent = input.trim().length > 0 || attachment !== null;
  const firstName = email.split("@")[0];

  return (
    <AuroraBackground style={styles.container}>
      <View style={styles.header}>
        <View style={styles.brandRow}>
          <LinearGradient colors={gradients.brand} style={styles.brandDot} />
          <Text style={styles.title}>VoxMate</Text>
          <View style={[styles.statusDot, { backgroundColor: error ? colors.error : connected ? colors.success : colors.textMuted }]} />
        </View>

        <View style={styles.headerRightGroup}>
          <TouchableOpacity style={styles.headerCircleButton} onPress={onOpenHistory}>
            <BlurView intensity={40} tint="dark" style={StyleSheet.absoluteFill} />
            <Ionicons name="time-outline" size={18} color={colors.textPrimary} />
          </TouchableOpacity>
          <TouchableOpacity style={styles.headerCircleButton} onPress={onOpenSettings}>
            <BlurView intensity={40} tint="dark" style={StyleSheet.absoluteFill} />
            <Ionicons name="settings-outline" size={18} color={colors.textPrimary} />
          </TouchableOpacity>
          <TouchableOpacity style={styles.headerCircleButton} onPress={onLogout}>
            <BlurView intensity={40} tint="dark" style={StyleSheet.absoluteFill} />
            <Ionicons name="ellipsis-horizontal" size={18} color={colors.textPrimary} />
          </TouchableOpacity>
        </View>
      </View>
      {error && <Text style={styles.errorText}>{error}</Text>}

      {transcript.length === 0 && !error ? (
        <ScrollView style={styles.transcript} contentContainerStyle={{ paddingBottom: 8 }} showsVerticalScrollIndicator={false}>
          <Text style={styles.greeting}>
            {timeGreeting()}, {firstName} 👋
          </Text>
          <Text style={styles.greetingSubtitle}>What can I help you with today?</Text>
          {meeting?.status === "recording" && (
            <Text style={{ color: colors.cyan, textAlign: "center", marginTop: 8 }}>
              ● Meeting recording active — use the mic to capture notes
            </Text>
          )}

          <View style={styles.orbBlock}>
            <VoiceAssistantOrb state={orbState} size={148} />
            <Text style={styles.orbLabel}>{orbLabel}</Text>
            <Text style={styles.orbSublabel}>{orbSublabel}</Text>
          </View>

          <View style={styles.quickGrid}>
            {QUICK_ACTIONS.map((action) => (
              <TouchableOpacity
                key={action.key}
                style={styles.quickCard}
                activeOpacity={0.75}
                onPress={() => onQuickAction(action.key)}
              >
                <BlurView intensity={26} tint="dark" style={[StyleSheet.absoluteFill, { borderRadius: 18 }]} />
                <Ionicons name={action.icon} size={20} color={colors.cyan} />
                <Text style={styles.quickCardLabel}>{action.label}</Text>
              </TouchableOpacity>
            ))}
          </View>

          {recent.length > 0 && (
            <View style={styles.recentSection}>
              <Text style={styles.recentTitle}>Recent</Text>
              {recent.map((item) => (
                <TouchableOpacity key={item.id} style={styles.recentCard} activeOpacity={0.75} onPress={onOpenHistory}>
                  <BlurView intensity={22} tint="dark" style={[StyleSheet.absoluteFill, { borderRadius: 16 }]} />
                  <Ionicons name="search-outline" size={16} color={colors.purpleSoft} style={{ marginRight: 10 }} />
                  <View style={{ flex: 1 }}>
                    <Text style={styles.recentCardTitle} numberOfLines={1}>
                      {item.query}
                    </Text>
                    <Text style={styles.recentCardTime}>{relativeTime(item.created_at)}</Text>
                  </View>
                  <Ionicons name="chevron-forward" size={16} color={colors.textMuted} />
                </TouchableOpacity>
              ))}
            </View>
          )}
        </ScrollView>
      ) : (
        <ScrollView style={styles.transcript} contentContainerStyle={{ paddingBottom: 8 }}>
          {transcript.map((entry, i) => (
            <View
              key={i}
              style={[
                styles.bubble,
                entry.role === "user" ? styles.userBubble : styles.assistantBubble,
              ]}
            >
              {entry.role === "assistant" && (
                <BlurView intensity={30} tint="dark" style={[StyleSheet.absoluteFill, { borderRadius: 16 }]} />
              )}
              {entry.role === "assistant" && entry.agent && AGENT_LABELS[entry.agent] && (
                <Text style={styles.agentBadge}>{AGENT_LABELS[entry.agent]}</Text>
              )}
              <Text style={styles.bubbleText}>{entry.text}</Text>
              {entry.image && (
                <View style={styles.generatedImageCard}>
                  <Image
                    source={{ uri: `data:${entry.image.mimeType};base64,${entry.image.data}` }}
                    style={styles.generatedImage}
                    resizeMode="cover"
                  />
                  <TouchableOpacity
                    style={styles.downloadImageButton}
                    activeOpacity={0.8}
                    onPress={() => downloadGeneratedImage(entry.image!)}
                  >
                    <Ionicons name="download-outline" size={18} color={colors.textPrimary} />
                    <Text style={styles.downloadImageText}>Download JPG/JPEG</Text>
                  </TouchableOpacity>
                </View>
              )}
              {entry.sources && entry.sources.length > 0 && (
                <View style={styles.sourcesWrap}>
                  {entry.sources.map((source, si) => (
                    <TouchableOpacity key={si} onPress={() => Linking.openURL(source.url)}>
                      <Text style={styles.sourceLink} numberOfLines={1}>
                        🔗 {source.title || source.url}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              )}
            </View>
          ))}
          {agentPlan?.steps?.length > 1 && (
            <Text style={{ color: colors.textMuted, fontSize: 12, marginTop: 8 }}>
              Agent plan: {agentPlan.steps.filter((s: any) => s.tool !== "conversation").map((s: any) => s.tool).join(" → ")}
            </Text>
          )}
          {busy && <ActivityIndicator style={{ marginTop: 8 }} color={colors.textPrimary} />}
        </ScrollView>
      )}

      {attachment && (
        <View style={styles.attachmentChip}>
          <BlurView intensity={30} tint="dark" style={[StyleSheet.absoluteFill, { borderRadius: 12 }]} />
          {attachment.kind === "image" ? (
            <Image source={{ uri: attachment.uri }} style={styles.attachmentThumb} />
          ) : (
            <View style={styles.attachmentFileIcon}>
              <Ionicons name="document-text-outline" size={20} color={colors.textPrimary} />
            </View>
          )}
          <Text style={styles.attachmentName} numberOfLines={1}>
            {attachment.fileName}
          </Text>
          <TouchableOpacity onPress={() => setAttachment(null)} style={styles.attachmentRemove}>
            <Ionicons name="close-circle" size={20} color={colors.textMuted} />
          </TouchableOpacity>
        </View>
      )}

      {recorderState.isRecording && (
        <View style={styles.listeningIndicator}>
          <Text style={styles.listeningText}>Listening</Text>
        </View>
      )}

      <View style={styles.inputBar}>
        <BlurView intensity={35} tint="dark" style={[StyleSheet.absoluteFill, { borderRadius: 30 }]} />
        <TouchableOpacity style={styles.iconButton} onPress={onAttachPress} disabled={busy}>
          <Ionicons name="add" size={22} color={colors.textSecondary} />
        </TouchableOpacity>

        <TextInput
          style={styles.input}
          value={input}
          onChangeText={setInput}
          placeholder="Tap to speak or type…"
          placeholderTextColor={colors.textMuted}
          onSubmitEditing={onSend}
        />

        <TouchableOpacity
          style={styles.micWrap}
          onPressIn={startRecording}
          onPressOut={stopRecordingAndSend}
          disabled={busy}
          activeOpacity={0.85}
        >
          {recorderState.isRecording ? (
            <LinearGradient
              colors={gradients.brandDuo}
              start={{ x: 0.2, y: 0 }}
              end={{ x: 0.9, y: 1 }}
              style={styles.micCircle}
            >
              <Ionicons name="mic" size={26} color="#fff" />
            </LinearGradient>
          ) : (
            <LinearGradient
              colors={gradients.brand}
              start={{ x: 0.15, y: 0 }}
              end={{ x: 0.9, y: 1 }}
              style={styles.micCircle}
            >
              <Ionicons name="mic" size={26} color="#fff" />
            </LinearGradient>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          onPress={onSend}
          disabled={!hasContent || busy}
          activeOpacity={0.85}
          style={styles.sendWrap}
        >
          <View style={[styles.sendButton, hasContent ? styles.sendButtonActive : styles.sendButtonDisabled]}>
            <Ionicons name={hasContent ? "send" : "close"} size={18} color={hasContent ? colors.cyan : colors.textMuted} />
          </View>
        </TouchableOpacity>
      </View>

      <AttachMenu
        visible={attachMenuVisible}
        onClose={() => setAttachMenuVisible(false)}
        onTakePhoto={async () => setAttachment(await takePhoto())}
        onUploadPhoto={async () => setAttachment(await pickImageFromLibrary())}
        onScreenScreenshot={async () => {
          try {
            const picked = await pickImageFromLibrary();
            setAttachment(picked);
            setInput("Analyze this screenshot. Explain what is visible, identify any errors or important UI details, and tell me what I should do next.");
          } catch (err: any) {
            Alert.alert("Screen understanding", err?.message || "Could not select a screenshot.");
          }
        }}
        onUploadFile={async () => {
          try {
            setAttachment(await pickDocument());
          } catch (err: any) {
            // pickDocument throws for oversized files instead of failing
            // silently later at send time — surface that here.
            Alert.alert("File too large", err?.message || "Please pick a smaller file.");
          }
        }}
      />
    </AuroraBackground>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, paddingTop: 48, paddingHorizontal: 16 },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  brandRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  brandDot: { width: 10, height: 10, borderRadius: 5 },
  headerCircleButton: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: colors.glassFill,
    borderWidth: 1,
    borderColor: colors.glassBorder,
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  },
  headerRightGroup: { flexDirection: "row", gap: 8 },
  title: { color: colors.textPrimary, fontSize: 17, fontWeight: "700", letterSpacing: 0.2 },
  statusDot: { width: 6, height: 6, borderRadius: 3, marginLeft: 2 },
  errorText: { color: colors.error, marginTop: 12, marginBottom: 4, fontSize: 13 },
  greeting: {
    color: colors.textPrimary,
    fontSize: 26,
    fontWeight: "600",
    textAlign: "center",
    marginTop: 18,
  },
  greetingSubtitle: {
    color: colors.textSecondary,
    fontSize: 14,
    textAlign: "center",
    marginTop: 6,
  },
  orbBlock: { alignItems: "center", marginTop: 8, marginBottom: 4 },
  orbLabel: { color: colors.textPrimary, fontSize: 16, fontWeight: "600", marginTop: 8 },
  orbSublabel: { color: colors.textMuted, fontSize: 12.5, marginTop: 4, textAlign: "center", paddingHorizontal: 40 },
  quickGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    marginTop: 22,
  },
  quickCard: {
    width: "31.5%",
    aspectRatio: 1,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.glassBorder,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 10,
    overflow: "hidden",
    gap: 6,
  },
  quickCardLabel: { color: colors.textSecondary, fontSize: 12, fontWeight: "600" },
  recentSection: { marginTop: 18, paddingBottom: 4 },
  recentTitle: { color: colors.textSecondary, fontSize: 13, fontWeight: "700", marginBottom: 8, textTransform: "uppercase", letterSpacing: 0.5 },
  recentCard: {
    flexDirection: "row",
    alignItems: "center",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.glassBorder,
    paddingHorizontal: 12,
    paddingVertical: 12,
    marginBottom: 8,
    overflow: "hidden",
  },
  recentCardTitle: { color: colors.textPrimary, fontSize: 13.5, fontWeight: "600" },
  recentCardTime: { color: colors.textMuted, fontSize: 11.5, marginTop: 2 },
  transcript: { flex: 1, marginBottom: 8 },
  bubble: { padding: 12, borderRadius: 16, marginBottom: 8, maxWidth: "85%", overflow: "hidden" },
  userBubble: { backgroundColor: "rgba(124,77,255,0.30)", alignSelf: "flex-end" },
  assistantBubble: {
    backgroundColor: colors.glassFill,
    borderWidth: 1,
    borderColor: colors.glassBorder,
    alignSelf: "flex-start",
  },
  generatedImageCard: {
    marginTop: 12,
    borderRadius: 14,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: colors.glassBorder,
    backgroundColor: colors.glassFill,
  },
  generatedImage: {
    width: "100%",
    aspectRatio: 1,
    backgroundColor: colors.surface,
  },
  downloadImageButton: {
    minHeight: 44,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingHorizontal: 14,
  },
  downloadImageText: {
    color: colors.textPrimary,
    fontSize: 13,
    fontWeight: "700",
  },
  bubbleText: { color: colors.textPrimary },
  agentBadge: { color: colors.textSecondary, fontSize: 11, fontWeight: "600", marginBottom: 4 },
  sourcesWrap: { marginTop: 8, gap: 4 },
  sourceLink: { color: colors.cyan, fontSize: 12 },
  attachmentChip: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.glassFill,
    borderWidth: 1,
    borderColor: colors.glassBorder,
    borderRadius: 12,
    padding: 8,
    marginBottom: 8,
    overflow: "hidden",
  },
  attachmentThumb: { width: 36, height: 36, borderRadius: 8, marginRight: 8 },
  attachmentFileIcon: {
    width: 36,
    height: 36,
    borderRadius: 8,
    backgroundColor: "rgba(255,255,255,0.12)",
    alignItems: "center",
    justifyContent: "center",
    marginRight: 8,
  },
  attachmentName: { color: colors.textPrimary, flex: 1, fontSize: 13 },
  attachmentRemove: { marginLeft: 8 },
  listeningIndicator: {
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 8,
  },
  listeningText: {
    color: colors.textPrimary,
    fontSize: 14,
    fontWeight: "600",
  },
  inputBar: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.glassFill,
    borderColor: colors.glassBorder,
    borderWidth: 1,
    borderRadius: 30,
    paddingHorizontal: 6,
    paddingVertical: 6,
    marginBottom: 24,
    overflow: "hidden",
  },
  iconButton: {
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.glassFill,
  },
  input: {
    flex: 1,
    color: colors.textPrimary,
    paddingHorizontal: 8,
    fontSize: 15,
  },
  micWrap: { marginHorizontal: 3 },
  micCircle: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: "center",
    justifyContent: "center",
  },
  sendWrap: { marginLeft: 2 },
  sendButton: {
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: "center",
    justifyContent: "center",
  },
  sendButtonActive: {
    backgroundColor: "rgba(0,217,255,0.14)",
    borderWidth: 1,
    borderColor: "rgba(0,217,255,0.5)",
  },
  sendButtonDisabled: {
    backgroundColor: colors.glassFill,
    borderWidth: 1,
    borderColor: colors.glassBorder,
  },
});
