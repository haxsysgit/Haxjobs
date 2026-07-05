import { createBrowserRouter, RouterProvider } from "react-router-dom"
import { MainLayout } from "./components/layout/MainLayout"
import { HomePage } from "./pages/HomePage"
import { JobsPage, JobsRolePage } from "./pages/JobsPage"
import { JobDetailPage } from "./pages/JobDetailPage"
import { DiscoveryPage } from "./pages/DiscoveryPage"
import { PacksPage } from "./pages/PacksPage"
import { SettingsPage } from "./pages/SettingsPage"
import { SettingsProvidersPage } from "./pages/SettingsProvidersPage"
import { SettingsPreferencesPage } from "./pages/SettingsPreferencesPage"
import { YouPage, YouPersonaPage, YouProfilePage } from "./pages/YouPage"
import { SetupPage } from "./pages/SetupPage"
import OnboardingPage from "./pages/OnboardingPage"

const router = createBrowserRouter([
  {
    element: <MainLayout />,
    children: [
      { path: "/", element: <HomePage /> },
      { path: "/discovery", element: <DiscoveryPage /> },
      { path: "/jobs", element: <JobsPage /> },
      { path: "/jobs/:roleId", element: <JobsRolePage /> },
      { path: "/jobs/:roleId/:jobId", element: <JobDetailPage /> },
      { path: "/jobs/detail/:jobId", element: <JobDetailPage /> },
      { path: "/packs", element: <PacksPage /> },
      { path: "/settings", element: <SettingsPage /> },
      { path: "/settings/providers", element: <SettingsProvidersPage /> },
      { path: "/settings/preferences", element: <SettingsPreferencesPage /> },
      { path: "/you", element: <YouPage /> },
      { path: "/you/:roleId", element: <YouPersonaPage /> },
      { path: "/you/profile", element: <YouProfilePage /> },
      { path: "/onboarding", element: <OnboardingPage /> },
      { path: "/setup", element: <SetupPage /> },
    ],
  },
])

export function App() {
  return <RouterProvider router={router} />
}
