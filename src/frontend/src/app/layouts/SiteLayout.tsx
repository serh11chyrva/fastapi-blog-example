import { Outlet } from "react-router-dom";
import { Footer, Navigation, RightRail } from "./Navigation";

export function SiteLayout() {
  return <div className="site-shell">
    <Navigation />
    <main className="site-column" id="top">
      <Outlet />
      <Footer />
    </main>
    <RightRail />
  </div>;
}
