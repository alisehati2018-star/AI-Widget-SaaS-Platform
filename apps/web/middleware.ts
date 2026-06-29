import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

export default createMiddleware(routing);

export const config = {
  // Run on everything except the API proxy, Next internals, and static files.
  // Excluding /api keeps the same-origin cookie-auth proxy untouched.
  matcher: ["/((?!api|_next|_vercel|.*\\..*).*)"],
};
