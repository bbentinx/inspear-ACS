import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Vazio = mesma origem; Next.js faz proxy /api → backend (evita NetworkError em acesso LAN)
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "";