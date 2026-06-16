import apiClient from "./client";
import type {
  AccessTokenResponse,
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  UserResponse,
} from "@/types/api";

export async function login(data: LoginRequest): Promise<TokenResponse> {
  const res = await apiClient.post<TokenResponse>("/auth/login", data);
  return res.data;
}

export async function register(data: RegisterRequest): Promise<TokenResponse> {
  const res = await apiClient.post<TokenResponse>("/auth/register", data);
  return res.data;
}

export async function getMe(): Promise<UserResponse> {
  const res = await apiClient.get<UserResponse>("/auth/me");
  return res.data;
}

export async function refreshToken(
  refreshToken: string
): Promise<AccessTokenResponse> {
  const res = await apiClient.post<AccessTokenResponse>("/auth/refresh", {
    refresh_token: refreshToken,
  });
  return res.data;
}
