"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { MouseEvent } from "react";

export function Brand({ reversed = false }: { reversed?: boolean }) {
  const pathname = usePathname();

  function handleClick(event: MouseEvent<HTMLAnchorElement>) {
    // Clicking the logo while already on the home route does not trigger a
    // Next.js navigation (same path), so scroll back to the top ourselves.
    if (pathname === "/" && event.button === 0 && !event.metaKey && !event.ctrlKey &&
        !event.altKey && !event.shiftKey) {
      event.preventDefault();
      const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      window.scrollTo({ top: 0, behavior: reduceMotion ? "instant" : "smooth" });
      // Clear a stale #hash so the address bar matches the top-of-page state.
      if (window.location.hash) {
        history.replaceState(null, "", "/");
      }
    }
  }

  return (
    <Link className="brand" href="/" aria-label="Ninai home" onClick={handleClick}>
      <img
        className={`brand__wordmark${reversed ? " brand__wordmark--reversed" : ""}`}
        src="/assets/ninai-wordmark.svg"
        alt="Ninai"
        width="640"
        height="257"
      />
    </Link>
  );
}
