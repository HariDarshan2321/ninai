"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";

import { Brand } from "./brand";

const primaryLinks = [
  { href: "/#how-it-works", label: "How it works" },
  { href: "/local/", label: "Why local" },
  { href: "/governance/", label: "Governance" },
  { href: "/support/", label: "Help" },
] as const;

export function SiteHeader() {
  const mobileMenu = useRef<HTMLDetailsElement>(null);
  const mobileMenuButton = useRef<HTMLElement>(null);
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

  function handleMobileMenuKeyDown(event: KeyboardEvent<HTMLDetailsElement>) {
    if (event.key === "Escape" && mobileMenu.current?.open) {
      event.preventDefault();
      closeMobileMenu();
      mobileMenuButton.current?.focus({ preventScroll: true });
    }
  }

  return (
    <header className="site-header">
      <div className="site-header__inner shell">
        <Brand />
        <nav className="main-nav" aria-label="Primary navigation">
          {primaryLinks.map(({ href, label }) => (
            <Link key={href} href={href} aria-current={currentSection === href.replace(/\/$/, "") ? "page" : undefined}>
              {label}
            </Link>
          ))}
        </nav>
        <Link className="button button--compact button--ink" href="/install/">
          Get Ninai
          <span aria-hidden="true">↗</span>
        </Link>
        <details
          className="mobile-nav"
          ref={mobileMenu}
          onKeyDown={handleMobileMenuKeyDown}
          onToggle={(event) => setMobileMenuOpen(event.currentTarget.open)}
        >
          <summary ref={mobileMenuButton} aria-label={`${mobileMenuOpen ? "Close" : "Open"} navigation menu`}>
            Menu
          </summary>
          <nav className="mobile-nav__panel" aria-label="Mobile navigation">
            {primaryLinks.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                aria-current={currentSection === href.replace(/\/$/, "") ? "page" : undefined}
                onClick={closeMobileMenu}
              >
                {label}
              </Link>
            ))}
            <Link className="mobile-nav__install" href="/install/" onClick={closeMobileMenu}>
              Get Ninai <span aria-hidden="true">↗</span>
            </Link>
          </nav>
        </details>
      </div>
    </header>
  );
}
