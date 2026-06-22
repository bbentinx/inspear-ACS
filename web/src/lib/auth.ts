"use client";

import { API_URL } from "./utils";

const TOKEN_KEY = "inspear_token";
const USER_KEY = "inspear_user";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: string;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function setAuth(token: string, user: AuthUser) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const r = await fetch(`${API_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail || "Falha no login");
  }
  const data = await r.json();
  setAuth(data.access_token, data.user);
  return data.user;
}

export async function fetchAuthAPI<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const r = await fetch(`${API_URL}/api/v1${path}`, { ...options, headers });
  if (r.status === 401) {
    clearAuth();
    window.location.href = "/login";
    throw new Error("Sessão expirada");
  }
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    const detail = typeof err.detail === "string" ? err.detail : null;
    throw new Error(detail || `API error: ${r.status}`);
  }
  return r.json();
}