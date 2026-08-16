import Link from "next/link";

import { Brand } from "./brand";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="shell site-footer__top">
        <div>
          <Brand reversed />
          <p className="site-footer__statement">
            Remember the work.
            <br />
            Keep the rest yours.
          </p>
        </div>
        <div className="site-footer__links">
          <div>
            <p className="footer-label">Product</p>
            <Link href="/install/">Get Ninai</Link>
            <Link href="/local/">Local Claude Code + Codex</Link>
            <Link href="/start/">Cloud · coming later</Link>
            <Link href="/privacy/">Privacy</Link>
            <Link href="/terms/">Terms</Link>
          </div>
          <div>
            <p className="footer-label">Connect</p>
            <a href="https://github.com/HariDarshan2321/ninai">GitHub</a>
            <a href="mailto:hello@ninai.io">hello@ninai.io</a>
            <a href="mailto:security@ninai.io">Security</a>
          </div>
        </div>
      </div>
      <div className="shell site-footer__bottom">
        <span>© 2026 Ninai</span>
        <span>Mac MVP available · Cloud coming later</span>
      </div>
    </footer>
  );
}
