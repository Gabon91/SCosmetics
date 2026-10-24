"use client";

import { type FormEvent, useState } from "react";
import styles from "./Portal.module.css";

export type AuthForm = {
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  password: string;
  passwordConfirmation: string;
};

type Props = {
  onSubmit: (mode: "login" | "register", form: AuthForm) => Promise<void>;
  busy: boolean;
};

export function AuthPanel({ onSubmit, busy }: Props) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState<AuthForm>({
    firstName: "", lastName: "", email: "", phone: "",
    password: "", passwordConfirmation: "",
  });

  function update(field: keyof AuthForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void onSubmit(mode, form);
  }

  return (
    <section className={styles.authCard} aria-labelledby="auth-title">
      <span className={styles.eyebrow}>לפני שמתחילות</span>
      <h2 id="auth-title">{mode === "login" ? "כניסה לאזור האישי" : "מצטרפות אלינו"}</h2>
      <p>כדי לשמור תור ולעקוב אחר חבילות הטיפול, התחברי או צרי חשבון.</p>
      <form onSubmit={submit} className={styles.form}>
        {mode === "register" && (
          <div className={styles.formRow}>
            <label>שם פרטי<input required minLength={2} value={form.firstName} onChange={(e) => update("firstName", e.target.value)} /></label>
            <label>שם משפחה<input required minLength={2} value={form.lastName} onChange={(e) => update("lastName", e.target.value)} /></label>
          </div>
        )}
        <label>כתובת אימייל<input required type="email" autoComplete="email" value={form.email} onChange={(e) => update("email", e.target.value)} /></label>
        {mode === "register" && (
          <label>טלפון<input required type="tel" autoComplete="tel" value={form.phone} onChange={(e) => update("phone", e.target.value)} /></label>
        )}
        <label>סיסמה<input required type="password" minLength={mode === "register" ? 8 : 1} autoComplete={mode === "register" ? "new-password" : "current-password"} value={form.password} onChange={(e) => update("password", e.target.value)} /></label>
        {mode === "register" && (
          <label>אימות סיסמה<input required type="password" minLength={8} autoComplete="new-password" value={form.passwordConfirmation} onChange={(e) => update("passwordConfirmation", e.target.value)} /></label>
        )}
        <button className={styles.primaryButton} disabled={busy} type="submit">{busy ? "רגע אחד..." : mode === "login" ? "כניסה" : "יצירת חשבון"}</button>
      </form>
      <button className={styles.textButton} type="button" onClick={() => setMode(mode === "login" ? "register" : "login")}>{mode === "login" ? "אין לך חשבון? להרשמה" : "כבר יש לך חשבון? לכניסה"}</button>
    </section>
  );
}
