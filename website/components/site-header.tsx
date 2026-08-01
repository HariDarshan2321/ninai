"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Brand } from "./brand";

export function SiteHeader() {
  const mobileMenu = useRef<HTMLDetailsElement>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const pathname = usePathname();
  const currentSection = pathname.replace(/\/$/, "");

  useEffect(() => {
    // Start refreshes at the top of the page instead of restoring the previous
    // scroll position. Hash deep links (e.g. /#product) still scroll to their
    // anchor because this only disables browser scroll restoration.
    if (typeof history !== "undefined" && "scrollRestoration" in history) {
      history.scrollRestoration = "manual";
    }
  }, []);

  function closeMobileMenu() {
    if (mobileMenu.current) {
      mobileMenu.current.open = false;
    }
  }

  return (
    <header className="site-header">
      <div className="site-header__inner shell">
        <Brand />
        <nav className="main-nav" aria-label="Primary navigation">
          <Link href="/#how-it-works">How it works</Link>
          <Link href="/local/" aria-current={currentSection === "/local" ? "page" : undefined}>Local</Link>
          <Link href="/start/" aria-current={currentSection === "/start" ? "page" : undefined}>Hosted</Link>
        </nav>
        <Link className="button button--compact button--ink" href="/start/">
          Get started
          <span aria-hidden="true">↗</span>
        </Link>
        <details
          className="mobile-nav"
          ref={mobileMenu}
          onToggle={(event) => setMobileMenuOpen(event.currentTarget.open)}
        >
          <summary aria-label={`${mobileMenuOpen ? "Close" : "Open"} navigation menu`}>
            Menu
          </summary>
          <nav className="mobile-nav__panel" aria-label="Mobile navigation">
            <Link href="/#how-it-works" onClick={closeMobileMenu}>How it works</Link>
            <Link href="/local/" aria-current={currentSection === "/local" ? "page" : undefined} onClick={closeMobileMenu}>Local</Link>
            <Link href="/start/" aria-current={currentSection === "/start" ? "page" : undefined} onClick={closeMobileMenu}>Hosted</Link>
            <Link className="mobile-nav__install" href="/install/" onClick={closeMobileMenu}>
              Install local ↗
            </Link>
          </nav>
        </details>
      </div>
    </header>
  );
}
