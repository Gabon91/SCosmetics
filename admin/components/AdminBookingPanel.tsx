"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { Customer, Package, StaffAppointment, Treatment } from "./types";
import styles from "@/app/page.module.css";

type Slot = { beautician_id: number; beautician_name: string; start_time: string; end_time: string };
type Availability = { slots: Slot[]; duration_minutes: number };
type OwnedPackage = {
  id: number; package_id: number; package_name: string; remaining_sessions: number;
  expiration_date: string; status: "active" | "exhausted"; expired: boolean;
};

const localDate = (value: string) => new Intl.DateTimeFormat("en-CA", {
  timeZone: "Asia/Jerusalem", year: "numeric", month: "2-digit", day: "2-digit",
}).format(new Date(value));
const localTime = new Intl.DateTimeFormat("he-IL", {
  timeZone: "Asia/Jerusalem", hour: "2-digit", minute: "2-digit",
});

export function AdminBookingPanel({ appointment, initialDay, onClose, onSaved, onMessage }: {
  appointment: StaffAppointment | null;
  initialDay: string;
  onClose: () => void;
  onSaved: (date: string) => Promise<void>;
  onMessage: (message: string) => void;
}) {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [catalog, setCatalog] = useState<Treatment[]>([]);
  const [packages, setPackages] = useState<Package[]>([]);
  const [owned, setOwned] = useState<OwnedPackage[]>([]);
  const [search, setSearch] = useState("");
  const [customerId, setCustomerId] = useState(appointment?.customer_id ?? 0);
  const [treatmentId, setTreatmentId] = useState(appointment?.treatment_id ?? 0);
  const [packageId, setPackageId] = useState(0);
  const [date, setDate] = useState(appointment ? localDate(appointment.start_time) : initialDay);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [busy, setBusy] = useState(false);

  const loadCustomers = useCallback(async (query: string) => {
    setCustomers(await api<Customer[]>(`/staff/customers?search=${encodeURIComponent(query)}`));
  }, []);
  useEffect(() => {
    queueMicrotask(() => {
      void Promise.all([api<Treatment[]>("/cms/treatments"), api<Package[]>("/cms/packages")])
        .then(([treatments, offers]) => { setCatalog(treatments); setPackages(offers); })
        .catch((error) => onMessage(error instanceof Error ? error.message : "לא ניתן לטעון קטלוג טיפולים."));
      if (!appointment) void loadCustomers("").catch((error) => onMessage(error instanceof Error ? error.message : "לא ניתן לטעון לקוחות."));
    });
  }, [appointment, loadCustomers, onMessage]);

  useEffect(() => {
    if (!customerId || appointment) return;
    let cancelled = false;
    api<OwnedPackage[]>(`/staff/customers/${customerId}/packages`)
      .then((items) => { if (!cancelled) setOwned(items); })
      .catch((error) => { if (!cancelled) onMessage(error instanceof Error ? error.message : "לא ניתן לטעון חבילות לקוחה."); });
    return () => { cancelled = true; };
  }, [appointment, customerId, onMessage]);

  async function findCustomer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try { await loadCustomers(search); }
    catch (error) { onMessage(error instanceof Error ? error.message : "חיפוש הלקוחה נכשל."); }
  }

  async function checkSlots() {
    if (!customerId || !treatmentId || !date) {
      onMessage("בחרי לקוחה, טיפול ותאריך כדי לבדוק שעות.");
      return;
    }
    setBusy(true);
    setSlots([]);
    try {
      const params = new URLSearchParams({
        customer_id: String(customerId), treatment_id: String(treatmentId), date,
      });
      if (appointment) params.set("appointment_id", String(appointment.id));
      const result = await api<Availability>(`/staff/booking-availability?${params}`);
      setSlots(result.slots);
      if (result.slots.length === 0) onMessage("אין שעות פנויות ביום שבחרת.");
      else onMessage(`נמצאו ${result.slots.length} שעות פנויות. בחרי שעה לשמירה.`);
    } catch (error) { onMessage(error instanceof Error ? error.message : "בדיקת הזמינות נכשלה."); }
    finally { setBusy(false); }
  }

  async function save(slot: Slot) {
    const action = appointment ? "שינוי מועד" : "קביעת תור";
    if (!window.confirm(`${action} עם ${slot.beautician_name} בשעה ${localTime.format(new Date(slot.start_time))}?`)) return;
    setBusy(true);
    try {
      if (appointment) {
        await api(`/staff/appointments/${appointment.id}/reschedule`, {
          method: "PATCH", body: JSON.stringify({ beautician_id: slot.beautician_id, start_time: slot.start_time }),
        });
      } else {
        await api("/staff/appointments", {
          method: "POST", body: JSON.stringify({
            customer_id: customerId, treatment_id: treatmentId, beautician_id: slot.beautician_id,
            start_time: slot.start_time, user_package_id: packageId || null,
          }),
        });
      }
      await onSaved(date);
      onMessage(appointment ? "מועד התור עודכן. מזהה התור והחבילה נשמרו." : "התור נקבע ללקוחה בהצלחה.");
      onClose();
    } catch (error) { onMessage(error instanceof Error ? error.message : "שמירת התור נכשלה; בדקי שהשעה עדיין פנויה."); }
    finally { setBusy(false); }
  }

  const eligible = owned.filter((item) => {
    const definition = packages.find((offer) => offer.id === item.package_id);
    return definition?.treatment_ids.includes(treatmentId)
      && item.status === "active" && item.remaining_sessions > 0
      && !item.expired && item.expiration_date >= date;
  });
  const selectedTreatment = catalog.find((item) => item.id === treatmentId);

  return <section className={styles.panel} aria-label={appointment ? "שינוי מועד תור" : "יצירת תור בשם לקוחה"}>
    <div className={styles.panelHeader}><h2>{appointment ? `שינוי מועד לתור #${appointment.id}` : "תור חדש בשם לקוחה"}</h2><button type="button" onClick={onClose}>סגירה ✕</button></div>
    <p>{appointment ? `התור של ${appointment.customer_name} עבור ${appointment.treatment_name}. הטיפול והחבילה המשויכת נשמרים; אפשר לבחור מטפלת ושעה אחרות.` : "בחרי לקוחה קיימת, טיפול ותאריך. רשימת השעות מבוססת על המשמרות, ההסמכות והתורים שכבר נקבעו."}</p>
    {!appointment && <form className={styles.filters} onSubmit={findCustomer}><label>חיפוש לקוחה<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="שם, טלפון או אימייל" /></label><button type="submit" className={styles.secondaryButton}>חיפוש</button></form>}
    <div className={styles.cmsForm}>
      {appointment ? <p className={styles.wide}><strong>לקוחה:</strong> {appointment.customer_name}</p> : <label>לקוחה<select required value={customerId} onChange={(event) => { setCustomerId(Number(event.target.value)); setPackageId(0); setSlots([]); }}><option value={0}>בחרי לקוחה</option>{customers.filter((item) => item.active).map((item) => <option key={item.id} value={item.id}>{item.first_name} {item.last_name} · {item.phone}</option>)}</select></label>}
      {appointment ? <p><strong>טיפול:</strong> {appointment.treatment_name}</p> : <label>טיפול<select required value={treatmentId} onChange={(event) => { setTreatmentId(Number(event.target.value)); setPackageId(0); setSlots([]); }}><option value={0}>בחרי טיפול</option>{catalog.filter((item) => item.active).map((item) => <option key={item.id} value={item.id}>{item.name} · {item.duration_minutes} דקות</option>)}</select></label>}
      <label>תאריך<input required type="date" min={localDate(new Date().toISOString())} value={date} onChange={(event) => { setDate(event.target.value); setPackageId(0); setSlots([]); }} /></label>
      {!appointment && eligible.length > 0 && <label>חבילה קיימת<select value={packageId} onChange={(event) => setPackageId(Number(event.target.value))}><option value={0}>ללא חבילה</option>{eligible.map((item) => <option key={item.id} value={item.id}>{item.package_name} · {item.remaining_sessions} טיפולים נותרו</option>)}</select></label>}
      {selectedTreatment && <p className={styles.wide}>משך הטיפול: {selectedTreatment.duration_minutes} דקות. כל שעה מוצעת בהתאם למשך הזה.</p>}
      <div className={styles.formActions}><button type="button" className={styles.primaryButton} disabled={busy || !customerId || !treatmentId || !date} onClick={() => void checkSlots()}>{busy ? "בודקים..." : "בדיקת שעות פנויות"}</button></div>
    </div>
    {slots.length > 0 && <div className={styles.bookingSlots} aria-label="שעות פנויות">{slots.map((slot) => <button key={`${slot.beautician_id}-${slot.start_time}`} type="button" disabled={busy} className={styles.bookingSlot} onClick={() => void save(slot)}><strong>{localTime.format(new Date(slot.start_time))}</strong><span>{slot.beautician_name}</span></button>)}</div>}
  </section>;
}
