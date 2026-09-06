import styles from "@/app/page.module.css";

export function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.brand}>
        <span className={styles.brandMark}>S</span>
        <span>
          <strong>S Cosmetics</strong>
          <small>Advanced Skin Clinic</small>
        </span>
      </div>
      <p>אתר הדגמה לפרויקט גמר Full Stack · כל הזכויות שמורות</p>
    </footer>
  );
}
