"use client";

import Image from "next/image";
import Link from "next/link";
import styles from "./SiteHeader.module.css";

type PortalTab = "book" | "packages" | "account";

type SiteHeaderProps =
  | { variant?: "home"; activeTab?: never; onTabChange?: never }
  | { variant: "portal"; activeTab: PortalTab; onTabChange: (tab: PortalTab) => void };

export function SiteHeader(props: SiteHeaderProps) {
  const isPortal = props.variant === "portal";

  return (
    <header className={`${styles.header} ${isPortal ? styles.portal : ""}`}>
      <Link className={styles.brand} href={isPortal ? "/" : "/#top"} aria-label="S Cosmetics — דף הבית">
        <Image
          className={styles.brandLogo}
          src="/images/logo-scosmetics.png"
          alt="S Cosmetics — מכון יופי, טיפוח וקוסמטיקה"
          width={1254}
          height={1254}
          priority
        />
      </Link>

      {isPortal ? (
        <nav className={styles.nav} aria-label="אזור לקוחות">
          <button type="button" className={props.activeTab === "book" ? styles.active : ""} onClick={() => props.onTabChange("book")}>קביעת תור</button>
          <button type="button" className={props.activeTab === "packages" ? styles.active : ""} onClick={() => props.onTabChange("packages")}>חבילות</button>
          <button type="button" className={props.activeTab === "account" ? styles.active : ""} onClick={() => props.onTabChange("account")}>האזור האישי</button>
        </nav>
      ) : (
        <nav className={styles.nav} aria-label="ניווט ראשי">
          <Link href="/#about">אודות</Link>
          <Link href="/#treatments">טיפולים</Link>
          <Link href="/#team">המטפלות</Link>
          <Link href="/#contact">יצירת קשר</Link>
        </nav>
      )}

      <Link className={styles.headerCta} href={isPortal ? "/" : "/portal?tab=book"}>
        {isPortal ? "לדף הבית ←" : "קביעת תור"}
      </Link>
    </header>
  );
}
