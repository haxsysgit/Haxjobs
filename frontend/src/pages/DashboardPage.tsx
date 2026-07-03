import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-heading font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">Your job search cockpit.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Welcome to HaxJobs</CardTitle>
          <CardDescription>Your personal job search platform.</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Use Discovery to find jobs, Jobs to review them, and Profile to tune what HaxJobs knows about you.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
