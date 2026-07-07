import { Link, useLocation } from "react-router-dom"
import React, { useEffect, useState, useMemo } from "react"
import { motion } from "framer-motion"
import {
  Sidebar, SidebarContent, SidebarGroup, SidebarGroupContent, SidebarGroupLabel,
  SidebarMenu, SidebarMenuButton, SidebarMenuItem, SidebarMenuSub,
  SidebarMenuSubButton, SidebarMenuSubItem, SidebarSeparator,
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
              {sections
                .filter((s) => s.title === "Dashboard" || s.title === "Workspace")
                .map((section) => (
                  <SidebarMenuItem key={section.title}>
                    <SidebarMenuButton
                      isActive={!!(section.path === "/" ? activePath === "/" : section.path && activePath.startsWith(section.path))}
                      render={
                        <Link to={section.path} onClick={() => setActivePath(section.path)} className="flex w-full items-center gap-2">
                          {iconMap[section.title] && React.createElement(iconMap[section.title])}
                          <span>{section.title}</span>
                          {activePath === section.path && (
                            <motion.span layoutId="active-sidebar-dot" className="ml-auto size-2 rounded-full bg-sidebar-primary" />
                          )}
                        </Link>
                      }
                    />
                  </SidebarMenuItem>
                ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarSeparator />

        <SidebarGroup>
          <SidebarGroupLabel>Tools</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {sections
                .filter((s) => ["Recon", "Packs", "Config"].includes(s.title))
                .map((section) => (
                  <SidebarMenuItem key={section.title}>
                    <SidebarMenuButton
                      isActive={!!(section.path && activePath.startsWith(section.path))}
                      render={
                        <Link to={section.path} onClick={() => setActivePath(section.path)} className="flex w-full items-center gap-2">
                          {iconMap[section.title] && React.createElement(iconMap[section.title])}
                          <span>{section.title}</span>
                          {section.path && activePath.startsWith(section.path) && (
                            <motion.span layoutId="active-sidebar-dot" className="ml-auto size-2 rounded-full bg-sidebar-primary" />
                          )}
                        </Link>
                      }
                    />
                  </SidebarMenuItem>
                ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarSeparator />

        {/* You dropdown */}
        {(() => {
          const youSection = sections.find((s) => s.title === "You")
          if (!youSection?.children?.length) return null
          const secKey = "you"
          const isOpen = expandedSections[secKey] ?? false
          const isParentActive = activePath.startsWith("/you")
          const IconComp = iconMap["You"] || UserRound
          return (
            <SidebarGroup key="you-group">
              <SidebarGroupLabel>You</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  <SidebarMenuItem>
                    <SidebarMenuButton
                      isActive={!!isParentActive}
                      onClick={() => setExpandedSections((prev) => ({ ...prev, [secKey]: !isOpen }))}
                    >
                      <IconComp className={cn(isParentActive && "text-sidebar-primary")} />
                      <span>You</span>
                      <ChevronDown className={cn("ml-auto size-4 transition-transform duration-200", isOpen && "rotate-180")} />
                    </SidebarMenuButton>
                    <div className={cn("grid transition-all duration-200", isOpen ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0")}>
                      <div className="overflow-hidden">
                        <SidebarMenuSub>
                          {youSection.children.map((child) => {
                            const isChildActive = activePath === child.path
                            return (
                              <SidebarMenuSubItem key={child.path}>
                                <SidebarMenuSubButton
                                  isActive={isChildActive}
                                  render={
                                    <Link to={child.path} onClick={() => setActivePath(child.path)} className="flex w-full items-center gap-2">
                                      <span>{child.title}</span>
                                      {isChildActive && <motion.span layoutId="active-sidebar-dot" className="ml-auto size-1.5 rounded-full bg-sidebar-primary" />}
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
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          )
        })()}

        <SidebarSeparator />

        {/* Workspaces dropdown */}
        {(() => {
          const wsSection = sections.find((s) => s.title === "Workspaces")
          if (!wsSection?.children?.length) return null
          const secKey = "workspaces"
          const isOpen = expandedSections[secKey] ?? false
          return (
            <SidebarGroup key="workspaces-group">
              <SidebarGroupLabel>Workspaces</SidebarGroupLabel>
              <SidebarGroupContent>
                <SidebarMenu>
                  <SidebarMenuItem>
                    <SidebarMenuButton
                      onClick={() => setExpandedSections((prev) => ({ ...prev, [secKey]: !isOpen }))}
                    >
                      <MessagesSquare />
                      <span>Workspaces</span>
                      <ChevronDown className={cn("ml-auto size-4 transition-transform duration-200", isOpen && "rotate-180")} />
                    </SidebarMenuButton>
                    <div className={cn("grid transition-all duration-200", isOpen ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0")}>
                      <div className="overflow-hidden">
                        <SidebarMenuSub>
                          {wsSection.children.map((child) => (
                            <SidebarMenuSubItem key={child.path}>
                              <SidebarMenuSubButton
                                isActive={activePath === child.path}
                                render={
                                  <Link to={child.path} onClick={() => setActivePath(child.path)} className="flex w-full items-center gap-2">
                                    <span>{child.title}</span>
                                    {activePath === child.path && <motion.span layoutId="active-sidebar-dot" className="ml-auto size-1.5 rounded-full bg-sidebar-primary" />}
                                  </Link>
                                }
                              />
                            </SidebarMenuSubItem>
                          ))}
                        </SidebarMenuSub>
                      </div>
                    </div>
                  </SidebarMenuItem>
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          )
        })()}

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
