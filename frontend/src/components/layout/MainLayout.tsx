import { useEffect, useState } from "react"
import { Outlet, useLocation, useNavigate } from "react-router-dom"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { TooltipProvider } from "@/components/ui/tooltip"
import { AppSidebar } from "./Sidebar"
import { Header } from "./Header"

function SetupGuard() {
  const location = useLocation()
  const navigate = useNavigate()
  const [checked, setChecked] = useState(false)

  useEffect(() => {
    fetch("/api/setup/status")
      .then((r) => r.json())
      .then((data: { configured: boolean }) => {
        if (!data.configured && location.pathname !== "/setup" && location.pathname !== "/onboarding") {
          navigate("/setup", { replace: true })
        }
        setChecked(true)
      })
  }, [location.pathname])

  if (!checked) return null
  return <Outlet />
}

export function MainLayout() {
  return (
    <TooltipProvider>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset>
          <Header />
          <main className="flex-1 p-6">
            <SetupGuard />
          </main>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  )
}
