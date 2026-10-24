"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { Customer } from "./types";
import styles from "@/app/page.module.css";

export function CustomersPanel({ onMessage }: { onMessage: (message: string) => void }) {
  const [people, setPeople] = useState<Customer[]>([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Customer | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (query: string) => {
    setPeople(await api<Customer[]>(`/staff/customers?search=${encodeURIComponent(query)}`));
  }, []);
  useEffect(() => {
    queueMicrotask(() => { void load("").catch((error) => onMessage(error instanceof Error ? error.message : "לא ניתן לטעון לקוחות.")); });
  }, [load, onMessage]);

  async function find(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try { await load(search); }
    catch (error) { onMessage(error instanceof Error ? error.message : "החיפוש נכשל."); }
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    setBusy(true);
    try {
      await api(`/staff/customers/${selected.id}`, { method: "PATCH", body: JSON.stringify({
        first_name: selected.first_name, last_name: selected.last_name,
        email: selected.email, phone: selected.phone, active: selected.active,
      }) });
      setSelected(null);
      await load(search);
      onMessage("פרטי הלקוחה נשמרו. שינוי סטטוס אינו מבטל תורים קיימים.");
    } catch (error) { onMessage(error instanceof Error ? error.message : "שמירת הלקוחה נכשלה."); }
    finally { setBusy(false); }
  }

  return <div className={styles.cmsGrid}>
    <section className={styles.panel}>
      <h2>לקוחות רשומות</h2>
      <p>מוצגות עד 100 תוצאות אחרונות. חפשי בשם, בטלפון או באימייל כדי לאתר לקוחה אחרת.</p>
      <form className={styles.filters} onSubmit={find}><label>חיפוש<input value={search} onChange={(event) => setSearch(event.target.value)} /></label><button type="submit" className={styles.secondaryButton}>חיפוש</button></form>
      <div className={styles.cmsList}>{people.map((person) => <article className={styles.cmsItem} key={person.id}>
        <div><strong>{person.first_name} {person.last_name}</strong><span>{person.email} · {person.phone}{person.active ? "" : " · מושבתת"}</span></div>
        <div className={styles.actions}><button type="button" onClick={() => setSelected({ ...person })}>עריכה</button></div>
      </article>)}</div>
    </section>
    <section className={styles.panel}>
      <h2>{selected ? `עריכת ${selected.first_name} ${selected.last_name}` : "בחרי לקוחה לעריכה"}</h2>
      <p>ממשק זה מיועד לעדכון פרטי הקשר והמצב הפעיל; לקוחה נרשמת בעצמה באתר. אין הצגה של סיסמה.</p>
      {selected && <form className={styles.cmsForm} onSubmit={save}>
        <label>שם פרטי<input required minLength={2} value={selected.first_name} onChange={(event) => setSelected({ ...selected, first_name: event.target.value })} /></label>
        <label>שם משפחה<input required minLength={2} value={selected.last_name} onChange={(event) => setSelected({ ...selected, last_name: event.target.value })} /></label>
        <label>אימייל<input required type="email" value={selected.email} onChange={(event) => setSelected({ ...selected, email: event.target.value })} /></label>
        <label>טלפון<input required type="tel" minLength={7} value={selected.phone} onChange={(event) => setSelected({ ...selected, phone: event.target.value })} /></label>
        <label className={styles.checkLabel}><input type="checkbox" checked={selected.active} onChange={(event) => setSelected({ ...selected, active: event.target.checked })} />חשבון פעיל</label>
        <div className={styles.formActions}><button className={styles.primaryButton} disabled={busy} type="submit">שמירה</button><button className={styles.secondaryButton} type="button" onClick={() => setSelected(null)}>ביטול</button></div>
      </form>}
    </section>
  </div>;
}
