import styles from "@/app/page.module.css";

export function ContactSection() {
  return (
    <section className={styles.contact} id="contact">
      <span className={styles.sectionNumber}>מתחילות מכאן</span>
      <h2>בואי נכיר את העור שלך.</h2>
      <p>השאירי פרטים ובקרוב נוסיף כאן קביעת תור מלאה עם זמינות בזמן אמת.</p>
      <a className={styles.lightButton} href="mailto:hello@scosmetics.co.il">
        hello@scosmetics.co.il
        <span aria-hidden="true">←</span>
      </a>
    </section>
  );
}
