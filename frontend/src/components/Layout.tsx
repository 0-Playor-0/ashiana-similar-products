import { NavLink, Outlet } from "react-router-dom";
import ColdStartBanner from "./ColdStartBanner";
import styles from "./Layout.module.css";

export default function Layout() {
  return (
    <div className={styles.shell}>
      <ColdStartBanner />
      <header className={styles.nav}>
        <NavLink to="/" className={styles.brand}>
          Similar pieces — a prototype for Ashiana
        </NavLink>
        <nav className={styles.links}>
          <NavLink to="/" end>
            Catalog
          </NavLink>
          <NavLink to="/under-the-hood">Under the hood</NavLink>
        </nav>
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
