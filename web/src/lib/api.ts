import { API_URL } from "./utils";

export async function fetchAPI<T>(path: string): Promise<T | null> {
  try {
    const r = await fetch(`${API_URL}/api/v1${path}`, { next: { revalidate: 30 } });
    if (!r.ok) return null;
    return r.json();
  } catch {
    return null;
  }
}