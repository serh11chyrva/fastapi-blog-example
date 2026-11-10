import { NavLink, Outlet } from "react-router-dom";
import { Icon } from "../../shared/ui/Icon";

export function SettingsLayout() {
  return <div className="settings-layout">
    <nav className="settings-nav" aria-label="Settings">
      <h2>Settings</h2>
      <div>
        <NavLink className="sidebar-link" to="profile"><Icon name="user" />Profile</NavLink>
        <NavLink className="sidebar-link" to="sessions"><Icon name="device" />Active sessions</NavLink>
      </div>
    </nav>
    <div className="settings-content"><Outlet /></div>
  </div>;
}
