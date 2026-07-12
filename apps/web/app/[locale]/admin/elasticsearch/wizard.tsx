"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { useApiErrorMessage } from "@/lib/errors";
import { adminFetch as authFetch } from "@/lib/auth";
import { formatTime } from "@/lib/datetime";
import type { Locale } from "@/i18n/routing";
import { Badge, Field, Input, Spinner } from "@/components/ui";

export interface LogEntry {
  at: string; // ISO timestamp
  step: string;
  ok: boolean;
  detail: string;
}

type StepState = "pending" | "running" | "done" | "failed" | "skipped";

/** First-run setup wizard: ensure-index → (optional) reindex → alias swap,
 *  executed sequentially with a live operation log. Each step drives the
 *  existing /admin/es endpoints — the wizard is pure orchestration. */
export function SetupWizard({
  onDone,
  log,
  appendLog,
}: {
  onDone: () => unknown;
  log: LogEntry[];
  appendLog: (e: LogEntry) => void;
}) {
  const t = useTranslations("admin");
  const apiMsg = useApiErrorMessage();
  const locale = useLocale() as Locale;
  const [source, setSource] = useState("");
  const [running, setRunning] = useState(false);
  const [steps, setSteps] = useState<Record<string, StepState>>({
    ensure: "pending", reindex: "pending", alias: "pending",
  });

  function mark(step: string, state: StepState) {
    setSteps((s) => ({ ...s, [step]: state }));
  }

  async function runStep(step: string, label: string, fn: () => unknown) {
    mark(step, "running");
    try {
      const r = await fn();
      mark(step, "done");
      appendLog({ at: new Date().toISOString(), step: label, ok: true, detail: JSON.stringify(r) });
      return true;
    } catch (e) {
      mark(step, "failed");
      const msg = apiMsg(e) ?? t("elasticsearch.actionFailed");
      appendLog({ at: new Date().toISOString(), step: label, ok: false, detail: msg });
      return false;
    }
  }

  async function run() {
    setRunning(true);
    setSteps({ ensure: "pending", reindex: "pending", alias: "pending" });
    let newIndex: string | null = null;

    const okEnsure = await runStep("ensure", t("elasticsearch.wizardStepEnsure"), async () => {
      const r = await authFetch<{ index?: string; status?: string }>("/admin/es/ensure-index", { body: {} });
      newIndex = r.index ?? null;
      return r;
    });
    if (!okEnsure) { setRunning(false); return; }

    if (source.trim()) {
      const okReindex = await runStep("reindex", t("elasticsearch.wizardStepReindex"), async () => {
        const r = await authFetch<{ new_index?: string }>("/admin/es/reindex", {
          body: { source_index: source.trim() },
        });
        newIndex = r.new_index ?? newIndex;
        return r;
      });
      if (!okReindex) { setRunning(false); return; }
    } else {
      mark("reindex", "skipped");
      appendLog({
        at: new Date().toISOString(),
        step: t("elasticsearch.wizardStepReindex"),
        ok: true,
        detail: t("elasticsearch.wizardSkippedNoSource"),
      });
    }

    const target = newIndex;
    if (target) {
      await runStep("alias", t("elasticsearch.wizardStepAlias"), () =>
        authFetch("/admin/es/alias", { body: { index: target } }),
      );
    } else {
      mark("alias", "skipped");
      appendLog({
        at: new Date().toISOString(),
        step: t("elasticsearch.wizardStepAlias"),
        ok: true,
        detail: t("elasticsearch.wizardSkippedNoIndex"),
      });
    }
    setRunning(false);
    await onDone();
  }

  const tone = (s: StepState) =>
    s === "done" ? "success" : s === "failed" ? "warning" : undefined;
  const stateLabel = (s: StepState) =>
    s === "pending" ? t("elasticsearch.wizardPending")
      : s === "running" ? t("elasticsearch.wizardRunning")
        : s === "done" ? t("elasticsearch.wizardDone")
          : s === "failed" ? t("elasticsearch.wizardFailed")
            : t("elasticsearch.wizardSkipped");

  return (
    <div className="dash-2col-even" style={{ marginBottom: "1.5rem" }}>
      <div className="card">
        <h3>{t("elasticsearch.wizardTitle")}</h3>
        <p className="hint">{t("elasticsearch.wizardHint")}</p>
        <table className="table">
          <tbody>
            {([
              ["ensure", t("elasticsearch.wizardStepEnsure"), t("elasticsearch.wizardStepEnsureHint")],
              ["reindex", t("elasticsearch.wizardStepReindex"), t("elasticsearch.wizardStepReindexHint")],
              ["alias", t("elasticsearch.wizardStepAlias"), t("elasticsearch.wizardStepAliasHint")],
            ] as const).map(([key, label, hint], i) => (
              <tr key={key}>
                <td style={{ whiteSpace: "nowrap" }}>{i + 1}. {label}</td>
                <td className="muted">{hint}</td>
                <td>
                  {steps[key] === "running"
                    ? <Spinner />
                    : <Badge tone={tone(steps[key])}>{stateLabel(steps[key])}</Badge>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="row" style={{ flexWrap: "wrap", alignItems: "flex-end", gap: ".75rem" }}>
          <Field label={t("elasticsearch.wizardSourceLabel")} hint={t("elasticsearch.wizardSourceHint")}>
            <Input dir="ltr" value={source} onChange={(e) => setSource(e.target.value)} placeholder={t("elasticsearch.wizardSourcePlaceholder")} />
          </Field>
          <button className="btn btn-primary" disabled={running} onClick={() => void run()} style={{ marginBottom: "1rem" }}>
            {running ? <Spinner /> : t("elasticsearch.wizardRun")}
          </button>
        </div>
      </div>

      <div className="card">
        <h3>{t("elasticsearch.logTitle")}</h3>
        {log.length === 0 ? <p className="muted">{t("elasticsearch.logEmpty")}</p> : (
          <div style={{ maxHeight: 320, overflowY: "auto" }}>
            <table className="table">
              <tbody>
                {log.map((e, i) => (
                  <tr key={i}>
                    <td className="muted" style={{ whiteSpace: "nowrap" }}>{formatTime(e.at, locale)}</td>
                    <td>{e.step}</td>
                    <td>{e.ok ? <Badge tone="success">{t("elasticsearch.logOk")}</Badge> : <Badge tone="warning">{t("elasticsearch.logFail")}</Badge>}</td>
                    <td className="muted" dir="ltr" style={{ fontSize: ".78rem", overflowWrap: "anywhere", maxWidth: 260 }}>{e.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="hint" style={{ marginTop: ".75rem" }}>{t("elasticsearch.logHint")}</p>
      </div>
    </div>
  );
}
