import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function initials(name: string) {
  return name
    .split(" ")
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function verdictColor(verdict: string) {
  switch (verdict) {
    case "STRONG FIT":
      return "text-primary bg-primary-soft border-primary/30";
    case "GOOD FIT":
      return "text-info bg-info/10 border-info/30";
    case "WEAK FIT":
      return "text-warn bg-warn/10 border-warn/30";
    default:
      return "text-danger bg-danger/10 border-danger/30";
  }
}

export function scoreColor(score: number) {
  if (score >= 80) return "var(--primary)";
  if (score >= 65) return "var(--info)";
  if (score >= 50) return "var(--warn)";
  return "var(--danger)";
}
