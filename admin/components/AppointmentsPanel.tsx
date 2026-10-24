"use client";

import { useState } from "react";
import { AdminBookingPanel } from "./AdminBookingPanel";
import { AppointmentList } from "./AppointmentList";
import type { Beautician, StaffAppointment } from "./types";
import styles from "@/app/page.module.css";

export function AppointmentsPanel({ items, beauticians, admin, day, busy, onDayChange, onUpdate, onBookingSaved, onMessage }: { items: StaffAppointment[]; beauticians: Beautician[]; admin: boolean; day: string; busy: boolean; onDayChange: (day: string) => Promise<void>; onUpdate: (id: number, action: "complete" | "no-show" | "cancel") => Promise<void>; onBookingSaved: (date: string) => Promise<void>; onMessage: (message: string) => void }) {
  const [beauticianId, setBeauticianId] = useState(0);
  const [status, setStatus] = useState("");
  const [editor, setEditor] = useState<{ key: string; appointment: StaffAppointment | null } | null>(null);
  const visible = items.filter((item) => (!beauticianId || item.beautician_id === beauticianId) && (!status || item.status === status));
  return <>
    {admin && editor && <AdminBookingPanel key={editor.key} appointment={editor.appointment} initialDay={day} onClose={() => setEditor(null)} onSaved={onBookingSaved} onMessage={onMessage} />}
    <section className={styles.panel}>
    <div className={styles.panelHeader}><h2>יומן ליום שנבחר</h2><span>{visible.length} תורים</span>{admin && <button type="button" className={styles.primaryButton} onClick={() => setEditor({ key: `create-${Date.now()}`, appointment: null })}>תור חדש ללקוחה</button>}</div>
    <div className={styles.filters}>
      <label>תאריך<input type="date" value={day} onChange={(event) => void onDayChange(event.target.value)} /></label>
      {admin && <label>מטפלת<select value={beauticianId} onChange={(event) => setBeauticianId(Number(event.target.value))}><option value={0}>כל המטפלות</option>{beauticians.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select></label>}
      <label>סטטוס<select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">הכול</option><option value="booked">נקבע</option><option value="completed">הושלם</option><option value="no_show">לא הגיעה</option><option value="cancelled">בוטל</option></select></label>
    </div>
    <AppointmentList items={visible} busy={busy} admin={admin} onUpdate={onUpdate} onReschedule={admin ? (item) => setEditor({ key: `move-${item.id}`, appointment: item }) : undefined} />
    </section>
  </>;
}
