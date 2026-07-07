import { PacksClient } from "@/components/packs/PacksClient"
import { getPacks } from "@/lib/fixtures"

export default function PacksPage() {
  return <PacksClient packs={getPacks()} />
}
