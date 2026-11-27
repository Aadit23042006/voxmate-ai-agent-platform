import * as ImagePicker from "expo-image-picker";
import * as DocumentPicker from "expo-document-picker";
import { readRecordingAsBase64 } from "./audio";

export type Attachment = {
  kind: "image" | "file";
  uri: string;
  base64: string;
  mimeType: string;
  fileName: string;
};

export async function ensureCameraPermission(): Promise<boolean> {
  const { granted } = await ImagePicker.requestCameraPermissionsAsync();
  return granted;
}

export async function ensureMediaLibraryPermission(): Promise<boolean> {
  const { granted } = await ImagePicker.requestMediaLibraryPermissionsAsync();
  return granted;
}

/** Opens the camera and returns the captured photo, or null if cancelled. */
export async function takePhoto(): Promise<Attachment | null> {
  const granted = await ensureCameraPermission();
  if (!granted) return null;

  const result = await ImagePicker.launchCameraAsync({
    mediaTypes: ["images"],
    base64: true,
    quality: 0.7,
  });
  return toAttachmentFromImagePicker(result);
}

/** Opens the photo library and returns the chosen photo, or null if cancelled. */
export async function pickImageFromLibrary(): Promise<Attachment | null> {
  const granted = await ensureMediaLibraryPermission();
  if (!granted) return null;

  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ["images"],
    base64: true,
    quality: 0.7,
  });
  return toAttachmentFromImagePicker(result);
}

const MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024; // 8MB raw file (~10.7MB once base64-encoded)

/** Opens the system file picker and returns the chosen document (read as
 * base64 via expo-file-system), or null if cancelled.
 * Throws if the file is too large to send safely as a single WebSocket
 * frame — this used to fail silently (the send would just never go
 * through, with no message shown to the user). */
export async function pickDocument(): Promise<Attachment | null> {
  const result = await DocumentPicker.getDocumentAsync({
    type: ["application/pdf", "text/plain", "image/*"],
    copyToCacheDirectory: true,
    multiple: false,
  });
  if (result.canceled || !result.assets?.length) return null;

  const asset = result.assets[0];
  if (asset.size && asset.size > MAX_ATTACHMENT_BYTES) {
    throw new Error(
      `"${asset.name}" is ${(asset.size / (1024 * 1024)).toFixed(1)}MB — please pick a file under 8MB.`
    );
  }

  const base64 = await readRecordingAsBase64(asset.uri);
  return {
    kind: "file",
    uri: asset.uri,
    base64,
    mimeType: asset.mimeType || "application/octet-stream",
    fileName: asset.name,
  };
}

function toAttachmentFromImagePicker(result: ImagePicker.ImagePickerResult): Attachment | null {
  if (result.canceled || !result.assets?.length) return null;
  const asset = result.assets[0];
  if (!asset.base64) return null;

  return {
    kind: "image",
    uri: asset.uri,
    base64: asset.base64,
    mimeType: asset.mimeType || "image/jpeg",
    fileName: asset.fileName || "photo.jpg",
  };
}
