import { Link, useLocation } from "react-router-dom"
import { useEffect, useState, useMemo } from "react"
import { motion } from "framer-motion"
import {
  Sidebar, SidebarContent, SidebarGroup, SidebarGroupContent,
  SidebarMenu, SidebarMenuButton, SidebarMenuItem, SidebarMenuSub,
  SidebarMenuSubButton, SidebarMenuSubItem,
} from "@/components/ui/sidebar"
import { ChevronDown, Home } from "lucide-react"
import { cn } from "@/lib/utils"
import { useRoles } from "@/hooks/useRoles"
import { buildSidebarLinks } from "@/lib/sidebarLinks"
import { IconRecon, IconArena, IconPack, IconControl, IconYou } from "@/components/icons"

const iconMap: Record<string, React.ElementType> = {
  Home,
  Recon: IconRecon,
  "Job Arena": IconArena,
  Packs: IconPack,
  "Control Room": IconControl,
  You: IconYou,
}

export function AppSidebar() {
  const location = useLocation()
  const [activePath, setActivePath] = useState(location.pathname)
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({})

  useEffect(() => setActivePath(location.pathname), [location.pathname])

  // Auto-open section based on current path
  useEffect(() => {
    const section = ["job-arena", "control-room", "you"].find((s) => {
      if (s === "job-arena") return location.pathname.startsWith("/jobs")
      if (s === "control-room") return location.pathname.startsWith("/settings")
      if (s === "you") return location.pathname.startsWith("/you")
      return false
    })
    if (section) {
      setExpandedSections((prev) => ({ ...prev, [section]: true }))
    }
  }, [location.pathname])

  const { roles } = useRoles()
  const sections = useMemo(() => buildSidebarLinks(roles), [roles])

  return (
    <Sidebar>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {sections.map((section) => {
                const IconComp = iconMap[section.title] || Home
                const hasChildren = section.children && section.children.length > 0
                const secKey = section.title.toLowerCase().replace(/\s+/g, "-")

                if (!hasChildren) {
                  const isActive = section.path === "/" ? activePath === "/" : activePath.startsWith(section.path)
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

                const isOpen = expandedSections[secKey] ?? false
                const isParentActive = activePath.startsWith(section.path)

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
        <div className="mx-3 mt-auto rounded-xl border border-sidebar-border/70 bg-sidebar-accent/45 px-3 py-2 text-[11px] text-sidebar-foreground/70">
          <span className="mr-2 inline-block size-1.5 rounded-full bg-sidebar-primary align-middle" />
          online, nosy, useful
        </div>
      </SidebarContent>
    </Sidebar>
  )
}
