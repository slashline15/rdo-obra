const API_BASE = "/api";

function getToken(): string | null {
  return localStorage.getItem("token");
}

async function apiFetchResponse(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = getToken();
  const headers = new Headers(options.headers ?? {});
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;

  if (!headers.has("Content-Type") && options.body !== undefined && !isFormData) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "/login";
    throw new Error("Não autenticado");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Erro ${res.status}`);
  }

  return res;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await apiFetchResponse(path, options);

  if (res.status === 204) return undefined as T;
  return res.json();
}

export function apiGet<T>(path: string) {
  return apiFetch<T>(path);
}

export function apiPost<T>(path: string, data?: unknown) {
  return apiFetch<T>(path, {
    method: "POST",
    body: data ? JSON.stringify(data) : undefined,
  });
}

export function apiPut<T>(path: string, data: unknown) {
  return apiFetch<T>(path, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function apiDelete(path: string) {
  return apiFetch<void>(path, { method: "DELETE" });
}

export async function apiGetText(path: string) {
  const res = await apiFetchResponse(path);
  return res.text();
}

export async function apiGetBlob(path: string) {
  const res = await apiFetchResponse(path);
  return res.blob();
}

export async function apiPostBlob(path: string, data?: unknown) {
  const res = await apiFetchResponse(path, {
    method: "POST",
    body: data ? JSON.stringify(data) : undefined,
  });
  return res.blob();
}

export async function apiLogin(
  username: string,
  password: string
): Promise<{ access_token: string }> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username, password }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Credenciais inválidas");
  }
  const data = await res.json();
  localStorage.setItem("token", data.access_token);
  return data;
}
