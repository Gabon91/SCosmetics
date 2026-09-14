"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AccountPanel } from "./AccountPanel";
import { AuthPanel, type AuthForm } from "./AuthPanel";
import { BookingPanel } from "./BookingPanel";
import { PackagesPanel } from "./PackagesPanel";
import { api, clearTokens, hasSession, saveTokens, type TokenPair } from "./api";
import type {
  Appointment,
  CustomerPackage,
  Order,
  Package,
  Treatment,
  User,
  WaitlistEntry,
} from "./types";
import styles from "./Portal.module.css";

type Tab = "book" | "packages" | "account";

export function Portal() {
  const [tab, setTab] = useState<Tab>("book");
  const [authenticated, setAuthenticated] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [treatments, setTreatments] = useState<Treatment[]>([]);
  const [packages, setPackages] = useState<Package[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [customerPackages, setCustomerPackages] = useState<CustomerPackage[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [waitlist, setWaitlist] = useState<WaitlistEntry[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const loadAccount = useCallback(async () => {
    const [profile, myAppointments, myPackages, myOrders, myWaitlist] =
      await Promise.all([
        api<User>("/auth/me", {}, true),
        api<Appointment[]>("/me/appointments", {}, true),
        api<CustomerPackage[]>("/me/packages", {}, true),
        api<Order[]>("/me/orders", {}, true),
        api<WaitlistEntry[]>("/me/waitlist", {}, true),
      ]);
    setUser(profile);
    setAppointments(myAppointments);
    setCustomerPackages(myPackages);
    setOrders(myOrders);
    setWaitlist(myWaitlist);
    setAuthenticated(true);
  }, []);

  useEffect(() => {
    const requestedTab = new URLSearchParams(window.location.search).get("tab");
    if (requestedTab === "account" || requestedTab === "packages") {
      queueMicrotask(() => setTab(requestedTab));
    }
    Promise.all([
      api<Treatment[]>("/treatments"),
      api<Package[]>("/packages"),
    ])
      .then(([catalog, offers]) => {
        setTreatments(catalog);
        setPackages(offers);
      })
      .catch(() => setMessage("לא ניתן לטעון את הנתונים. ודאי שהשרת פועל."));
    if (hasSession()) {
      queueMicrotask(() => {
        loadAccount().catch(() => {
          clearTokens();
          setAuthenticated(false);
        });
      });
    }
  }, [loadAccount]);

  function switchTab(next: Tab) {
    setTab(next);
    setMessage("");
    window.history.replaceState(null, "", `/portal?tab=${next}`);
  }

  async function handleAuth(mode: "login" | "register", form: AuthForm) {
    setBusy(true);
    setMessage("");
    try {
      if (mode === "register") {
        await api("/auth/register", {
          method: "POST",
          body: JSON.stringify({
            first_name: form.firstName,
            last_name: form.lastName,
            email: form.email,
            phone: form.phone,
            password: form.password,
            password_confirmation: form.passwordConfirmation,
          }),
        });
      }
      const tokens = await api<TokenPair>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: form.email, password: form.password }),
      });
      saveTokens(tokens);
      await loadAccount();
      setMessage(mode === "register" ? "נרשמת והתחברת בהצלחה." : "ברוכה הבאה!");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "ההתחברות נכשלה.");
    } finally {
      setBusy(false);
    }
  }

  async function handlePurchase(packageId: number) {
    setBusy(true);
    setMessage("");
    try {
      await api(
        "/orders",
        { method: "POST", body: JSON.stringify({ package_id: packageId }) },
        true,
      );
      await loadAccount();
      setMessage("חבילת ההדגמה נוספה לאזור האישי. לא בוצע חיוב כספי.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "הפעולה נכשלה.");
    } finally {
      setBusy(false);
    }
  }

  async function handleCancel(appointmentId: number) {
    if (!window.confirm("לבטל את התור?")) return;
    setBusy(true);
    try {
      await api(`/appointments/${appointmentId}`, { method: "DELETE" }, true);
      await loadAccount();
      setMessage("התור בוטל. אם יש רשימת המתנה, החלון הוצע ללקוחה הבאה.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "לא ניתן לבטל את התור.");
    } finally {
      setBusy(false);
    }
  }

  async function handleAccept(entry: WaitlistEntry) {
    if (!entry.offered_start_time || !entry.beautician_id) return;
    setBusy(true);
    try {
      await api(
        "/appointments",
        {
          method: "POST",
          body: JSON.stringify({
            treatment_id: entry.treatment_id,
            beautician_id: entry.beautician_id,
            start_time: entry.offered_start_time,
          }),
        },
        true,
      );
      await loadAccount();
      setMessage("המקום שהתפנה נקבע עבורך בהצלחה.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "לא ניתן לקבוע את התור.");
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    clearTokens();
    setAuthenticated(false);
    setUser(null);
    setAppointments([]);
    setCustomerPackages([]);
    setOrders([]);
    setWaitlist([]);
    setMessage("התנתקת בהצלחה.");
  }

  return (
    <main className={styles.root} data-portal>
      <header className={styles.header}>
        <Link href="/" className={styles.brand} aria-label="חזרה לדף הבית">
          <Image src="/images/logo-scosmetics.png" alt="S Cosmetics" width={1254} height={1254} />
        </Link>
        <nav className={styles.tabs} aria-label="אזור לקוחות">
          <button className={tab === "book" ? styles.active : ""} onClick={() => switchTab("book")}>קביעת תור</button>
          <button className={tab === "packages" ? styles.active : ""} onClick={() => switchTab("packages")}>חבילות</button>
          <button className={tab === "account" ? styles.active : ""} onClick={() => switchTab("account")}>האזור האישי</button>
        </nav>
        <Link className={styles.homeLink} href="/">לדף הבית ←</Link>
      </header>

      <div className={styles.intro}>
        <span>הטיפול שלך, בדרך שלך</span>
        <h1>{tab === "book" ? "קובעות זמן לעצמך" : tab === "packages" ? "טיפוח שנמשך איתך" : "המקום האישי שלך"}</h1>
        <p>קביעת תורים לפי זמינות אמיתית, חבילות טיפול ומעקב אישי — במקום אחד.</p>
      </div>

      {message && <p className={styles.message} role="status">{message}</p>}

      {!authenticated && tab !== "packages" && (
        <AuthPanel onSubmit={handleAuth} busy={busy} />
      )}
      {tab === "book" && authenticated && (
        <BookingPanel
          treatments={treatments}
          packages={packages}
          customerPackages={customerPackages}
          onChanged={loadAccount}
          onMessage={setMessage}
        />
      )}
      {tab === "packages" && (
        <PackagesPanel
          packages={packages}
          authenticated={authenticated}
          busy={busy}
          onPurchase={handlePurchase}
          onLogin={() => switchTab("account")}
        />
      )}
      {tab === "account" && authenticated && user && (
        <AccountPanel
          user={user}
          appointments={appointments}
          customerPackages={customerPackages}
          orders={orders}
          waitlist={waitlist}
          treatments={treatments}
          busy={busy}
          onCancel={handleCancel}
          onAccept={handleAccept}
          onLogout={logout}
        />
      )}

      <footer className={styles.footer}>S Cosmetics · טיפול שמתחיל בהקשבה לעור</footer>
    </main>
  );
}
