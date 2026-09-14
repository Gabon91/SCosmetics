import styles from "@/app/page.module.css";

export function ContactSection() {
  return (
    <section className={styles.contact} id="contact">
      <span className={styles.sectionNumber}>מתחילות מכאן</span>
      <h2>בואי נכיר את העור שלך.</h2>
      <p>בחרי את הטיפול והיום שמתאימים לך — ונמצא יחד שעה פנויה.</p>
      <a className={styles.lightButton} href="/portal?tab=book">
        לקביעת תור
        <span aria-hidden="true">←</span>
      </a>
    </section>
  );
}
