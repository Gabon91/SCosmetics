import { AppointmentList } from "./AppointmentList";
import type { Dashboard } from "./types";
import styles from "@/app/page.module.css";

export function DashboardPanel({ data, admin, busy, onUpdate, onShowCalendar }: { data: Dashboard; admin: boolean; busy: boolean; onUpdate: (id: number, action: "complete" | "no-show" | "cancel") => Promise<void>; onShowCalendar: () => void }) {
  return <>
    <div className={styles.kpiGrid}>
      <article className={styles.kpiCard}><span>תורים היום</span><strong>{data.appointments_today}</strong></article>
      <article className={styles.kpiCard}><span>טיפולים שהושלמו</span><strong>{data.completed_today}</strong></article>
      <article className={styles.kpiCard}><span>תורים שנקבעו</span><strong>{data.upcoming_today}</strong></article>
      {admin && <article className={styles.kpiCard}><span>לקוחות פעילות</span><strong>{data.active_customers}</strong></article>}
    </div>
    {admin && <p className={styles.summary}>הזמנות הדגמה החודש: {data.demo_orders_month} · סך הזמנות הדגמה: ₪{Number(data.demo_sales_month).toLocaleString("he-IL")} (ללא סליקה אמיתית)</p>}
    <section className={styles.panel}><div className={styles.panelHeader}><h2>התורים של היום</h2><button type="button" onClick={onShowCalendar}>לכל היומן ←</button></div><AppointmentList items={data.appointments} busy={busy} admin={admin} onUpdate={onUpdate} /></section>
  </>;
}
