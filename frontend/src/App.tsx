import { createBrowserRouter, RouterProvider } from "react-router-dom"
import { MainLayout } from "./components/layout/MainLayout"
import HomePage from "./pages/HomePage"
import WorkspacePage from "./pages/WorkspacePage"
import DiscoveryPage from "./pages/DiscoveryPage"
import PacksPage from "./pages/PacksPage"
import ConfigPage from "./pages/ConfigPage"
import { YouPage, YouPersonaPage, YouProfilePage } from "./pages/YouPage"
import { SetupPage } from "./pages/SetupPage"
import OnboardingPage from "./pages/OnboardingPage"

const router = createBrowserRouter([
  {
    element: <MainLayout />,
    children: [
      { path: "/", element: <HomePage /> },
      { path: "/workspace", element: <WorkspacePage /> },
      { path: "/workspace/:roleId", element: <WorkspacePage /> },
      { path: "/recon", element: <DiscoveryPage /> },
      { path: "/packs", element: <PacksPage /> },
      { path: "/config", element: <ConfigPage /> },
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
