"use client";

import { useState } from "react";

export function CopyCommand({ children }: { children: string }) {
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");

  function copyWithFallback() {
    const textarea = document.createElement("textarea");
    textarea.value = children;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    const copied = document.execCommand("copy");
    textarea.remove();
    return copied;
  }

  async function copy() {
    let copied = false;
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(children);
        copied = true;
      }
    } catch {
      copied = false;
    }
    if (!copied) {
      copied = copyWithFallback();
    }
    setCopyState(copied ? "copied" : "failed");
    window.setTimeout(() => setCopyState("idle"), 1600);
  }

  return (
    <div className="command-block">
      <pre><code>{children}</code></pre>
      <button type="button" onClick={copy} aria-live="polite">
        {copyState === "copied" ? "Copied" : copyState === "failed" ? "Copy failed" : "Copy"}
      </button>
    </div>
  );
}
