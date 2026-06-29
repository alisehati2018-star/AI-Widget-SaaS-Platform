"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

export function Faq() {
  const t = useTranslations("marketing");
  const items = t.raw("landing.faq.items") as { q: string; a: string }[];
  const [open, setOpen] = useState<number | null>(0);

  return (
    <section className="section">
      <div className="container" style={{ maxWidth: 760 }}>
        <div className="center section-head">
          <h2>{t("landing.faq.title")}</h2>
        </div>
        <div className="faq-list">
          {items.map((item, i) => {
            const isOpen = open === i;
            return (
              <div className={`faq-item${isOpen ? " open" : ""}`} key={item.q}>
                <button
                  className="faq-q"
                  aria-expanded={isOpen}
                  onClick={() => setOpen(isOpen ? null : i)}
                >
                  <span>{item.q}</span>
                  <span className="faq-chevron" aria-hidden>
                    {isOpen ? "−" : "+"}
                  </span>
                </button>
                {isOpen ? <p className="faq-a">{item.a}</p> : null}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
