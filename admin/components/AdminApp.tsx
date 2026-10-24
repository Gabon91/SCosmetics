"use client";

import { useCallback, useEffect, useState } from "react";
import { api, clearTokens, hasTokens, request, saveTokens, type Tokens } from "./api";
import { AppointmentsPanel } from "./AppointmentsPanel";
import { CatalogPanel } from "./CatalogPanel";
import { ContentPanel } from "./ContentPanel";
import { CustomersPanel } from "./CustomersPanel";
import { DashboardPanel } from "./DashboardPanel";
import { EquipmentPanel } from "./EquipmentPanel";
import { LoginPanel } from "./LoginPanel";
import { StaffPanel } from "./StaffPanel";
import { TeamPanel } from "./TeamPanel";
import type { Beautician, Dashboard, StaffAppointment, StaffUser } from "./types";
import styles from "@/app/page.module.css";

type Tab = "dashboard" | "appointments" | "catalog" | "content" | "equipment" | "team" | "staff" | "customers" | "reports";
const today = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jerusalem", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());

export function AdminApp() {
  const [user, setUser] = useState<StaffUser | null>(null);
  const [tab, setTab] = useState<Tab>("dashboard");
  const [day, setDay] = useState(today);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [appointments, setAppointments] = useState<StaffAppointment[]>([]);
  const [beauticians, setBeauticians] = useState<Beautician[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const loadStaffData = useCallback(async (selectedDay: string) => {
    const [overview, calendar, people] = await Promise.all([
      api<Dashboard>("/staff/dashboard"),
      api<StaffAppointment[]>(`/staff/appointments?date=${selectedDay}`),
      api<Beautician[]>("/staff/beauticians"),
    ]);
    setDashboard(overview);
    setAppointments(calendar);
    setBeauticians(people);
  }, []);

  const loadProfile = useCallback(async () => {
    const profile = await api<StaffUser>("/auth/me");
    if (profile.role !== "admin" && profile.role !== "beautician") {
      clearTokens();
      throw new Error("גישה לממשק זה מותרת לצוות הקליניקה בלבד.");
    }
    setUser(profile);
  }, []);

  useEffect(() => {
    if (hasTokens()) queueMicrotask(() => {
      loadProfile().then(() => loadStaffData(today)).catch((error) => {
        clearTokens();
        setUser(null);
        setMessage(error instanceof Error ? error.message : "לא ניתן לטעון את ממשק הניהול.");
      });
    });
  }, [loadProfile, loadStaffData]);

  async function login(email: string, password: string) {
    setBusy(true);
    setMessage("");
    try {
      const tokens = await api<Tokens>("/auth/login", {
        method: "POST", body: JSON.stringify({ email, password }),
      }, false);
      saveTokens(tokens);
      await loadProfile();
      await loadStaffData(day);
    } catch (error) {
      clearTokens();
      setUser(null);
      setMessage(error instanceof Error ? error.message : "הכניסה נכשלה.");
    } finally { setBusy(false); }
  }

  function logout() {
    clearTokens();
    setUser(null);
    setDashboard(null);
    setAppointments([]);
    setMessage("התנתקת בהצלחה.");
  }

  async function changeDay(value: string) {
    setDay(value);
    try { setAppointments(await api<StaffAppointment[]>(`/staff/appointments?date=${value}`)); }
    catch (error) { setMessage(error instanceof Error ? error.message : "לא ניתן לטעון תורים."); }
  }

  async function bookingSaved(value: string) {
    setDay(value);
    await loadStaffData(value);
  }

  async function updateAppointment(id: number, action: "complete" | "no-show" | "cancel") {
    if (!window.confirm(action === "complete" ? "לסמן שהטיפול הושלם? אם נעשה שימוש בחבילה, ירד טיפול אחד מהיתרה." : action === "cancel" ? "לבטל את התור? חלון פנוי עשוי להיות מוצע ללקוחה ברשימת ההמתנה." : "לסמן שהלקוחה לא הגיעה?")) return;
    setBusy(true);
    try {
      const path = action === "complete" ? `/appointments/${id}/complete` : action === "cancel" ? `/staff/appointments/${id}` : `/staff/appointments/${id}/no-show`;
      await api(path, { method: action === "cancel" ? "DELETE" : "PATCH" });
      await loadStaffData(day);
      setMessage(action === "complete" ? "הטיפול הושלם והיתרה עודכנה פעם אחת בלבד." : action === "cancel" ? "התור בוטל ורשימת ההמתנה עודכנה." : "התור סומן כלא הגיעה.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "העדכון נכשל."); }
    finally { setBusy(false); }
  }

  async function downloadReport(kind: "appointments" | "orders") {
    setBusy(true);
    try {
      const response = await request(`/staff/reports/${kind}.csv`);
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = `scosmetics-${kind}.csv`;
      document.body.append(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setMessage("הדוח הורד כקובץ CSV.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "לא ניתן לייצא דוח."); }
    finally { setBusy(false); }
  }

  if (!user) return <LoginPanel busy={busy} message={message} onLogin={login} />;

  return <div className={styles.shell}>
    <aside className={styles.sidebar}>
      <div className={styles.brand}><span className={styles.brandMark}>S</span><div><strong>S Cosmetics</strong><small>Clinic management</small></div></div>
      <nav className={styles.nav} aria-label="ניווט ממשק ניהול">
        <button className={tab === "dashboard" ? styles.selected : ""} onClick={() => setTab("dashboard")}>לוח בקרה</button>
        <button className={tab === "appointments" ? styles.selected : ""} onClick={() => setTab("appointments")}>יומן ותורים</button>
        {user.role === "admin" && <button className={tab === "catalog" ? styles.selected : ""} onClick={() => setTab("catalog")}>טיפולים וחבילות</button>}
        {user.role === "admin" && <button className={tab === "content" ? styles.selected : ""} onClick={() => setTab("content")}>תוכן האתר</button>}
        {user.role === "admin" && <button className={tab === "equipment" ? styles.selected : ""} onClick={() => setTab("equipment")}>רשימת ציוד</button>}
        {user.role === "admin" && <button className={tab === "team" ? styles.selected : ""} onClick={() => setTab("team")}>צוות האתר</button>}
        {user.role === "admin" && <button className={tab === "staff" ? styles.selected : ""} onClick={() => setTab("staff")}>מטפלות ותזמונים</button>}
        {user.role === "admin" && <button className={tab === "customers" ? styles.selected : ""} onClick={() => setTab("customers")}>לקוחות</button>}
        {user.role === "admin" && <button className={tab === "reports" ? styles.selected : ""} onClick={() => setTab("reports")}>דוחות וייצוא</button>}
      </nav>
      <div className={styles.userCard}><strong>{user.first_name} {user.last_name}</strong><span>{user.role === "admin" ? "מנהלת" : "מטפלת"}</span><button type="button" onClick={logout}>התנתקות</button></div>
    </aside>
    <main className={styles.main}>
      <header className={styles.topbar}><div><span className={styles.eyebrow}>S COSMETICS / {user.role === "admin" ? "ADMIN" : "BEAUTICIAN"}</span><h1>{tab === "dashboard" ? `שלום, ${user.first_name}` : tab === "appointments" ? "יומן ותורים" : tab === "catalog" ? "טיפולים וחבילות" : tab === "content" ? "תוכן האתר" : tab === "equipment" ? "רשימת ציוד" : tab === "team" ? "צוות האתר" : tab === "staff" ? "מטפלות ותזמונים" : tab === "customers" ? "לקוחות" : "דוחות וייצוא"}</h1></div><span>{new Date().toLocaleDateString("he-IL")}</span></header>
      {message && <p role="status" className={styles.message}>{message}</p>}
      {tab === "dashboard" && dashboard && <DashboardPanel data={dashboard} admin={user.role === "admin"} busy={busy} onUpdate={updateAppointment} onShowCalendar={() => setTab("appointments")} />}
      {tab === "appointments" && <AppointmentsPanel items={appointments} beauticians={beauticians} admin={user.role === "admin"} day={day} busy={busy} onDayChange={changeDay} onUpdate={updateAppointment} onBookingSaved={bookingSaved} onMessage={setMessage} />}
      {tab === "catalog" && user.role === "admin" && <CatalogPanel onMessage={setMessage} />}
      {tab === "content" && user.role === "admin" && <ContentPanel onMessage={setMessage} />}
      {tab === "equipment" && user.role === "admin" && <EquipmentPanel onMessage={setMessage} />}
      {tab === "team" && user.role === "admin" && <TeamPanel onMessage={setMessage} />}
      {tab === "staff" && user.role === "admin" && <StaffPanel onMessage={setMessage} onChanged={() => void loadStaffData(day)} />}
      {tab === "customers" && user.role === "admin" && <CustomersPanel onMessage={setMessage} />}
      {tab === "reports" && user.role === "admin" && <section className={styles.panel}><h2>ייצוא נתוני העסק</h2><p>דוחות CSV כוללים עד 5,000 רשומות. סכומי ההזמנות הם נתוני הדגמה, ללא סליקה אמיתית.</p><div className={styles.reportActions}><button className={styles.primaryButton} disabled={busy} onClick={() => void downloadReport("appointments")}>הורדת דוח תורים</button><button className={styles.secondaryButton} disabled={busy} onClick={() => void downloadReport("orders")}>הורדת דוח הזמנות</button></div></section>}
    </main>
  </div>;
}
