import Link from "next/link";

export default function NotFound() {
  return (
    <main className="not-found" id="main-content">
      <div className="not-found__code">404</div>
      <p className="section-label">Memory not found</p>
      <h1>This context does not exist.</h1>
      <p>The page may have moved, expired, or never entered the permitted scope.</p>
      <Link className="button button--acid" href="/">Return home ↗</Link>
    </main>
  );
}
