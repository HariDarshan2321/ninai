"use client";

import { useEffect, useState } from "react";

const email = "hello@ninai.io";

export default function EmailContact({
  label,
  subject,
  summaryClassName = "button button--line",
}: {
  label: string;
  subject: string;
  summaryClassName?: string;
}) {
  const [message, setMessage] = useState("");
  const [ready, setReady] = useState(false);

  useEffect(() => setReady(true), []);

  async function copyEmail() {
    try {
      await navigator.clipboard.writeText(email);
      setMessage("Email address copied.");
    } catch {
      setMessage("Select and copy the email address above.");
    }
  }

  return (
    <details className="email-contact">
      <summary className={summaryClassName}>
        {label}
        <span className="email-contact__indicator" aria-hidden="true" />
      </summary>
      <div className="email-contact__panel">
        <p>Email <strong>{email}</strong></p>
        <p>Subject <strong>{subject}</strong></p>
        <div className="email-contact__actions">
          {ready && (
            <button className="button button--compact button--line" type="button" onClick={copyEmail}>
              Copy email address
            </button>
          )}
          <a href={`mailto:${email}?subject=${encodeURIComponent(subject)}`}>Open email app</a>
        </div>
        <p className="email-contact__status" role="status">{message}</p>
      </div>
    </details>
  );
}
