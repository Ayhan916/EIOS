import type {
  NotificationListResponse,
  NotificationPreferences,
} from "@/types/api";
import apiClient from "./client";

export async function listNotifications(): Promise<NotificationListResponse> {
  const { data } = await apiClient.get<NotificationListResponse>("/notifications/");
  return data;
}

export async function markNotificationRead(notificationId: string): Promise<void> {
  await apiClient.patch(`/notifications/${notificationId}/read`);
}

export async function markAllNotificationsRead(): Promise<void> {
  await apiClient.patch("/notifications/read-all");
}

export async function getNotificationPreferences(): Promise<NotificationPreferences> {
  const { data } = await apiClient.get<{ notification_preferences: NotificationPreferences }>(
    "/auth/me"
  );
  return data.notification_preferences;
}

export async function updateNotificationPreferences(
  prefs: Partial<NotificationPreferences>
): Promise<void> {
  await apiClient.patch("/auth/me", { notification_preferences: prefs });
}
