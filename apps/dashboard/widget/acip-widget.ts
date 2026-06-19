/**
 * ACIP embeddable widget (M8: REQ-M8-001/004/005).
 *
 * A lightweight, framework-free widget a store page embeds to replace native
 * search and host the grounded assistant. It consumes the public API
 * (/v1/search, /v1/chat) with a tenant-scoped key and supports white-label
 * branding (logo + colours, presentation-only — never weakens isolation).
 *
 * Embed:
 *   <div id="acip-widget"></div>
 *   <script type="module">
 *     import { mountAcipWidget } from "/widget/acip-widget.js";
 *     mountAcipWidget(document.getElementById("acip-widget"), {
 *       apiBase: "https://store.example.com",
 *       apiKey: "acip_...",          // shopper-widget (least-privilege) key
 *       primaryColor: "#1A7A4B",
 *       logoUrl: "/logo.png",
 *     });
 *   </script>
 */

export interface WidgetConfig {
  apiBase: string;
  apiKey: string;
  primaryColor?: string;
  logoUrl?: string;
  placeholder?: string;
}

interface SearchResult {
  product_id?: string;
  title?: string;
  brand?: string;
  price?: number;
}

interface ChatResponse {
  answer: string;
  citations?: SearchResult[];
  session_id?: string;
}

const DEFAULTS = { primaryColor: "#1A7A4B", placeholder: "جستجو در فروشگاه…" };

export function mountAcipWidget(host: HTMLElement | null, config: WidgetConfig): void {
  if (!host) throw new Error("acip-widget: host element not found");
  const color = config.primaryColor ?? DEFAULTS.primaryColor;
  let sessionId: string | undefined;

  host.innerHTML = "";
  const root = document.createElement("div");
  root.style.fontFamily = "system-ui, sans-serif";
  root.style.border = `1px solid ${color}`;
  root.style.borderRadius = "8px";
  root.style.padding = "12px";

  if (config.logoUrl) {
    const img = document.createElement("img");
    img.src = config.logoUrl;
    img.style.height = "24px";
    root.appendChild(img);
  }

  const input = document.createElement("input");
  input.type = "search";
  input.placeholder = config.placeholder ?? DEFAULTS.placeholder;
  input.style.width = "100%";
  input.style.padding = "8px";
  input.style.boxSizing = "border-box";

  const results = document.createElement("ul");
  const chatLog = document.createElement("div");

  async function runSearch(query: string): Promise<void> {
    results.innerHTML = "";
    const resp = await fetch(`${config.apiBase}/v1/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-api-key": config.apiKey },
      body: JSON.stringify({ query }),
    });
    if (!resp.ok) return;
    const data = (await resp.json()) as { results?: SearchResult[] };
    for (const r of data.results ?? []) {
      const li = document.createElement("li");
      li.textContent = `${r.title ?? ""}${r.price != null ? ` — ${r.price}` : ""}`;
      results.appendChild(li);
    }
  }

  async function askAssistant(message: string): Promise<void> {
    const resp = await fetch(`${config.apiBase}/v1/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-api-key": config.apiKey },
      body: JSON.stringify({ message, session_id: sessionId }),
    });
    if (!resp.ok) return;
    const data = (await resp.json()) as ChatResponse;
    sessionId = data.session_id ?? sessionId;
    const bubble = document.createElement("p");
    bubble.textContent = data.answer;
    chatLog.appendChild(bubble);
    // Render citation cards (REQ-M8-005).
    for (const c of data.citations ?? []) {
      const card = document.createElement("small");
      card.style.display = "block";
      card.style.color = color;
      card.textContent = `↳ ${c.title ?? c.product_id ?? ""}`;
      chatLog.appendChild(card);
    }
  }

  input.addEventListener("keydown", (e: KeyboardEvent) => {
    if (e.key !== "Enter") return;
    const q = input.value.trim();
    if (!q) return;
    void runSearch(q);
    void askAssistant(q);
  });

  root.appendChild(input);
  root.appendChild(results);
  root.appendChild(chatLog);
  host.appendChild(root);
}
