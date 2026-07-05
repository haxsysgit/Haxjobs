import { PageHeader } from "@/components/app/PageHeader"
import { Card, CardContent } from "@/components/ui/card"
import { SlidersHorizontal } from "lucide-react"

export function SettingsPreferencesPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Preferences" kicker="Control Room" description="Role preferences, work modes, and locations." />
      <Card>
        <CardContent className="py-8 text-center text-sm text-muted-foreground">
          <SlidersHorizontal className="mx-auto mb-3 size-10 text-muted-foreground/50" />
          <p>Preference editing lands after the jobs loop works.</p>
          <p className="mt-1 text-xs">Configure role priorities, target levels, and location filters here.</p>
        </CardContent>
      </Card>
    </div>
  )
}
