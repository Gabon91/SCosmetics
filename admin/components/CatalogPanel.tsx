"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { Package, Treatment } from "./types";
import styles from "@/app/page.module.css";

type TreatmentForm = Omit<Treatment, "id">;
type PackageForm = Omit<Package, "id">;
const blankTreatment: TreatmentForm = { name: "", category: "", description: "", duration_minutes: 60, price: 0, accent: "light-pink", active: true };
const blankPackage: PackageForm = { name: "", price: 0, sessions: 5, validity_days: 180, treatment_ids: [], active: true };

export function CatalogPanel({ onMessage }: { onMessage: (message: string) => void }) {
  const [treatments, setTreatments] = useState<Treatment[]>([]);
  const [packages, setPackages] = useState<Package[]>([]);
  const [treatmentForm, setTreatmentForm] = useState<TreatmentForm>(blankTreatment);
  const [packageForm, setPackageForm] = useState<PackageForm>(blankPackage);
  const [editingTreatment, setEditingTreatment] = useState<number | null>(null);
  const [editingPackage, setEditingPackage] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const [catalog, offers] = await Promise.all([
      api<Treatment[]>("/cms/treatments"), api<Package[]>("/cms/packages"),
    ]);
    setTreatments(catalog);
    setPackages(offers);
  }, []);

  useEffect(() => { queueMicrotask(() => { void load().catch((error) => onMessage(error instanceof Error ? error.message : "לא ניתן לטעון את הקטלוג.")); }); }, [load, onMessage]);

  async function saveTreatment(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      await api(editingTreatment ? `/cms/treatments/${editingTreatment}` : "/cms/treatments", {
        method: editingTreatment ? "PATCH" : "POST", body: JSON.stringify(treatmentForm),
      });
      setTreatmentForm(blankTreatment);
      setEditingTreatment(null);
      await load();
      onMessage("פרטי הטיפול נשמרו והקטלוג הציבורי עודכן.");
    } catch (error) { onMessage(error instanceof Error ? error.message : "שמירת הטיפול נכשלה."); }
    finally { setBusy(false); }
  }

  async function savePackage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      await api(editingPackage ? `/cms/packages/${editingPackage}` : "/cms/packages", {
        method: editingPackage ? "PATCH" : "POST", body: JSON.stringify(packageForm),
      });
      setPackageForm(blankPackage);
      setEditingPackage(null);
      await load();
      onMessage("החבילה נשמרה.");
    } catch (error) { onMessage(error instanceof Error ? error.message : "שמירת החבילה נכשלה."); }
    finally { setBusy(false); }
  }

  async function toggleTreatment(item: Treatment) {
    if (item.active && !window.confirm(`להעביר את הטיפול ״${item.name}״ לארכיון? תורים קיימים לא יימחקו.`)) return;
    setBusy(true);
    try {
      await api(`/cms/treatments/${item.id}`, { method: "PATCH", body: JSON.stringify({ active: !item.active }) });
      await load();
      onMessage(item.active ? "הטיפול הוסר מהקטלוג הפעיל." : "הטיפול הוחזר לקטלוג.");
    } catch (error) { onMessage(error instanceof Error ? error.message : "העדכון נכשל."); }
    finally { setBusy(false); }
  }

  async function togglePackage(item: Package) {
    if (item.active && !window.confirm(`להעביר את החבילה ״${item.name}״ לארכיון? חבילות שכבר נרכשו יישארו.`)) return;
    setBusy(true);
    try {
      await api(`/cms/packages/${item.id}`, { method: "PATCH", body: JSON.stringify({ active: !item.active }) });
      await load();
      onMessage(item.active ? "החבילה הוסרה מהחנות." : "החבילה הוחזרה לחנות.");
    } catch (error) { onMessage(error instanceof Error ? error.message : "העדכון נכשל."); }
    finally { setBusy(false); }
  }

  return <div className={styles.cmsGrid}>
    <section className={styles.panel}>
      <h2>טיפולים</h2>
      <p>שינוי משך טיפול משפיע על חישוב הזמינות של תורים חדשים. תורים קיימים שומרים את זמני ההזמנה שלהם.</p>
      <div className={styles.cmsList}>{treatments.map((item) => <article className={styles.cmsItem} key={item.id}>
        <div><strong>{item.name}</strong><span>{item.category} · {item.duration_minutes} דקות · ₪{Number(item.price).toLocaleString("he-IL")}{!item.active ? " · בארכיון" : ""}</span></div>
        <div className={styles.actions}><button type="button" disabled={busy} onClick={() => { setEditingTreatment(item.id); setTreatmentForm({ name: item.name, category: item.category, description: item.description, duration_minutes: item.duration_minutes, price: item.price, accent: item.accent, active: item.active }); }}>עריכה</button><button type="button" disabled={busy} onClick={() => void toggleTreatment(item)}>{item.active ? "ארכיון" : "החזרה"}</button></div>
      </article>)}</div>
      <h3>{editingTreatment ? "עריכת טיפול" : "טיפול חדש"}</h3>
      <form className={styles.cmsForm} onSubmit={saveTreatment}>
        <label>שם הטיפול<input required minLength={2} value={treatmentForm.name} onChange={(event) => setTreatmentForm({ ...treatmentForm, name: event.target.value })} /></label>
        <label>קטגוריה<input required minLength={2} value={treatmentForm.category} onChange={(event) => setTreatmentForm({ ...treatmentForm, category: event.target.value })} /></label>
        <label className={styles.wide}>תיאור<textarea required minLength={2} value={treatmentForm.description} onChange={(event) => setTreatmentForm({ ...treatmentForm, description: event.target.value })} /></label>
        <label>משך בדקות<input required type="number" min={15} step={15} value={treatmentForm.duration_minutes} onChange={(event) => setTreatmentForm({ ...treatmentForm, duration_minutes: Number(event.target.value) })} /></label>
        <label>מחיר בש״ח<input required type="number" min={0} step="0.01" value={treatmentForm.price} onChange={(event) => setTreatmentForm({ ...treatmentForm, price: Number(event.target.value) })} /></label>
        <div className={styles.formActions}><button className={styles.primaryButton} disabled={busy} type="submit">{editingTreatment ? "שמירת שינויים" : "הוספת טיפול"}</button>{editingTreatment && <button className={styles.secondaryButton} type="button" onClick={() => { setEditingTreatment(null); setTreatmentForm(blankTreatment); }}>ביטול עריכה</button>}</div>
      </form>
    </section>

    <section className={styles.panel}>
      <h2>חבילות</h2>
      <p>המחיר ומספר הטיפולים נשמרים בעת רכישת חבילת ההדגמה; שינוי מוצר אינו משנה חבילות שכבר הוקצו ללקוחות.</p>
      <div className={styles.cmsList}>{packages.map((item) => <article className={styles.cmsItem} key={item.id}>
        <div><strong>{item.name}</strong><span>{item.sessions} טיפולים · ₪{Number(item.price).toLocaleString("he-IL")}{!item.active ? " · בארכיון" : ""}</span></div>
        <div className={styles.actions}><button type="button" disabled={busy} onClick={() => { setEditingPackage(item.id); setPackageForm({ name: item.name, price: item.price, sessions: item.sessions, validity_days: item.validity_days, treatment_ids: item.treatment_ids, active: item.active }); }}>עריכה</button><button type="button" disabled={busy} onClick={() => void togglePackage(item)}>{item.active ? "ארכיון" : "החזרה"}</button></div>
      </article>)}</div>
      <h3>{editingPackage ? "עריכת חבילה" : "חבילה חדשה"}</h3>
      <form className={styles.cmsForm} onSubmit={savePackage}>
        <label className={styles.wide}>שם החבילה<input required minLength={2} value={packageForm.name} onChange={(event) => setPackageForm({ ...packageForm, name: event.target.value })} /></label>
        <label>מחיר בש״ח<input required type="number" min={0} step="0.01" value={packageForm.price} onChange={(event) => setPackageForm({ ...packageForm, price: Number(event.target.value) })} /></label>
        <label>מספר טיפולים<input required type="number" min={1} value={packageForm.sessions} onChange={(event) => setPackageForm({ ...packageForm, sessions: Number(event.target.value) })} /></label>
        <label>תוקף בימים<input required type="number" min={1} value={packageForm.validity_days} onChange={(event) => setPackageForm({ ...packageForm, validity_days: Number(event.target.value) })} /></label>
        <fieldset className={styles.wide}><legend>טיפולים בחבילה</legend>{treatments.filter((item) => item.active).map((item) => <label className={styles.checkLabel} key={item.id}><input type="checkbox" checked={packageForm.treatment_ids.includes(item.id)} onChange={(event) => setPackageForm({ ...packageForm, treatment_ids: event.target.checked ? [...packageForm.treatment_ids, item.id] : packageForm.treatment_ids.filter((id) => id !== item.id) })} />{item.name}</label>)}</fieldset>
        <div className={styles.formActions}><button className={styles.primaryButton} disabled={busy || packageForm.treatment_ids.length === 0} type="submit">{editingPackage ? "שמירת שינויים" : "הוספת חבילה"}</button>{editingPackage && <button className={styles.secondaryButton} type="button" onClick={() => { setEditingPackage(null); setPackageForm(blankPackage); }}>ביטול עריכה</button>}</div>
      </form>
    </section>
  </div>;
}
