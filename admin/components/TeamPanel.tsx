"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { TeamMember } from "./types";
import styles from "@/app/page.module.css";

type TeamForm = Omit<TeamMember, "id">;
const blank: TeamForm = {
  name: "", title: "", description: "", image_url: "",
  featured: false, display_order: 0, active: true,
};

export function TeamPanel({ onMessage }: { onMessage: (message: string) => void }) {
  const [people, setPeople] = useState<TeamMember[]>([]);
  const [form, setForm] = useState<TeamForm>(blank);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => setPeople(await api<TeamMember[]>("/cms/team")), []);
  useEffect(() => {
    queueMicrotask(() => { void load().catch((error) => onMessage(error instanceof Error ? error.message : "לא ניתן לטעון את הצוות.")); });
  }, [load, onMessage]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      await api(editingId ? `/cms/team/${editingId}` : "/cms/team", {
        method: editingId ? "PATCH" : "POST", body: JSON.stringify(form),
      });
      setEditingId(null);
      setForm(blank);
      await load();
      onMessage("פרטי המטפלת נשמרו. רענון דף הבית יציג את השינוי.");
    } catch (error) { onMessage(error instanceof Error ? error.message : "שמירת הצוות נכשלה."); }
    finally { setBusy(false); }
  }

  async function toggle(person: TeamMember) {
    if (person.active && !window.confirm(`להעביר את ״${person.name}״ לארכיון?`)) return;
    setBusy(true);
    try {
      await api(`/cms/team/${person.id}`, { method: "PATCH", body: JSON.stringify({ active: !person.active }) });
      await load();
      onMessage("תצוגת המטפלת עודכנה.");
    } catch (error) { onMessage(error instanceof Error ? error.message : "העדכון נכשל."); }
    finally { setBusy(false); }
  }

  return <div className={styles.cmsGrid}>
    <section className={styles.panel}>
      <h2>מטפלות המוצגות באתר</h2>
      <p>כרטיסי הצוות כאן הם תוכן תצוגתי. הרשאות הזמנת תורים ושעות העבודה מנוהלות בנפרד בשרת.</p>
      <div className={styles.cmsList}>{people.map((person) => <article className={styles.cmsItem} key={person.id}>
        <div><strong>{person.name}</strong><span>{person.title}{person.featured ? " · פרופיל ראשי" : ""}{!person.active ? " · בארכיון" : ""}</span></div>
        <div className={styles.actions}>
          <button disabled={busy} onClick={() => { setEditingId(person.id); setForm({ name: person.name, title: person.title, description: person.description, image_url: person.image_url, featured: person.featured, display_order: person.display_order, active: person.active }); }}>עריכה</button>
          <button disabled={busy} onClick={() => void toggle(person)}>{person.active ? "ארכיון" : "החזרה"}</button>
        </div>
      </article>)}</div>
    </section>
    <section className={styles.panel}>
      <h2>{editingId ? "עריכת מטפלת" : "מטפלת חדשה"}</h2>
      <p>נתיב התמונה צריך להצביע לקובץ תחת <code>client/public/images</code>, לדוגמה <code>/images/Sigal_Levi.png</code>.</p>
      <form className={styles.cmsForm} onSubmit={save}>
        <label className={styles.wide}>שם מלא<input required minLength={2} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
        <label className={styles.wide}>כותרת מקצועית<input required minLength={2} value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label>
        <label className={styles.wide}>תיאור<textarea required minLength={2} maxLength={4000} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
        <label className={styles.wide}>נתיב תמונה<input placeholder="/images/name.png" value={form.image_url} onChange={(event) => setForm({ ...form, image_url: event.target.value })} /></label>
        <label>סדר הופעה<input type="number" min={0} value={form.display_order} onChange={(event) => setForm({ ...form, display_order: Number(event.target.value) })} /></label>
        <label className={styles.checkLabel}><input type="checkbox" checked={form.featured} onChange={(event) => setForm({ ...form, featured: event.target.checked })} />פרופיל ראשי (אחד בלבד)</label>
        <div className={styles.formActions}><button className={styles.primaryButton} disabled={busy} type="submit">{editingId ? "שמירת שינויים" : "הוספת מטפלת"}</button>{editingId && <button className={styles.secondaryButton} type="button" onClick={() => { setEditingId(null); setForm(blank); }}>ביטול עריכה</button>}</div>
      </form>
    </section>
  </div>;
}
