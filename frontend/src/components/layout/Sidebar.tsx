import { Link, useLocation } from "react-router-dom"
import { useEffect, useState } from "react"
import {
  Sidebar, SidebarContent, SidebarGroup, SidebarGroupContent,
  SidebarMenu, SidebarMenuButton, SidebarMenuItem,
} from "@/components/ui/sidebar"
import { LayoutDashboard, Briefcase, User, Settings, UserRoundPlus } from "lucide-react"

const items = [
  { title: "Dashboard", url: "/", icon: LayoutDashboard },
  { title: "Jobs", url: "/jobs", icon: Briefcase },
  { title: "Onboarding", url: "/onboarding", icon: UserRoundPlus },
  { title: "Setup", url: "/setup", icon: Settings },
  { title: "Profile", url: "/profile", icon: User },
]

export function AppSidebar() {
  const location = useLocation()
  const [activePath, setActivePath] = useState(location.pathname)

  useEffect(() => setActivePath(location.pathname), [location.pathname])

  return (
    <Sidebar>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => {
                const isActive = item.url === "/" ? activePath === "/" : activePath.startsWith(item.url)
                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      isActive={isActive}
                      render={
                        <Link to={item.url} onClick={() => setActivePath(item.url)}>
                          <item.icon />
                          <span>{item.title}</span>
                        </Link>
                      }
                    />
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  )
}
