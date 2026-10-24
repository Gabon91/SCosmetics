"use client";

import { type FormEvent, useState } from "react";
import styles from "@/app/page.module.css";

export function LoginPanel({ busy, message, onLogin }: { busy: boolean; message: string; onLogin: (email: string, password: string) => Promise<void> }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void onLogin(email, password).then(() => setPassword(""));
  }
  return <main className={styles.loginPage}><section className={styles.loginCard}>
    <span className={styles.eyebrow}>S COSMETICS / TEAM</span>
    <h1>כניסה לצוות הקליניקה</h1>
    <p>היומן ונתוני העסק זמינים למטפלות ולמנהלת בלבד.</p>
    {message && <p role="alert" className={styles.message}>{message}</p>}
    <form className={styles.form} onSubmit={submit}>
      <label>כתובת אימייל<input type="email" autoComplete="username" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
      <label>סיסמה<input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
      <button type="submit" className={styles.primaryButton} disabled={busy}>{busy ? "מתחברים..." : "כניסה"}</button>
    </form>
  </section></main>;
}
