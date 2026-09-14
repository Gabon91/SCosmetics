import styles from "@/app/page.module.css";

export function AboutSection({ content }: { content: Record<string, string> }) {
  return (
    <section className={styles.about} id="about">
      <div>
        <span className={styles.sectionNumber}>אודות הקליניקה</span>
        <h2>{content.about_title ?? "יופי בריא מתחיל בהבנה עמוקה של העור."}</h2>
      </div>
      <div className={styles.aboutCopy}>
        <p>{content.about_body ?? "ב־S Cosmetics אנחנו משלבות ניסיון מקצועי, מכשור מתקדם וחומרים פעילים כדי ליצור תוכנית טיפול מדויקת — בלי קיצורי דרך ובלי הבטחות גנריות."}</p>
        <a href="#team">
          הכירי את המטפלות <span aria-hidden="true">←</span>
        </a>
      </div>
    </section>
  );
}
