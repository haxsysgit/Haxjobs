import { Link, useLocation } from "react-router-dom"
import { useEffect, useState, useMemo } from "react"
import { motion } from "framer-motion"
import {
  Sidebar, SidebarContent, SidebarGroup, SidebarGroupContent,
  SidebarMenu, SidebarMenuButton, SidebarMenuItem, SidebarMenuSub,
  SidebarMenuSubButton, SidebarMenuSubItem,
} from "@/components/ui/sidebar"
import { ChevronDown, LayoutDashboard, MessagesSquare, Radio, Package, SlidersHorizontal, UserRound, Moon, Sun, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"
import { useRoles } from "@/hooks/useRoles"
import { useTheme } from "@/hooks/useTheme"
import { buildSidebarLinks } from "@/lib/sidebarLinks"
import { HaxJobsLockup } from "@/components/brand/HaxJobsLockup"

export function AppSidebar() {
  const location = useLocation()
  const [activePath, setActivePath] = useState(location.pathname)
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({})

  useEffect(() => setActivePath(location.pathname), [location.pathname])

  // Auto-open section based on current path
  useEffect(() => {
    const section = ["workspaces", "you"].find((s) => {
      if (s === "workspaces") return location.pathname.startsWith("/workspace/")
      if (s === "you") return location.pathname.startsWith("/you")
      return false
    })
    if (section) {
      setExpandedSections((prev) => ({ ...prev, [section]: true }))
    }
  }, [location.pathname])

  const { roles } = useRoles()
  const sections = useMemo(() => buildSidebarLinks(roles), [roles])
  const { theme, toggle } = useTheme()

  const iconMap: Record<string, React.ElementType> = {
    Dashboard: LayoutDashboard,
    Workspace: MessagesSquare,
    Recon: Radio,
    Packs: Package,
    Config: SlidersHorizontal,
    You: UserRound,
  }

  return (
    <Sidebar>
      <SidebarContent>
        {/* Brand lockup */}
        <div className="px-3 pt-5 pb-3">
          <Link to="/" className="inline-block">
            <HaxJobsLockup markSize={34} variant={theme === "dark" ? "color" : "light"} showTagline animated />
          </Link>
        </div>

        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {sections.map((section) => {
                const hasChildren = section.children && section.children.length > 0
                const secKey = section.title.toLowerCase().replace(/\s+/g, "-")

                // Section label (Workspaces — not clickable, no icon)
                if (!section.icon && hasChildren) {
                  const isOpen = expandedSections[secKey] ?? false
                  return (
                    <SidebarMenuItem key={section.title}>
                      <div
                        onClick={() => setExpandedSections((prev) => ({ ...prev, [secKey]: !isOpen }))}
                        className="mt-4 flex cursor-pointer items-center gap-2 px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-sidebar-foreground/50"
                      >
                        <span>{section.title}</span>
                        <ChevronDown
                          className={cn(
                            "ml-auto size-3 transition-transform duration-200",
                            isOpen && "rotate-180"
                          )}
                        />
                      </div>
                      <div
                        className={cn(
                          "grid transition-all duration-200",
                          isOpen ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
                        )}
                      >
                        <div className="overflow-hidden">
                          <SidebarMenuSub>
                            {section.children?.map((child) => {
                              const isChildActive = activePath === child.path
                              return (
                                <SidebarMenuSubItem key={child.path}>
                                  <SidebarMenuSubButton
                                    isActive={isChildActive}
                                    render={
                                      <Link to={child.path} onClick={() => setActivePath(child.path)} className="flex w-full items-center gap-2">
                                        <span>{child.title}</span>
                                        {isChildActive && (
                                          <motion.span
                                            layoutId="active-sidebar-dot"
                                            className="ml-auto size-1.5 rounded-full bg-sidebar-primary"
                                          />
                                        )}
                                      </Link>
                                    }
                                  />
                                </SidebarMenuSubItem>
                              )
                            })}
                          </SidebarMenuSub>
                        </div>
                      </div>
                    </SidebarMenuItem>
                  )
                }

                // Regular clickable items
                const IconComp = iconMap[section.title] || LayoutDashboard
                const isActive = section.path === "/" ? activePath === "/" : section.path && activePath.startsWith(section.path)

                if (!hasChildren) {
                  return (
                    <SidebarMenuItem key={section.title}>
                      <SidebarMenuButton
                        isActive={isActive}
                        render={
                          <Link to={section.path} onClick={() => setActivePath(section.path)} className="flex w-full items-center gap-2">
                            <IconComp />
                            <span>{section.title}</span>
                            {isActive && (
                              <motion.span
                                layoutId="active-sidebar-dot"
                                className="ml-auto size-2 rounded-full bg-sidebar-primary"
                              />
                            )}
                          </Link>
                        }
                      />
                    </SidebarMenuItem>
                  )
                }

                // Dropdown sections (You)
                const isOpen = expandedSections[secKey] ?? false
                const isParentActive = section.path && activePath.startsWith(section.path)

                return (
                  <SidebarMenuItem key={section.title}>
                    <SidebarMenuButton
                      isActive={isParentActive}
                      onClick={() => setExpandedSections((prev) => ({ ...prev, [secKey]: !isOpen }))}
                    >
                      <IconComp className={cn(isParentActive && "text-sidebar-primary")} />
                      <span>{section.title}</span>
                      <ChevronDown
                        className={cn(
                          "ml-auto size-4 transition-transform duration-200",
                          isOpen && "rotate-180"
                        )}
                      />
                    </SidebarMenuButton>
                    <div
                      className={cn(
                        "grid transition-all duration-200",
                        isOpen ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0"
                      )}
                    >
                      <div className="overflow-hidden">
                        <SidebarMenuSub>
                          {section.children?.map((child) => {
                            const isChildActive = activePath === child.path
                            return (
                              <SidebarMenuSubItem key={child.path}>
                                <SidebarMenuSubButton
                                  isActive={isChildActive}
                                  render={
                                    <Link to={child.path} onClick={() => setActivePath(child.path)} className="flex w-full items-center gap-2">
                                      <span>{child.title}</span>
                                      {isChildActive && (
                                        <motion.span
                                          layoutId="active-sidebar-dot"
                                          className="ml-auto size-1.5 rounded-full bg-sidebar-primary"
                                        />
                                      )}
                                    </Link>
                                  }
                                />
                              </SidebarMenuSubItem>
                            )
                          })}
                        </SidebarMenuSub>
                      </div>
                    </div>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {/* Roadmap card */}
        <div className="mx-3 mt-4 rounded-xl border border-sidebar-border/50 bg-sidebar-accent/30 p-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-sidebar-primary">
            <Sparkles size={13} /> Roadmap
          </div>
          <p className="mt-1 leading-relaxed text-[11px] text-sidebar-foreground/60">
            Next up: Hax finds hiring managers on LinkedIn and drafts outreach for you.
          </p>
        </div>

        {/* Footer — agent status + theme toggle */}
        <div className="mx-3 mt-auto flex items-center gap-2 rounded-xl border border-sidebar-border/70 bg-sidebar-accent/45 px-3 py-2 text-[11px] text-sidebar-foreground/70">
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <span className="inline-block size-1.5 shrink-0 rounded-full bg-sidebar-primary" />
            <span className="truncate">online, nosy, useful</span>
          </div>
          <button
            onClick={toggle}
            className="shrink-0 rounded-md p-1 transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground"
            aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          >
            {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
          </button>
        </div>
      </SidebarContent>
    </Sidebar>
  )
}
