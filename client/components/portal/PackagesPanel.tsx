import type { Package } from "./types";
import styles from "./Portal.module.css";

type Props = {
  packages: Package[];
  authenticated: boolean;
  busy: boolean;
  onPurchase: (packageId: number) => Promise<void>;
  onLogin: () => void;
};

export function PackagesPanel({ packages, authenticated, busy, onPurchase, onLogin }: Props) {
  return (
    <section className={styles.content} aria-labelledby="packages-title">
      <div className={styles.sectionHeading}><span className={styles.eyebrow}>02 / חבילות טיפולים</span><h2 id="packages-title">תהליך שמתאים לך</h2><p>חבילות טיפול שמאפשרות רצף ומעקב אישי.</p></div>
      <div className={styles.packageGrid}>
        {packages.map((item) => (
          <article className={styles.packageCard} key={item.id}>
            <span className={styles.eyebrow}>S COSMETICS / CARE</span>
            <h3>{item.name}</h3>
            <p>{item.sessions} טיפולים · תוקף של {item.validity_days} ימים</p>
            <strong className={styles.price}>₪{Number(item.price).toLocaleString("he-IL")}</strong>
            <button className={styles.primaryButton} disabled={busy} type="button" onClick={() => authenticated ? void onPurchase(item.id) : onLogin()}>{authenticated ? "הוספה לחשבון — הדגמה" : "כניסה לרכישת הדגמה"}</button>
          </article>
        ))}
      </div>
      <p className={styles.demoNotice}>פרויקט לימודי: תהליך ההזמנה מדגים רכישת חבילה בלבד. אין סליקת אשראי או חיוב כספי.</p>
    </section>
  );
}
