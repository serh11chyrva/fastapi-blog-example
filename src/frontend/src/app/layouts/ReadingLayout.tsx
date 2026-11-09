import { Outlet } from "react-router-dom";
import { useApp } from "../AuthProvider";
import { Footer, Header } from "./Navigation";
export function ReadingLayout() {
  const { status } = useApp();
  return <div className="min-h-screen bg-white">
    <Header authReady={status !== "loading"} fullscreen />
    <main className="mx-auto min-h-[calc(100vh-4rem)] w-full max-w-[1440px] px-5 py-10 sm:px-8">
      <Outlet />
    </main>
    <Footer />
  </div>;
}
