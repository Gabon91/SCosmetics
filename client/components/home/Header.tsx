import Image from "next/image";
import styles from "@/app/page.module.css";

export function Header() {
  return (
    <header className={styles.header}>
      <a className={styles.brand} href="#top" aria-label="S Cosmetics — דף הבית">
        <Image
          className={styles.brandLogo}
          src="/images/logo-scosmetics.png"
          alt="S Cosmetics — מכון יופי, טיפוח וקוסמטיקה"
          width={1254}
          height={1254}
          priority
        />
      </a>

      <nav className={styles.nav} aria-label="ניווט ראשי">
        <a href="#about">אודות</a>
        <a href="#treatments">טיפולים</a>
        <a href="#team">המטפלות</a>
        <a href="#contact">יצירת קשר</a>
      </nav>

      <a className={styles.headerCta} href="#contact">
        קביעת פגישת ייעוץ
      </a>
    </header>
  );
}
