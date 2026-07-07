import { useEffect } from "react"
import { Outlet, useLocation, useNavigate } from "react-router-dom"
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { TooltipProvider } from "@/components/ui/tooltip"
import { AppSidebar } from "./Sidebar"

function RouteGuard() {
  const location = useLocation()
  const navigate = useNavigate()

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
        } else if (setupDone && !onboardDone && path !== "/onboarding" && !path.startsWith("/config")) {
          navigate("/onboarding", { replace: true })
        }
      } catch {
        // server down, let the page render
      }
    }
    check()
  }, [location.pathname])

  return <Outlet />
}

export function MainLayout() {
  return (
    <TooltipProvider>
      <SidebarProvider defaultOpen={true}>
        <AppSidebar />
        <SidebarInset>
          <header className="flex h-12 shrink-0 items-center gap-2 border-b border-sidebar-border px-4">
            <SidebarTrigger className="-ml-1" />
          </header>
          <main className="flex-1 overflow-hidden">
            <RouteGuard />
          </main>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  )
}
