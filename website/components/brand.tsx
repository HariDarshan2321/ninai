"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { MouseEvent } from "react";

export function Brand({ reversed = false }: { reversed?: boolean }) {
  const pathname = usePathname();

  function handleClick(event: MouseEvent<HTMLAnchorElement>) {
    // Clicking the logo while already on the home route does not trigger a
    // Next.js navigation (same path), so scroll back to the top ourselves.
    if (pathname === "/") {
      event.preventDefault();
      window.scrollTo({ top: 0, behavior: "smooth" });
      // Clear a stale #hash so the address bar matches the top-of-page state.
      if (window.location.hash) {
        history.replaceState(null, "", "/");
      }
    }
  }

  return (
    <Link className="brand" href="/" aria-label="Ninai home" onClick={handleClick}>
      <img
        className="brand__wordmark"
        src={
          reversed
            ? "/assets/ninai-wordmark-reversed.svg"
            : "/assets/ninai-wordmark.svg"
        }
        alt="Ninai"
        width="640"
        height="257"
      />
    </Link>
  );
}
