import { Outlet } from "react-router-dom";
import { useApp } from "../AuthProvider";
import { Footer, Header, MobileNav, Sidebar, RightRail } from "./Navigation";
export function SiteLayout() {
  const { status } = useApp();
  return <div className="min-h-screen bg-white">
    <Header authReady={status !== "loading"} />
    <MobileNav />
    <main className="mx-auto grid w-full max-w-6xl grid-cols-1 gap-7 px-4 py-8 lg:grid-cols-[210px_minmax(0,1fr)_240px]">
      <Sidebar />
      <section className="min-w-0">
        <Outlet />
      </section>
      <RightRail authReady={status !== "loading"} />
    </main>
    <Footer />
  </div>;
}
