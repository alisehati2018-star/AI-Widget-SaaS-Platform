"use client";

// Direction (LTR/RTL) support for the Persian-first market. Persisted in
// localStorage and applied to <html dir/lang> on the client (avoids SSR
// hydration mismatch). The design system's [dir="rtl"] rules handle layout.

import { useEffect, useState } from "react";

const KEY = "vitrin.dir";

function apply(dir: "ltr" | "rtl") {
  document.documentElement.dir = dir;
  document.documentElement.lang = dir === "rtl" ? "fa" : "en";
}

/** Mounts once to apply the saved direction. Renders nothing. */
export function DirectionInit() {
  useEffect(() => {
    const saved = (localStorage.getItem(KEY) as "ltr" | "rtl" | null) ?? "ltr";
    apply(saved);
  }, []);
  return null;
}

/** A small toggle button (EN ⇄ فا). */
export function DirectionToggle({ className = "btn btn-ghost" }: { className?: string }) {
  const [dir, setDir] = useState<"ltr" | "rtl">("ltr");

  useEffect(() => {
    setDir((localStorage.getItem(KEY) as "ltr" | "rtl" | null) ?? "ltr");
  }, []);

  function toggle() {
    const next = dir === "ltr" ? "rtl" : "ltr";
    setDir(next);
    localStorage.setItem(KEY, next);
    apply(next);
  }

  return (
    <button
      className={className}
      onClick={toggle}
      aria-label={dir === "ltr" ? "Switch to right-to-left (Persian)" : "Switch to left-to-right (English)"}
      title="Toggle text direction"
    >
      {dir === "ltr" ? "فا" : "EN"}
    </button>
  );
}
