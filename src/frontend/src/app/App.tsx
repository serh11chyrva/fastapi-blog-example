import { AuthProvider } from "./AuthProvider";
import { AppRoutes } from "./routes";
import { NotificationsProvider } from "../features/notifications/NotificationsProvider";
export default function App() {
  return <AuthProvider>
    <NotificationsProvider><AppRoutes /></NotificationsProvider>
  </AuthProvider>;
}
