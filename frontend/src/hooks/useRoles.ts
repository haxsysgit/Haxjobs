import { useQuery } from "@tanstack/react-query"
import { FALLBACK_ROLES, type Role } from "../lib/roles"
import { fixtureMode } from "../lib/fixtureMode"
// import removed
import { apiGet } from "../lib/api"

interface ProfileResponse {
  preferred_roles?: string[]
}

export function useRoles(): {
  roles: Role[]
  isLoading: boolean
} {
  const { data, isLoading } = useQuery<ProfileResponse>({
    queryKey: ["profile"],
    queryFn: () => apiGet<ProfileResponse>("/profile"),
    enabled: !fixtureMode,
    staleTime: 60_000,
    retry: false,
  })

  if (fixtureMode) {
    // ponytail: replace with actual fixture roles when profile endpoint returns them
    return { roles: FALLBACK_ROLES, isLoading: false }
  }

  if (!data?.preferred_roles?.length) {
    return { roles: FALLBACK_ROLES, isLoading }
  }

  return {
    roles: data.preferred_roles.map((id: string) => ({
      id,
      displayName: id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    })),
    isLoading,
  }
}
