import { Navigate, Outlet, useLocation } from "react-router-dom";
import { usePageTitle } from "./usePageTitle";
import { useApp } from "./AuthProvider";
export function ProtectedRoute() {
  const auth = useApp();
  const location = useLocation();
  usePageTitle(auth.status === "loading" ? "Restoring session" : auth.status === "error" ? "Session unavailable" : null);
  if (auth.status === "loading")
    return <p role="status">Restoring your session…</p>;
  if (auth.status === "error")
    return <div className="notice-error">
      {auth.message}
      <button className="button-secondary ml-3" onClick={auth.retry}>Try again</button>
    </div>;
  if (auth.status === "anonymous")
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search + location.hash }} />;
  return <Outlet />;
}
