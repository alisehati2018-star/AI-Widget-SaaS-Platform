import { createNavigation } from "next-intl/navigation";
import { routing } from "./routing";

// Locale-aware drop-in replacements for next/link & next/navigation. Every
// internal link/redirect MUST come from here so the active locale is preserved.
export const { Link, redirect, usePathname, useRouter, getPathname } =
  createNavigation(routing);
