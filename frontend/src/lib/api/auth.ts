import axios from "axios";
import apiClient from "./client";
import type {
  AccessTokenResponse,
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  UserResponse,
} from "@/types/api";

const BACKEND_ORIGIN =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const BASE_URL = `${BACKEND_ORIGIN}/api/v1`;

// Use plain axios (no interceptors) so 401 from login/register propagates to the form
const authAxios = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

export async function login(data: LoginRequest): Promise<TokenResponse> {
  const res = await authAxios.post<TokenResponse>("/auth/login", data);
  return res.data;
}

export async function register(data: RegisterRequest): Promise<TokenResponse> {
  const res = await authAxios.post<TokenResponse>("/auth/register", data);
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
