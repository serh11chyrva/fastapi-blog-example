import { Outlet, useMatch } from "react-router-dom";
import { Footer, Navigation, RightRail } from "./Navigation";

export function SiteLayout() {
  const settings = useMatch("/settings/*");
  return <div className="site-shell">
    <Navigation />
    <main className={settings ? "site-column settings-column" : "site-column"} id="top">
      <Outlet />
      <Footer />
    </main>
    {!settings && <RightRail />}
  </div>;
}
