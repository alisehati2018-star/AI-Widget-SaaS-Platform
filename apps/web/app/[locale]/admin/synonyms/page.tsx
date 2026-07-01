"use client";

import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";
import { adminFetch as authFetch } from "@/lib/auth";
import { DashboardShell, useAdminNav } from "@/components/shell";
import { Alert, Spinner } from "@/components/ui";

interface TenantRow { id: string; name: string }

export default function AdminSynonyms() {
  const t = useTranslations("admin");
  const nav = useAdminNav();
  const [tenants, setTenants] = useState<TenantRow[]>([]);
  const [selected, setSelected] = useState("");
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    authFetch<{ tenants: TenantRow[] }>("/admin/tenants")
      .then((r) => {
        setTenants(r.tenants);
        if (r.tenants[0]) setSelected(r.tenants[0].id);
      })
      .catch(() => setTenants([]));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    setSaved(false);
    authFetch<{ synonyms: string[] }>(`/admin/synonyms?tenant=${encodeURIComponent(selected)}`)
      .then((r) => setText(r.synonyms.join("\n")))
      .catch(() => setText(""))
      .finally(() => setLoading(false));
  }, [selected]);

  async function save() {
    const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
    await authFetch(`/admin/synonyms?tenant=${encodeURIComponent(selected)}`, { body: { synonyms: lines } });
    setSaved(true);
  }

  const ruleCount = text.split("\n").map((l) => l.trim()).filter(Boolean).length;

  return (
    <DashboardShell title={t("synonyms.title")} nav={nav} requireAdmin loginHref="/admin/login">
      <div className="row-between" style={{ marginTop: "-1rem", marginBottom: "1.5rem", flexWrap: "wrap", gap: ".75rem" }}>
        <p style={{ margin: 0 }}>{t("synonyms.intro")}</p>
        <select className="input" style={{ maxWidth: 260 }} value={selected} onChange={(e) => setSelected(e.target.value)}>
          {tenants.length === 0 ? <option value="">{t("common.noTenants")}</option> : null}
          {tenants.map((tn) => <option key={tn.id} value={tn.id}>{tn.name}</option>)}
        </select>
      </div>

      <div className="dash-2col">
        <div className="card">
          <div className="row-between">
            <h3 style={{ margin: 0 }}>{t("synonyms.synonyms")}</h3>
            <span className="hint">{t("synonyms.count", { n: ruleCount })}</span>
          </div>
          {saved ? <Alert kind="success">{t("synonyms.saved")}</Alert> : null}
          {loading ? (
            <Spinner />
          ) : (
            <textarea
              className="input"
              style={{ minHeight: 340, fontFamily: "monospace" }}
              value={text}
              onChange={(e) => { setText(e.target.value); setSaved(false); }}
              placeholder={"laptop, notebook, لپ‌تاپ\nmobile, cellphone, موبایل"}
            />
          )}
          <div style={{ marginTop: "1rem" }}>
            <button className="btn btn-primary" onClick={() => void save()} disabled={!selected}>{t("synonyms.save")}</button>
          </div>
        </div>

        <div className="card">
          <h3>{t("synonyms.helpTitle")}</h3>
          <p className="hint">{t("synonyms.helpBody")}</p>
          <h4>{t("synonyms.helpExampleTitle")}</h4>
          <pre className="code-block">{"laptop, notebook, لپ‌تاپ\nmobile, cellphone, موبایل\nsneaker, trainer, کتانی"}</pre>
        </div>
      </div>
    </DashboardShell>
  );
}
