import type { StaffAppointment } from "./types";
import styles from "@/app/page.module.css";

const time = new Intl.DateTimeFormat("he-IL", { timeZone: "Asia/Jerusalem", hour: "2-digit", minute: "2-digit" });
const statusLabels: Record<StaffAppointment["status"], string> = {
  booked: "נקבע", completed: "הושלם", cancelled: "בוטל", no_show: "לא הגיעה",
};

export function AppointmentList({ items, busy, admin = false, onUpdate, onReschedule }: { items: StaffAppointment[]; busy: boolean; admin?: boolean; onUpdate: (id: number, action: "complete" | "no-show" | "cancel") => Promise<void>; onReschedule?: (item: StaffAppointment) => void }) {
  if (!items.length) return <p className={styles.empty}>אין תורים להצגה.</p>;
  return <div className={styles.appointmentList}>{items.map((item) => <article className={styles.appointment} key={item.id}>
    <time>{time.format(new Date(item.start_time))}</time>
    <div><strong>{item.customer_name}</strong><span>{item.treatment_name} · {item.beautician_name}{item.uses_package ? " · חבילה" : ""}</span><small>{item.customer_phone}</small></div>
    <span className={styles.status}>{statusLabels[item.status]}</span>
    {item.status === "booked" && <div className={styles.actions}><button disabled={busy} type="button" onClick={() => void onUpdate(item.id, "complete")}>הושלם</button><button disabled={busy} type="button" onClick={() => void onUpdate(item.id, "no-show")}>לא הגיעה</button>{admin && onReschedule && <button disabled={busy || new Date(item.start_time) <= new Date()} type="button" onClick={() => onReschedule(item)}>שינוי מועד</button>}{admin && <button disabled={busy || new Date(item.start_time) <= new Date()} type="button" onClick={() => void onUpdate(item.id, "cancel")}>ביטול תור</button>}</div>}
  </article>)}</div>;
}
