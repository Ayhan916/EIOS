import type { TokenResponse } from "@/types/api";

const DEMO_FLAG = "eios_demo_mode";
const REAL_ACCESS = "eios_real_access_token";
const REAL_REFRESH = "eios_real_refresh_token";
const ACCESS_KEY = "eios_access_token";
const REFRESH_KEY = "eios_refresh_token";

export function isDemoMode(): boolean {
  if (typeof window === "undefined") return false;
  return sessionStorage.getItem(DEMO_FLAG) === "true";
}

export function enterDemoMode(response: TokenResponse): void {
  // Save real tokens to sessionStorage before overwriting localStorage
  const realAccess = localStorage.getItem(ACCESS_KEY);
  const realRefresh = localStorage.getItem(REFRESH_KEY);
  if (realAccess) sessionStorage.setItem(REAL_ACCESS, realAccess);
  if (realRefresh) sessionStorage.setItem(REAL_REFRESH, realRefresh);
  sessionStorage.setItem(DEMO_FLAG, "true");

  // Swap in demo tokens
  localStorage.setItem(ACCESS_KEY, response.access_token);
  localStorage.setItem(REFRESH_KEY, response.refresh_token);

  window.location.replace("/");
}

export function exitDemoMode(): void {
  const realAccess = sessionStorage.getItem(REAL_ACCESS);
  const realRefresh = sessionStorage.getItem(REAL_REFRESH);

  if (realAccess) {
    localStorage.setItem(ACCESS_KEY, realAccess);
  } else {
    localStorage.removeItem(ACCESS_KEY);
  }
  if (realRefresh) {
    localStorage.setItem(REFRESH_KEY, realRefresh);
  } else {
    localStorage.removeItem(REFRESH_KEY);
  }

  sessionStorage.removeItem(DEMO_FLAG);
  sessionStorage.removeItem(REAL_ACCESS);
  sessionStorage.removeItem(REAL_REFRESH);

  window.location.replace("/");
}
