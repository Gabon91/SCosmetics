"use client";

import { type FormEvent, useState } from "react";
import type { User } from "./types";
import styles from "./Portal.module.css";

export function ProfileEditor({ user, busy, onSave }: { user: User; busy: boolean; onSave: (profile: Pick<User, "first_name" | "last_name" | "email" | "phone">) => Promise<void> }) {
  const [profile, setProfile] = useState({ first_name: user.first_name, last_name: user.last_name, email: user.email, phone: user.phone });

  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void onSave(profile);
  }

  return <section className={styles.card} aria-labelledby="profile-title">
    <h3 id="profile-title">הפרטים שלי</h3>
    <form className={styles.form} onSubmit={save}>
      <div className={styles.formRow}>
        <label>שם פרטי<input required minLength={2} value={profile.first_name} onChange={(event) => setProfile({ ...profile, first_name: event.target.value })} /></label>
        <label>שם משפחה<input required minLength={2} value={profile.last_name} onChange={(event) => setProfile({ ...profile, last_name: event.target.value })} /></label>
      </div>
      <label>אימייל<input required type="email" value={profile.email} onChange={(event) => setProfile({ ...profile, email: event.target.value })} /></label>
      <label>טלפון<input required type="tel" minLength={7} value={profile.phone} onChange={(event) => setProfile({ ...profile, phone: event.target.value })} /></label>
      <button className={styles.primaryButton} type="submit" disabled={busy}>שמירת פרטים</button>
    </form>
  </section>;
}
