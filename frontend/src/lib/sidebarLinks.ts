import {
  LayoutDashboard,
  MessagesSquare,
  Radio,
  Package,
  SlidersHorizontal,
  UserRound,
} from "lucide-react"
import { FALLBACK_ROLES, type Role } from "./roles"

export interface SidebarSection {
  title: string
  icon: React.ElementType | null
  path: string
  children?: SidebarChild[]
}

export interface SidebarChild {
  title: string
  path: string
}

export function buildSidebarLinks(roles: Role[] = FALLBACK_ROLES): SidebarSection[] {
  return [
    { title: "Dashboard", icon: LayoutDashboard, path: "/" },
    { title: "Workspace", icon: MessagesSquare, path: "/workspace" },
    { title: "Recon", icon: Radio, path: "/recon" },
    { title: "Packs", icon: Package, path: "/packs" },
    { title: "Config", icon: SlidersHorizontal, path: "/config" },
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
    {
      title: "Workspaces",
      icon: null,
      path: "",
      children: roles.map((r) => ({
        title: `${r.displayName} hunt`,
        path: `/workspace/${r.id}`,
      })),
    },
  ]
}

export function useSidebarLinks() {
  return buildSidebarLinks(FALLBACK_ROLES)
}
