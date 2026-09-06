import Image from "next/image";
import styles from "@/app/page.module.css";
import { TherapistCard } from "./TherapistCard";

const therapists = [
  {
    name: "מטפלת1",
    role: "קוסמטיקאית פרה-רפואית",
    description:
      "קוסמטיקאית מקצועית המתמחה בהתאמת טיפולי פנים לצורכי העור, תוך הקפדה על עבודה עדינה, אבחון אישי וליווי לאורך התהליך.",
  },
  {
    name: "מטפלת2",
    role: "מומחית להזרקות ועיצוב שפתיים",
    description:
      "מטפלת בתחום האסתטיקה המתמקדת בתכנון אישי וביצירת מראה מאוזן וטבעי, מתוך הקשבה לרצונות המטופלת ושמירה על תהליך מקצועי ומדויק.",
  },
  {
    name: "מטפלת3",
    role: "קוסמטיקאית פרה-רפואית",
    description:
      "קוסמטיקאית בעלת גישה אישית ואהבה לעולם הטיפוח, המשלבת ידע מקצועי עם התאמת שגרת טיפול שמטרתה לשמור על עור בריא ומטופח.",
  },
  {
    name: "מטפלת4",
    role: "מומחית להזרקות ועיצוב שפתיים",
    description:
      "מטפלת אסתטית המתמחה בהתאמת טיפולים למבנה הפנים, עם תשומת לב לפרטים, תקשורת פתוחה ושאיפה לתוצאה עדינה והרמונית.",
  },
] as const;

export function TeamSection() {
  return (
    <section className={styles.team} id="team">
      <div className={styles.teamHeading}>
        <span className={styles.sectionNumber}>הכר את המטפלות</span>
        <h2>הצוות שמלווה אותך בדרך לעור בריא ומטופח.</h2>
      </div>

      <article className={styles.founderProfile}>
        <Image
          className={styles.founderImage}
          src="/images/Sigal_Levi.png"
          alt="סיגל לוי, מייסדת מכון היופי S.Cosmetics"
          width={1080}
          height={1080}
          sizes="(max-width: 600px) calc(100vw - 40px), 560px"
        />
        <div className={styles.founderContent}>
          <h3>סיגל לוי</h3>
          <strong>מייסדת מכון היופי S.Cosmetics</strong>
          <p>
            סיגל הקימה את המכון מתוך אהבה לעולם הטיפוח והאסתטיקה ומתוך אמונה
            שטיפול מקצועי מתחיל בהקשבה. היא משלבת יחס אישי, ניסיון והתאמה לצרכים
            הייחודיים של כל מטופלת.
          </p>
        </div>
      </article>

      <div className={styles.teamGrid}>
        {therapists.map((therapist) => (
          <TherapistCard
            key={therapist.name}
            {...therapist}
            imageSrc="/images/logo-scosmetics.png"
          />
        ))}
      </div>
    </section>
  );
}
