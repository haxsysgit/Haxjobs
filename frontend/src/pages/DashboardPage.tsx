import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function DashboardPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-heading font-bold tracking-tight">Dashboard</h2>
      <Card>
        <CardHeader>
          <CardTitle>Welcome to HaxJobs</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Your personal job search platform. Discover jobs, evaluate fit,
            generate application packs, and track every application.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
