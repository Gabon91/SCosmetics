"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { Equipment, Treatment } from "./types";
import styles from "@/app/page.module.css";

type EquipmentForm = Omit<Equipment, "id">;
const blank: EquipmentForm = {
  name: "", manufacturer: "", description: "", image_url: "",
  treatment_ids: [], active: true,
};

export function EquipmentPanel({ onMessage }: { onMessage: (message: string) => void }) {
  const [equipment, setEquipment] = useState<Equipment[]>([]);
  const [treatments, setTreatments] = useState<Treatment[]>([]);
  const [form, setForm] = useState<EquipmentForm>(blank);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [machines, catalog] = await Promise.all([
      api<Equipment[]>("/cms/equipment"),
      api<Treatment[]>("/cms/treatments"),
    ]);
    setEquipment(machines);
    setTreatments(catalog);
  }, []);
  useEffect(() => {
    queueMicrotask(() => { void load().catch((error) => onMessage(error instanceof Error ? error.message : "לא ניתן לטעון את רשימת הציוד.")); });
  }, [load, onMessage]);

  function edit(item: Equipment) {
    setEditingId(item.id);
    setForm({
      name: item.name, manufacturer: item.manufacturer, description: item.description,
      image_url: item.image_url, treatment_ids: item.treatment_ids, active: item.active,
    });
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      await api(editingId ? `/cms/equipment/${editingId}` : "/cms/equipment", {
        method: editingId ? "PATCH" : "POST", body: JSON.stringify(form),
      });
      setEditingId(null);
      setForm(blank);
      await load();
      onMessage("פרטי הציוד נשמרו. רענון דף הבית יציג את השינוי.");
    } catch (error) { onMessage(error instanceof Error ? error.message : "שמירת הציוד נכשלה."); }
    finally { setBusy(false); }
  }

  async function toggle(item: Equipment) {
    if (item.active && !window.confirm(`להעביר את ״${item.name}״ לארכיון?`)) return;
    setBusy(true);
    try {
      await api(`/cms/equipment/${item.id}`, {
        method: "PATCH", body: JSON.stringify({ active: !item.active }),
      });
      await load();
      onMessage("תצוגת הציוד עודכנה.");
    } catch (error) { onMessage(error instanceof Error ? error.message : "העדכון נכשל."); }
    finally { setBusy(false); }
  }

  return <div className={styles.cmsGrid}>
    <section className={styles.panel}>
      <h2>רשימת הציוד באתר</h2>
      <p>כאן מוסיפים, עורכים ומעבירים ציוד לארכיון. ציוד פעיל מוצג בכרטיסים בעמוד הבית.</p>
      {equipment.length === 0 && <p className={styles.empty}>עדיין לא הוזן ציוד.</p>}
      <div className={styles.cmsList}>{equipment.map((item) => <article className={styles.cmsItem} key={item.id}>
        <div><strong>{item.name}</strong><span>{item.manufacturer || "ללא יצרן מוצג"}{!item.active ? " · בארכיון" : ""}</span></div>
        <div className={styles.actions}>
          <button type="button" disabled={busy} onClick={() => edit(item)}>עריכה</button>
          <button type="button" disabled={busy} onClick={() => void toggle(item)}>{item.active ? "ארכיון" : "החזרה"}</button>
        </div>
      </article>)}</div>
    </section>
    <section className={styles.panel}>
      <h2>{editingId ? "עריכת ציוד" : "ציוד חדש"}</h2>
      <p>נתיב התמונה צריך להצביע לקובץ תחת <code>client/public/images</code>, לדוגמה <code>/images/Hair_Removal_Soprano.png</code>.</p>
      <form className={styles.cmsForm} onSubmit={save}>
        <label className={styles.wide}>שם הציוד<input required minLength={2} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label>
        <label>יצרן<input value={form.manufacturer} onChange={(event) => setForm({ ...form, manufacturer: event.target.value })} /></label>
        <label>נתיב תמונה<input placeholder="/images/device.png" value={form.image_url} onChange={(event) => setForm({ ...form, image_url: event.target.value })} /></label>
        <label className={styles.wide}>תיאור שיופיע בהרחבת הכרטיס<textarea required minLength={2} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label>
        <fieldset className={styles.wide}><legend>טיפולים קשורים</legend>{treatments.filter((item) => item.active).map((item) => <label className={styles.checkLabel} key={item.id}><input type="checkbox" checked={form.treatment_ids.includes(item.id)} onChange={(event) => setForm({ ...form, treatment_ids: event.target.checked ? [...form.treatment_ids, item.id] : form.treatment_ids.filter((id) => id !== item.id) })} />{item.name}</label>)}</fieldset>
        <div className={styles.formActions}>
          <button className={styles.primaryButton} disabled={busy} type="submit">{editingId ? "שמירת שינויים" : "הוספת ציוד"}</button>
          {editingId && <button className={styles.secondaryButton} type="button" onClick={() => { setEditingId(null); setForm(blank); }}>ביטול עריכה</button>}
        </div>
      </form>
    </section>
  </div>;
}
