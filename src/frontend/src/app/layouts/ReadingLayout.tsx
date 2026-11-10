import { Outlet } from "react-router-dom";
import { Navigation } from "./Navigation";

export function ReadingLayout() {
  return <div className="reading-shell">
    <Navigation reading />
    <main className="reading-column" id="top"><Outlet /></main>
  </div>;
}
