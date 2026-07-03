import { createBrowserRouter, RouterProvider } from "react-router-dom"
import { MainLayout } from "./components/layout/MainLayout"
import { DashboardPage } from "./pages/DashboardPage"
import { JobsPage } from "./pages/JobsPage"
import { ProfilePage } from "./pages/ProfilePage"
import { SetupPage } from "./pages/SetupPage"
import OnboardingPage from "./pages/OnboardingPage"

const router = createBrowserRouter([
  {
    element: <MainLayout />,
    children: [
      { path: "/", element: <DashboardPage /> },
      { path: "/jobs", element: <JobsPage /> },
      { path: "/onboarding", element: <OnboardingPage /> },
      { path: "/profile", element: <ProfilePage /> },
      { path: "/setup", element: <SetupPage /> },
    ],
  },
])

export function App() {
  return <RouterProvider router={router} />
}
