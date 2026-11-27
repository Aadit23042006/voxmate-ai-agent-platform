import {
  AudioModule,
  RecordingPresets,
  setAudioModeAsync,
  useAudioRecorder,
  useAudioRecorderState,
  useAudioPlayer,
} from "expo-audio";
import { File, Paths } from "expo-file-system";

export async function ensureMicPermission(): Promise<boolean> {
  const status = await AudioModule.requestRecordingPermissionsAsync();
  return status.granted;
}

export async function configureAudioSession() {
  await setAudioModeAsync({
    playsInSilentMode: true,
    allowsRecording: true,
    shouldPlayInBackground: false,
    shouldRouteThroughEarpiece: false,
  });
}

// Re-exported so the recording hook + preset live in one place.
export { useAudioRecorder, useAudioRecorderState, useAudioPlayer, RecordingPresets };

/** Reads a recorded file (by its local URI) back out as a base64 string,
 * ready to send over the WebSocket. */
export async function readRecordingAsBase64(uri: string): Promise<string> {
  const file = new File(uri);
  return await file.base64();
}

/** Writes base64 audio received from the server (e.g. a TTS reply) to a
 * temporary local file and returns its URI, so it can be handed to an
 * audio player for playback. */
export function writeBase64ToTempFile(base64Audio: string, extension: string = "wav"): string {
  const file = new File(Paths.cache, `voxmate-tts-${Date.now()}.${extension}`);
  file.write(base64Audio, { encoding: "base64" });
  return file.uri;
}
