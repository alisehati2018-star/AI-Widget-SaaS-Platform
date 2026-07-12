"use client";

// Localized API-error messages. The backend returns a stable `error.code` in
// every envelope (see packages/acip_core/errors.py); this hook maps known
// codes to the viewer's language instead of surfacing raw English server
// text. Usage at a catch site:
//
//   const apiMsg = useApiErrorMessage();
//   ...
//   setError(apiMsg(err) ?? t("common.actionFailed"));
//
// `apiMsg` returns null for non-ApiError failures (network, bugs) so each
// section supplies its own contextual fallback after `??`.

import { useCallback } from "react";
import { useTranslations } from "next-intl";
import { ApiError } from "./api";

// Keep in sync with `codes` in messages/{fa,en}/errors.json and with the
// backend's error_response call sites.
const KNOWN_CODES = new Set([
  "invalid_request", "validation_error", "invalid_body", "not_found",
  "unauthenticated", "unauthorized", "forbidden", "invalid_credentials",
  "invalid_password", "weak_password", "invalid_email", "email_taken",
  "email_unverified", "account_disabled", "invalid_token", "invalid_totp",
  "totp_already_enabled", "totp_not_enrolled", "totp_not_enabled",
  "self_action", "signup_disabled", "auth_unconfigured", "rate_limited",
  "too_long", "payload_too_large", "method_not_allowed", "es_error",
  "search_error", "agent_error", "unknown_order", "unknown_plan",
  "no_subscription", "psp_unavailable", "billing_unconfigured", "code_taken",
  "bad_signature", "internal_error", "http_error", "not_implemented",
]);

export function useApiErrorMessage(): (err: unknown) => string | null {
  const t = useTranslations("errors");
  return useCallback(
    (err: unknown) => {
      if (!(err instanceof ApiError)) return null;
      if (KNOWN_CODES.has(err.code)) return t(`codes.${err.code}`);
      // Uncoded server detail beats a generic shrug (rare: custom messages).
      return err.message || null;
    },
    [t],
  );
}
