import { createBrowserRouter, RouterProvider } from "react-router-dom"
import { MainLayout } from "./components/layout/MainLayout"
import { DashboardPage } from "./pages/DashboardPage"
import { JobsPage } from "./pages/JobsPage"
import { ProfilePage } from "./pages/ProfilePage"
import { SetupPage } from "./pages/SetupPage"

const router = createBrowserRouter([
  {
    element: <MainLayout />,
    children: [
      { path: "/", element: <DashboardPage /> },
      { path: "/jobs", element: <JobsPage /> },
      { path: "/profile", element: <ProfilePage /> },
      { path: "/setup", element: <SetupPage /> },
    ],
  },
])

export function App() {
  return <RouterProvider router={router} />
}
