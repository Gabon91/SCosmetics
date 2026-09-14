import type { Appointment, CustomerPackage, Order, Treatment, User, WaitlistEntry } from "./types";
import styles from "./Portal.module.css";

type Props = {
  user: User;
  appointments: Appointment[];
  customerPackages: CustomerPackage[];
  orders: Order[];
  waitlist: WaitlistEntry[];
  treatments: Treatment[];
  busy: boolean;
  onCancel: (appointmentId: number) => Promise<void>;
  onAccept: (entry: WaitlistEntry) => Promise<void>;
  onLogout: () => void;
};

const dateTime = new Intl.DateTimeFormat("he-IL", { timeZone: "Asia/Jerusalem", dateStyle: "medium", timeStyle: "short" });
const dateOnly = new Intl.DateTimeFormat("he-IL", { timeZone: "Asia/Jerusalem", dateStyle: "medium" });

function titleFor(treatments: Treatment[], id: number) {
  return treatments.find((item) => item.id === id)?.name ?? `טיפול #${id}`;
}

export function AccountPanel({ user, appointments, customerPackages, orders, waitlist, treatments, busy, onCancel, onAccept, onLogout }: Props) {
  return (
    <section className={styles.content} aria-labelledby="account-title">
      <div className={styles.sectionHeading}><span className={styles.eyebrow}>03 / האזור האישי</span><h2 id="account-title">שלום, {user.first_name}</h2><p>התורים, החבילות וההזמנות שלך במקום אחד.</p><button className={styles.textButton} type="button" onClick={onLogout}>התנתקות</button></div>
      <div className={styles.accountGrid}>
        <section className={styles.card} aria-labelledby="appointments-title">
          <h3 id="appointments-title">התורים שלי</h3>
          {!appointments.length && <p className={styles.muted}>עדיין לא קבעת תור.</p>}
          {appointments.map((item) => <article className={styles.listItem} key={item.id}><div><strong>{titleFor(treatments, item.treatment_id)}</strong><span>{dateTime.format(new Date(item.start_time))} · {item.status === "booked" ? "נקבע" : item.status === "completed" ? "הושלם" : "בוטל"}{item.user_package_id ? " · מתוך חבילה" : ""}</span></div>{item.status === "booked" && new Date(item.start_time) > new Date() && <button className={styles.textButton} type="button" disabled={busy} onClick={() => void onCancel(item.id)}>ביטול תור</button>}</article>)}
        </section>
        <section className={styles.card} aria-labelledby="owned-title">
          <h3 id="owned-title">החבילות שלי</h3>
          {!customerPackages.length && <p className={styles.muted}>אין לך חבילות פעילות עדיין.</p>}
          {customerPackages.map((item) => <article className={styles.listItem} key={item.id}><div><strong>{item.package_name}</strong><span>{item.remaining_sessions} מתוך {item.total_sessions} טיפולים נותרו · בתוקף עד {dateOnly.format(new Date(`${item.expiration_date}T12:00:00Z`))}{item.expired ? " · פג תוקף" : ""}</span></div></article>)}
          <p className={styles.hint}>יתרת החבילה מתעדכנת רק כשהמטפלת מסמנת שהטיפול הסתיים, ולא ברגע קביעת התור.</p>
        </section>
        <section className={styles.card} aria-labelledby="waitlist-title">
          <h3 id="waitlist-title">רשימת המתנה</h3>
          {!waitlist.length && <p className={styles.muted}>אין בקשות המתנה כרגע.</p>}
          {waitlist.map((item) => <article className={styles.listItem} key={item.id}><div><strong>{titleFor(treatments, item.treatment_id)}</strong><span>{dateOnly.format(new Date(`${item.preferred_date}T12:00:00Z`))} · {item.status === "waiting" ? "ממתינה לתור שיתפנה" : item.status === "offered" && !item.offer_expired ? "התפנה עבורך מקום!" : item.status === "fulfilled" ? "נקבע תור" : "ההצעה הסתיימה"}</span>{item.status === "offered" && !item.offer_expired && item.offered_start_time && <span>בשעה {dateTime.format(new Date(item.offered_start_time))} · עד {item.offer_expires_at && dateTime.format(new Date(item.offer_expires_at))}</span>}</div>{item.status === "offered" && !item.offer_expired && item.offered_start_time && <button className={styles.secondaryButton} type="button" disabled={busy} onClick={() => void onAccept(item)}>קביעת התור</button>}</article>)}
        </section>
        <section className={styles.card} aria-labelledby="orders-title">
          <h3 id="orders-title">הזמנות חבילה</h3>
          {!orders.length && <p className={styles.muted}>עדיין אין הזמנות.</p>}
          {orders.map((item) => <article className={styles.listItem} key={item.id}><div><strong>הזמנה #{item.id}</strong><span>{item.items.map((part) => part.package_name).join(", ")} · ₪{Number(item.total).toLocaleString("he-IL")}</span><span>{dateTime.format(new Date(item.created_at))} · הדגמה ללא חיוב</span></div></article>)}
        </section>
      </div>
    </section>
  );
}
