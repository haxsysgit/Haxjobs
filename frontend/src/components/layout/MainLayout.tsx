import { useEffect, useState } from "react"
import { Outlet, useLocation, useNavigate } from "react-router-dom"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { TooltipProvider } from "@/components/ui/tooltip"
import { AppSidebar } from "./Sidebar"
import { Header } from "./Header"

function RouteGuard() {
  const location = useLocation()
  const navigate = useNavigate()
  const [checked, setChecked] = useState(false)

  useEffect(() => {
    async function check() {
      try {
        const [setupRes, onboardRes] = await Promise.all([
          fetch("/api/setup/status").then((r) => r.json()),
          fetch("/api/onboarding/status").then((r) => r.json()),
        ])

        const setupDone: boolean = setupRes.configured
        const onboardDone: boolean = onboardRes.stage === "complete"
        const path = location.pathname

        if (!setupDone && path !== "/setup") {
          navigate("/setup", { replace: true })
        } else if (setupDone && !onboardDone && path !== "/onboarding" && !path.startsWith("/settings")) {
          navigate("/onboarding", { replace: true })
        }
      } catch {
        // server down, let the page render and handle its own errors
      }
      setChecked(true)
    }
    check()
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
            <RouteGuard />
          </main>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  )
}
