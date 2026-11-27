import { Platform } from "react-native";
import Constants from "expo-constants";
import * as Notifications from "expo-notifications";
import { registerPushToken } from "./api";

export async function registerDevicePushToken(
  authToken: string,
  requestPermission = false
): Promise<{ registered: boolean; reason?: string }> {
  let permission = await Notifications.getPermissionsAsync();

  if (permission.status !== "granted" && requestPermission) {
    permission = await Notifications.requestPermissionsAsync();
  }

  if (permission.status !== "granted") {
    return { registered: false, reason: "permission-not-granted" };
  }

  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("default", {
      name: "VoxMate notifications",
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      sound: "default",
    });
  }

  const projectId =
    Constants.expoConfig?.extra?.eas?.projectId ||
    Constants.easConfig?.projectId;

  if (!projectId) {
    throw new Error(
      "Expo EAS project ID is missing. Check the app configuration."
    );
  }

  const tokenResult = await Notifications.getExpoPushTokenAsync({ projectId });

  if (!tokenResult.data) {
    throw new Error("Expo did not return a push token. Please retry.");
  }

  await registerPushToken(authToken, tokenResult.data, Platform.OS);
  return { registered: true };
}
