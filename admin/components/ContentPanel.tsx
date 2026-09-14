"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "./api";
import styles from "@/app/page.module.css";

const fields: { key: string; label: string; multiline?: boolean }[] = [
  { key: "hero_eyebrow", label: "כותרת משנה בבאנר" },
  { key: "hero_title_first", label: "כותרת ראשית — חלק ראשון" },
  { key: "hero_title_second", label: "כותרת ראשית — חלק שני" },
  { key: "hero_description", label: "תיאור בבאנר", multiline: true },
  { key: "about_title", label: "כותרת אודות" },
  { key: "about_body", label: "תיאור אודות", multiline: true },
  { key: "equipment_title", label: "כותרת מכשור" },
  { key: "equipment_intro", label: "תיאור מכשור", multiline: true },
  { key: "materials_title", label: "כותרת חומרים" },
  { key: "materials_body", label: "תיאור חומרים", multiline: true },
  { key: "contact_title", label: "כותרת יצירת קשר" },
  { key: "contact_body", label: "תיאור יצירת קשר", multiline: true },
  { key: "opening_hours", label: "שעות פעילות מוצגות" },
];
export function ContentPanel({ onMessage }: { onMessage: (message: string) => void }) {
  const [content, setContent] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => setContent(await api<Record<string, string>>("/cms/content")), []);
  useEffect(() => { queueMicrotask(() => { void load().catch((error) => onMessage(error instanceof Error ? error.message : "לא ניתן לטעון את תוכן האתר.")); }); }, [load, onMessage]);

  async function saveContent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      const values = Object.fromEntries(fields.map(({ key }) => [key, content[key] ?? ""]));
      setContent(await api<Record<string, string>>("/cms/content", { method: "PATCH", body: JSON.stringify({ values }) }));
      onMessage("תוכן דף הבית עודכן.");
    } catch (error) { onMessage(error instanceof Error ? error.message : "שמירת התוכן נכשלה."); }
    finally { setBusy(false); }
  }

  return <section className={styles.panel}><h2>טקסטים בדף הבית</h2><p>השינויים נשמרים במסד הנתונים ומוצגים באתר הציבורי ברענון הדף.</p>
      <form className={styles.cmsForm} onSubmit={saveContent}>{fields.map((field) => <label className={styles.wide} key={field.key}>{field.label}{field.multiline ? <textarea maxLength={4000} value={content[field.key] ?? ""} onChange={(event) => setContent({ ...content, [field.key]: event.target.value })} /> : <input maxLength={4000} value={content[field.key] ?? ""} onChange={(event) => setContent({ ...content, [field.key]: event.target.value })} />}</label>)}<div className={styles.formActions}><button className={styles.primaryButton} disabled={busy} type="submit">שמירת תוכן</button></div></form>
  </section>;
}
