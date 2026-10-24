"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { BookableBeautician, Treatment, WorkingHours } from "./types";
import styles from "@/app/page.module.css";

type StaffForm = Omit<BookableBeautician, "id" | "user_id"> & { password: string };
const blank: StaffForm = {
  first_name: "", last_name: "", email: "", phone: "", password: "", bio: "",
  treatment_ids: [], working_hours: [], active: true,
};
const weekdays = ["יום שני", "יום שלישי", "יום רביעי", "יום חמישי", "יום שישי", "יום שבת", "יום ראשון"];

export function StaffPanel({ onMessage, onChanged }: { onMessage: (message: string) => void; onChanged: () => void }) {
  const [people, setPeople] = useState<BookableBeautician[]>([]);
  const [treatments, setTreatments] = useState<Treatment[]>([]);
  const [form, setForm] = useState<StaffForm>(blank);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [staff, catalog] = await Promise.all([
      api<BookableBeautician[]>("/cms/beauticians"), api<Treatment[]>("/cms/treatments"),
    ]);
    setPeople(staff);
    setTreatments(catalog);
  }, []);
  useEffect(() => {
    queueMicrotask(() => { void load().catch((error) => onMessage(error instanceof Error ? error.message : "לא ניתן לטעון מטפלות.")); });
  }, [load, onMessage]);

  function edit(person: BookableBeautician) {
    setEditingId(person.id);
    setForm({
      first_name: person.first_name, last_name: person.last_name, email: person.email,
      phone: person.phone, password: "", bio: person.bio, treatment_ids: [...person.treatment_ids],
      working_hours: person.working_hours.map((shift) => ({ ...shift })), active: person.active,
    });
  }

  function changeShift(index: number, patch: Partial<WorkingHours>) {
    setForm((current) => ({ ...current, working_hours: current.working_hours.map((shift, i) => i === index ? { ...shift, ...patch } : shift) }));
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      const payload = editingId ? { ...form, password: undefined } : form;
      await api(editingId ? `/cms/beauticians/${editingId}` : "/cms/beauticians", {
        method: editingId ? "PATCH" : "POST", body: JSON.stringify(payload),
      });
      setEditingId(null);
      setForm(blank);
      await load();
      onChanged();
      onMessage("פרטי המטפלת, ההסמכות והשעות נשמרו.");
    } catch (error) { onMessage(error instanceof Error ? error.message : "שמירת המטפלת נכשלה."); }
    finally { setBusy(false); }
  }

  async function toggle(person: BookableBeautician) {
    if (person.active && !window.confirm(`להשבית את ״${person.first_name} ${person.last_name}״? לא יוצעו לה תורים חדשים והכניסה שלה למערכת תיחסם. תורים קיימים לא יבוטלו אוטומטית.`)) return;
    setBusy(true);
    try {
      await api(`/cms/beauticians/${person.id}`, { method: "PATCH", body: JSON.stringify({ active: !person.active }) });
      await load();
      onChanged();
      onMessage(person.active ? "המטפלת הושבתה. בדקי בנפרד תורים עתידיים קיימים." : "המטפלת הופעלה מחדש.");
    } catch (error) { onMessage(error instanceof Error ? error.message : "העדכון נכשל."); }
    finally { setBusy(false); }
  }

  return <div className={styles.cmsGrid}>
    <section className={styles.panel}>
      <h2>מטפלות לקביעת תורים</h2>
      <p>חשבונות אלה קובעים את זמינות התורים בפועל. כרטיסי ״צוות האתר״ הם תוכן שיווקי נפרד.</p>
      {people.length === 0 && <p className={styles.empty}>אין מטפלות בחשבון.</p>}
      <div className={styles.cmsList}>{people.map((person) => <article className={styles.cmsItem} key={person.id}>
        <div><strong>{person.first_name} {person.last_name}</strong><span>{person.email} · {person.treatment_ids.length} הסמכות · {person.working_hours.length} משמרות{person.active ? "" : " · מושבתת"}</span></div>
        <div className={styles.actions}>
          <button type="button" disabled={busy} onClick={() => edit(person)}>עריכה</button>
          <button type="button" disabled={busy} onClick={() => void toggle(person)}>{person.active ? "השבתה" : "הפעלה"}</button>
        </div>
      </article>)}</div>
    </section>
    <section className={styles.panel}>
      <h2>{editingId ? "עריכת מטפלת" : "הוספת מטפלת"}</h2>
      <p>אפשר לבחור כמה טיפולים ומשמרות. שעות ומועדים נשמרים לפי אזור הזמן של העסק. שינוי שעות אינו מבטל תורים קיימים.</p>
      <form className={styles.cmsForm} onSubmit={save}>
        <label>שם פרטי<input required maxLength={80} value={form.first_name} onChange={(event) => setForm({ ...form, first_name: event.target.value })} /></label>
        <label>שם משפחה<input required maxLength={80} value={form.last_name} onChange={(event) => setForm({ ...form, last_name: event.target.value })} /></label>
        <label>אימייל לכניסה<input required type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label>
        <label>טלפון<input required type="tel" minLength={5} value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} /></label>
        {!editingId && <label className={styles.wide}>סיסמה זמנית — לפחות 8 תווים<input required type="password" minLength={8} autoComplete="new-password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} /></label>}
        <label className={styles.wide}>ביוגרפיה<textarea maxLength={4000} value={form.bio} onChange={(event) => setForm({ ...form, bio: event.target.value })} /></label>
        <fieldset className={styles.wide}><legend>הסמכות לטיפולים</legend>{treatments.filter((item) => item.active || form.treatment_ids.includes(item.id)).map((item) => <label className={styles.checkLabel} key={item.id}><input type="checkbox" checked={form.treatment_ids.includes(item.id)} onChange={(event) => setForm({ ...form, treatment_ids: event.target.checked ? [...form.treatment_ids, item.id] : form.treatment_ids.filter((id) => id !== item.id) })} />{item.name}{item.active ? "" : " (בארכיון)"}</label>)}</fieldset>
        <fieldset className={styles.wide}><legend>שעות עבודה שבועיות</legend>
          {form.working_hours.map((shift, index) => <div className={styles.shiftRow} key={index}>
            <label>יום<select value={shift.weekday} onChange={(event) => changeShift(index, { weekday: Number(event.target.value) })}>{weekdays.map((name, day) => <option key={day} value={day}>{name}</option>)}</select></label>
            <label>התחלה<input required type="time" value={shift.start_time.slice(0, 5)} onChange={(event) => changeShift(index, { start_time: event.target.value })} /></label>
            <label>סיום<input required type="time" value={shift.end_time.slice(0, 5)} onChange={(event) => changeShift(index, { end_time: event.target.value })} /></label>
            <button type="button" className={styles.secondaryButton} onClick={() => setForm({ ...form, working_hours: form.working_hours.filter((_, i) => i !== index) })}>הסרה</button>
          </div>)}
          <button type="button" className={styles.secondaryButton} onClick={() => setForm({ ...form, working_hours: [...form.working_hours, { weekday: 0, start_time: "09:00", end_time: "17:00" }] })}>הוספת משמרת</button>
        </fieldset>
        <div className={styles.formActions}><button className={styles.primaryButton} disabled={busy} type="submit">{editingId ? "שמירת שינויים" : "יצירת חשבון"}</button>{editingId && <button className={styles.secondaryButton} type="button" onClick={() => { setEditingId(null); setForm(blank); }}>ביטול עריכה</button>}</div>
      </form>
    </section>
  </div>;
}
