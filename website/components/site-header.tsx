"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { Brand } from "./brand";

export function SiteHeader() {
  const mobileMenu = useRef<HTMLDetailsElement>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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
          <Link href="/#product">Product</Link>
          <Link href="/#how-it-works">How it works</Link>
          <Link href="/privacy/">Trust</Link>
          <Link href="/research/">Research</Link>
        </nav>
        <Link className="button button--compact button--ink" href="/install/">
          Install Ninai
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
            <Link href="/#product" onClick={closeMobileMenu}>Product</Link>
            <Link href="/#how-it-works" onClick={closeMobileMenu}>How it works</Link>
            <Link href="/privacy/" onClick={closeMobileMenu}>Trust</Link>
            <Link href="/research/" onClick={closeMobileMenu}>Research</Link>
            <Link className="mobile-nav__install" href="/install/" onClick={closeMobileMenu}>
              Install Ninai ↗
            </Link>
          </nav>
        </details>
      </div>
    </header>
  );
}
