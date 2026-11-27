import * as SecureStore from "expo-secure-store";

const TOKEN_KEY = "voxmate_access_token";
const EMAIL_KEY = "voxmate_email";

export async function saveSession(token: string, email: string) {
  await SecureStore.setItemAsync(TOKEN_KEY, token);
  await SecureStore.setItemAsync(EMAIL_KEY, email);
}

export async function loadToken(): Promise<string | null> {
  return SecureStore.getItemAsync(TOKEN_KEY);
}

export async function loadEmail(): Promise<string | null> {
  return SecureStore.getItemAsync(EMAIL_KEY);
}

export async function clearSession() {
  await SecureStore.deleteItemAsync(TOKEN_KEY);
  await SecureStore.deleteItemAsync(EMAIL_KEY);
}
