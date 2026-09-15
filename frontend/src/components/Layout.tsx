import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import ColdStartBanner from "./ColdStartBanner";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import styles from "./Layout.module.css";

// The global header search doubles as the catalog's title filter (?q=) and
// a cross-page search: typed while already on the catalog, it debounces
// straight into the URL for a live filter; typed anywhere else, it only
// takes effect on submit, navigating to the catalog with that query — per
// docs/DESIGN.md, replacing the catalog page's old local search input
// rather than duplicating it.
export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const isCatalog = location.pathname === "/";
  const urlQuery = searchParams.get("q") ?? "";

  const [draft, setDraft] = useState(urlQuery);

  // Stay in sync with URL changes that didn't come from typing here — the
  // catalog page's "Clear filters", the back/forward buttons, a hand-edited
  // URL — rather than fighting them.
  useEffect(() => {
    setDraft(urlQuery);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlQuery]);

  const debouncedDraft = useDebouncedValue(draft, 250);

  useEffect(() => {
    if (!isCatalog || debouncedDraft === urlQuery) return;
    const next = new URLSearchParams(searchParams);
    if (debouncedDraft.trim()) next.set("q", debouncedDraft);
    else next.delete("q");
    setSearchParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedDraft, isCatalog]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!isCatalog) {
      navigate(draft.trim() ? `/?q=${encodeURIComponent(draft.trim())}` : "/");
    }
  };

  return (
    <div className={styles.shell}>
      <header>
        <div className={styles.strip}>Technical Submission for Internship - AI/ML and Web Dev</div>
        <ColdStartBanner />
        <div className={styles.nav}>
          <NavLink to="/" className={styles.brand}>
            Ashiana
          </NavLink>
          <form className={styles.searchForm} onSubmit={handleSubmit} role="search">
            <input
              type="search"
              className={styles.searchInput}
              placeholder="Search anything…"
              aria-label="Search products by title"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
            />
          </form>
        </div>
      </header>
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
