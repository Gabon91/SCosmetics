import styles from "@/app/page.module.css";

export function HeroSection() {
  return (
    <section className={styles.hero} id="top">
      <div className={styles.heroCopy}>
        <span className={styles.eyebrow}>מדע, דיוק וטיפוח שנפגשים במקום אחד</span>
        <h1>
          להרגיש טוב בעור שלך,
          <span> בכל שלב בדרך.</span>
        </h1>
        <p>
          קליניקה לקוסמטיקה פרה-רפואית המתמחה בטיפולי פנים, אנטי אייג׳ינג
          ולייזר — עם אבחון אישי, טכנולוגיה מתקדמת וליווי מקצועי.
        </p>
        <div className={styles.heroActions}>
          <a className={styles.primaryButton} href="/portal?tab=book">
            קביעת תור
            <span aria-hidden="true">←</span>
          </a>
          <a className={styles.textButton} href="#treatments">
            הכירי את הטיפולים
          </a>
        </div>
        <div className={styles.trustRow} aria-label="יתרונות הקליניקה">
          <span>התאמה אישית</span>
          <span>סטנדרט מקצועי</span>
          <span>תוצאות טבעיות</span>
        </div>
      </div>

      <div className={styles.heroVisual} aria-label="מרחב טיפולים רגוע ומקצועי">
        <div className={styles.visualGlow} />
        <div className={styles.visualPanel}>
          <span className={styles.visualKicker}>Skin intelligence</span>
          <strong>טיפול שמתחיל בהקשבה לעור</strong>
          <p>אבחון · התאמה · מעקב</p>
        </div>
        <div className={styles.floatingCard}>
          <span>גישה אישית</span>
          <strong>100%</strong>
          <small>התוכנית נבנית עבורך</small>
        </div>
        <div className={styles.botanicalLine} aria-hidden="true">
          <i />
          <i />
          <i />
        </div>
      </div>
    </section>
  );
}
