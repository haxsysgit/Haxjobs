import { useLocation, Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { roleDisplayName } from "@/lib/roles"
import { cn } from "@/lib/utils"
import { apiGet } from "@/lib/api"

const sectionLabels: Record<string, string> = {
  "/": "Home",
  "/discovery": "Recon",
  "/jobs": "Job Arena",
  "/packs": "Packs",
  "/settings": "Control Room",
  "/you": "You",
}

function buildBreadcrumbs(pathname: string): { label: string; href?: string }[] {
  const crumbs: { label: string; href?: string }[] = []

  // Home is implied; skip for root
  if (pathname === "/") {
    crumbs.push({ label: "Home" })
    return crumbs
  }

  // Determine section
  const seg1 = "/" + (pathname.split("/")[1] || "")
  const sectionLabel = sectionLabels[seg1]
  if (sectionLabel) {
    crumbs.push({ label: sectionLabel, href: seg1 })
  } else {
    crumbs.push({ label: "Home", href: "/" })
  }

  // Subpage
  const segments = pathname.split("/").filter(Boolean)
  if (segments.length >= 2) {
    const sub = segments[1]
    const roleName = roleDisplayName(sub)
    crumbs.push({ label: roleName })
  } else if (segments.length === 1 && seg1 === "/settings") {
    crumbs.push({ label: "Overview" })
  } else if (segments.length === 1 && seg1 === "/you") {
    crumbs.push({ label: "Personas" })
  }

  return crumbs
}

export function Header() {
  const location = useLocation()
  const crumbs = buildBreadcrumbs(location.pathname)

  const { data: setup } = useQuery<{ configured: boolean }>({
    queryKey: ["setup-status"],
    queryFn: () => apiGet<{ configured: boolean }>("/setup/status"),
    retry: false,
    staleTime: 60_000,
  })

  const { data: onboard } = useQuery<{ stage?: string }>({
    queryKey: ["onboarding-status"],
    queryFn: () => apiGet<{ stage?: string }>("/onboarding/status"),
    retry: false,
    staleTime: 60_000,
  })

  const setupDone = setup?.configured
  const onboardDone = onboard?.stage === "complete"

  let statusLabel = "Setup needed"
  let statusVariant = "amber"
  if (setupDone && !onboardDone) {
    statusLabel = "Profile draft"
    statusVariant = "amber"
  } else if (setupDone && onboardDone) {
    statusLabel = "Active"
    statusVariant = "green"
  }

  return (
    <header className="flex h-14 items-center gap-3 border-b px-6">
      <SidebarTrigger className="md:hidden" />
      <nav className="flex flex-1 items-center gap-1.5 text-sm">
        {crumbs.map((crumb, i) => (
          <span key={crumb.label} className="flex items-center gap-1.5">
            {i > 0 && (
              <span className="text-muted-foreground/40" aria-hidden="true">/</span>
            )}
            {crumb.href ? (
              <Link
                to={crumb.href}
                className={cn(
                  "transition-colors hover:text-foreground",
                  i === crumbs.length - 1
                    ? "font-medium text-foreground"
                    : "text-muted-foreground"
                )}
              >
                {crumb.label}
              </Link>
            ) : (
              <span className="font-medium text-foreground">{crumb.label}</span>
            )}
          </span>
        ))}
      </nav>
      <span
        className={cn(
          "shrink-0 rounded-full border px-2.5 py-0.5 text-[10px] font-medium",
          statusVariant === "green" && "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
          statusVariant === "amber" && "border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400"
        )}
      >
        {statusLabel}
      </span>
    </header>
  )
}
