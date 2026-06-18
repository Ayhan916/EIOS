import apiClient from "./client";
import type {
  UserInviteRequest,
  UserInviteResponse,
  UserResponse,
  UserUpdate,
} from "@/types/api";

export async function listUsers(): Promise<UserResponse[]> {
  const { data } = await apiClient.get<UserResponse[]>("/users/");
  return data;
}

export async function updateUser(
  userId: string,
  update: UserUpdate
): Promise<UserResponse> {
  const { data } = await apiClient.patch<UserResponse>(
    `/users/${userId}`,
    update
  );
  return data;
}

export async function inviteUser(
  req: UserInviteRequest
): Promise<UserInviteResponse> {
  const { data } = await apiClient.post<UserInviteResponse>(
    "/users/invite",
    req
  );
  return data;
}
