"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import type { Availability, CustomerPackage, Package, Slot, Treatment } from "./types";
import styles from "./Portal.module.css";

type Props = {
  treatments: Treatment[];
  packages: Package[];
  customerPackages: CustomerPackage[];
  onChanged: () => Promise<void>;
  onMessage: (message: string) => void;
};

const hour = new Intl.DateTimeFormat("he-IL", { timeZone: "Asia/Jerusalem", hour: "2-digit", minute: "2-digit" });
const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jerusalem", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());

export function BookingPanel({ treatments, packages, customerPackages, onChanged, onMessage }: Props) {
  const [treatmentId, setTreatmentId] = useState(0);
  const [date, setDate] = useState("");
  const [beauticianId, setBeauticianId] = useState(0);
  const [userPackageId, setUserPackageId] = useState(0);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0);

  const selected = treatments.find((item) => item.id === treatmentId);
  const eligiblePackages = customerPackages.filter((owned) => {
    const definition = packages.find((item) => item.id === owned.package_id);
    return definition?.treatment_ids.includes(treatmentId) && owned.status === "active" && !owned.expired && owned.remaining_sessions > 0 && (!date || owned.expiration_date >= date);
  });

  useEffect(() => {
    if (!treatmentId || !date) return;
    let cancelled = false;
    const query = new URLSearchParams({ treatment_id: String(treatmentId), date });
    api<Availability>(`/appointments/availability?${query}`, {}, true)
      .then((result) => { if (!cancelled) setSlots(result.slots); })
      .catch((error) => { if (!cancelled) { setSlots([]); onMessage(error instanceof Error ? error.message : "לא ניתן לטעון שעות פנויות."); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [treatmentId, date, reload, onMessage]);

  const beauticians = useMemo(() => [...new Map(slots.map((slot) => [slot.beautician_id, slot.beautician_name])).entries()], [slots]);
  const visibleSlots = slots.filter((slot) => !beauticianId || slot.beautician_id === beauticianId);

  async function book(slot: Slot) {
    setBusy(true);
    try {
      await api("/appointments", { method: "POST", body: JSON.stringify({ treatment_id: treatmentId, beautician_id: slot.beautician_id, start_time: slot.start_time, user_package_id: userPackageId || null }) }, true);
      await onChanged();
      setSlots([]);
      setLoading(true);
      setReload((value) => value + 1);
      onMessage(`התור עם ${slot.beautician_name} בשעה ${hour.format(new Date(slot.start_time))} נקבע בהצלחה.`);
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "לא ניתן לקבוע את התור.");
    } finally { setBusy(false); }
  }

  async function joinWaitlist() {
    setBusy(true);
    try {
      await api("/waitlist", { method: "POST", body: JSON.stringify({ treatment_id: treatmentId, preferred_date: date, beautician_id: beauticianId || null }) }, true);
      await onChanged();
      onMessage("נוספת לרשימת ההמתנה. אם יתפנה תור, הצעה תופיע באזור האישי למשך 15 דקות.");
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "לא ניתן להצטרף לרשימת ההמתנה.");
    } finally { setBusy(false); }
  }

  return (
    <section className={styles.content} aria-labelledby="booking-title">
      <div className={styles.sectionHeading}><span className={styles.eyebrow}>01 / קביעת תור</span><h2 id="booking-title">בוחרות את הרגע המתאים</h2><p>השעות מוצגות בזמן אמת, לפי משך הטיפול, הסמכת המטפלת והמכשיר הפנוי.</p></div>
      <div className={styles.bookingGrid}>
        <div className={styles.card}>
          <div className={styles.form}>
            <label>איזה טיפול תרצי?<select value={treatmentId} onChange={(event) => { setTreatmentId(Number(event.target.value)); setBeauticianId(0); setUserPackageId(0); setSlots([]); setLoading(Boolean(event.target.value && date)); }}><option value={0}>בחרי טיפול</option>{treatments.map((treatment) => <option key={treatment.id} value={treatment.id}>{treatment.name} · {treatment.duration_minutes} דקות</option>)}</select></label>
            <label>באיזה יום?<input type="date" min={today} value={date} onChange={(event) => { setDate(event.target.value); setSlots([]); setLoading(Boolean(treatmentId && event.target.value)); }} /></label>
            {beauticians.length > 1 && <label>מטפלת<select value={beauticianId} onChange={(event) => setBeauticianId(Number(event.target.value))}><option value={0}>כל המטפלות הפנויות</option>{beauticians.map(([id, name]) => <option key={id} value={id}>{name}</option>)}</select></label>}
            {eligiblePackages.length > 0 && <label>שימוש בחבילה קיימת<select value={userPackageId} onChange={(event) => setUserPackageId(Number(event.target.value))}><option value={0}>תור רגיל, ללא חבילה</option>{eligiblePackages.map((owned) => <option key={owned.id} value={owned.id}>{owned.package_name} · {owned.remaining_sessions} טיפולים נותרו</option>)}</select></label>}
            {selected && <p className={styles.hint}>משך הטיפול: {selected.duration_minutes} דקות · מחיר טיפול רגיל: ₪{Number(selected.price).toLocaleString("he-IL")}</p>}
          </div>
        </div>
        <div className={styles.card}>
          <h3>השעות הפנויות</h3>
          {!treatmentId || !date ? <p className={styles.muted}>בחרי טיפול ותאריך כדי לראות שעות.</p> : loading ? <p className={styles.muted}>בודקים זמינות...</p> : visibleSlots.length ? <div className={styles.slotGrid}>{visibleSlots.map((slot) => <button type="button" disabled={busy} className={styles.slot} key={`${slot.beautician_id}-${slot.start_time}`} onClick={() => void book(slot)}><strong>{hour.format(new Date(slot.start_time))}</strong><span>{slot.beautician_name}</span></button>)}</div> : <p className={styles.muted}>אין שעות פנויות ליום הזה.</p>}
          {treatmentId > 0 && date && <div className={styles.waitlistBox}><p>לא מצאת שעה מתאימה? אפשר להצטרף לרשימת ההמתנה ליום שבחרת.</p><button className={styles.secondaryButton} disabled={busy} type="button" onClick={() => void joinWaitlist()}>הצטרפות לרשימת המתנה</button></div>}
        </div>
      </div>
    </section>
  );
}
