/** ponytail: static role map — in production roles come from profile API. */
export interface Role {
  id: string
  displayName: string
}

export const FALLBACK_ROLES: Role[] = [
  { id: "backend_python", displayName: "Backend Developer" },
  { id: "full_stack", displayName: "Full Stack Engineer" },
  { id: "ai_ml", displayName: "AI/ML Engineer" },
  { id: "waiter", displayName: "Waiter" },
]

export function roleDisplayName(id: string): string {
  return FALLBACK_ROLES.find((r) => r.id === id)?.displayName ?? id.replace(/_/g, " ")
}

export function roleFromPath(path: string): string | null {
  const match = path.match(/^\/(?:jobs|you)\/(.+)$/)
  return match ? match[1] : null
}
