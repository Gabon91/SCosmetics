import styles from "@/app/page.module.css";

export function ContactSection({ content }: { content: Record<string, string> }) {
  return (
    <section className={styles.contact} id="contact">
      <span className={styles.sectionNumber}>מתחילות מכאן</span>
      <h2>{content.contact_title ?? "בואי נכיר את העור שלך."}</h2>
      <p>{content.contact_body ?? "בחרי את הטיפול והיום שמתאימים לך — ונמצא יחד שעה פנויה."}</p>
      <a className={styles.lightButton} href="/portal?tab=book">
        לקביעת תור
        <span aria-hidden="true">←</span>
      </a>
      <p>שעות פעילות: {content.opening_hours ?? "א׳–ה׳, 09:00–17:00"}</p>
    </section>
  );
}
