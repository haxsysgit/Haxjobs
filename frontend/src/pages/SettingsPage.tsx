import { Link } from "react-router-dom"
import { PageHeader } from "@/components/app/PageHeader"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Settings, SlidersHorizontal } from "lucide-react"

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Control Room" description="Configure providers and preferences." />
      <div className="grid gap-4 sm:grid-cols-2">
        <Link to="/settings/providers">
          <Card className="transition-all hover:border-primary/30 hover:shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Settings className="size-5 text-muted-foreground" />
                Providers
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">Configure API provider keys and models</p>
            </CardContent>
          </Card>
        </Link>
        <Link to="/settings/preferences">
          <Card className="transition-all hover:border-primary/30 hover:shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <SlidersHorizontal className="size-5 text-muted-foreground" />
                Preferences
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">Role preferences, work modes, locations</p>
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  )
}
