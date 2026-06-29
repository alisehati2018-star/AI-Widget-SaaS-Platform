import { getMessages } from "next-intl/server";
import type { Namespace } from "@/i18n/request";

// Returns only the requested namespaces so each route ships the minimum locale
// payload to the client (no global bundle). Used by the per-area layouts to
// scope their NextIntlClientProvider.
export async function scopedMessages(
  namespaces: readonly Namespace[],
): Promise<Record<string, unknown>> {
  const all = (await getMessages()) as Record<string, unknown>;
  return Object.fromEntries(namespaces.map((ns) => [ns, all[ns]]));
}
