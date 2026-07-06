import {
  Home,
  Radio,
  Swords,
  Package,
  SlidersHorizontal,
  UserRound,

} from "lucide-react"
import { FALLBACK_ROLES, type Role } from "./roles"

export interface SidebarSection {
  title: string
  icon: React.ElementType
  path: string
  children?: SidebarChild[]
}

export interface SidebarChild {
  title: string
  path: string
}

export function buildSidebarLinks(roles: Role[] = FALLBACK_ROLES): SidebarSection[] {
  return [
    { title: "Home", icon: Home, path: "/" },
    { title: "Recon", icon: Radio, path: "/discovery" },
    {
      title: "Job Arena",
      icon: Swords,
      path: "/jobs",
      children: roles.map((r) => ({
        title: r.displayName,
        path: `/jobs/${r.id}`,
      })),
    },
    { title: "Packs", icon: Package, path: "/packs" },
    {
      title: "Config",
      icon: SlidersHorizontal,
      path: "/settings",
      children: [
        { title: "Providers", path: "/settings/providers" },
        { title: "Preferences", path: "/settings/preferences" },
      ],
    },
    {
      title: "You",
      icon: UserRound,
      path: "/you",
      children: [
        ...roles.map((r) => ({
          title: r.displayName,
          path: `/you/${r.id}`,
        })),
        { title: "Profile", path: "/you/profile" },
      ],
    },
  ]
}

export function useSidebarLinks() {
  return buildSidebarLinks(FALLBACK_ROLES)
}
