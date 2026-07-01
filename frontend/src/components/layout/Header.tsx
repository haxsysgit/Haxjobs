import { Separator } from "@/components/ui/separator"

export function Header() {
  return (
    <header className="flex h-14 items-center gap-4 border-b px-6">
      <h1 className="text-lg font-heading font-semibold">HaxJobs</h1>
      <Separator orientation="vertical" className="h-6" />
      <span className="text-sm text-muted-foreground">
        Self-hosted job search
      </span>
    </header>
  )
}
