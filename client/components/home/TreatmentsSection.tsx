import type { Treatment } from "@/app/lib/treatments";
import styles from "@/app/page.module.css";

type TreatmentsSectionProps = {
  treatments: Treatment[];
};

const formatPrice = (price: number) =>
  new Intl.NumberFormat("he-IL", {
    style: "currency",
    currency: "ILS",
    maximumFractionDigits: 0,
  }).format(price);

export function TreatmentsSection({ treatments }: TreatmentsSectionProps) {
  return (
    <section className={styles.treatmentsSection} id="treatments">
      <div className={styles.sectionHeading}>
        <div>
          <span className={styles.sectionNumber}>טיפולים נבחרים</span>
          <h2>הטיפול הנכון, בזמן הנכון.</h2>
        </div>
        <p>תוכנית הטיפול מותאמת עבורך אישית, לאחר אבחון והיכרות עם הצרכים שלך.</p>
      </div>

      <div className={styles.treatmentGrid}>
        {treatments.map((treatment, index) => (
          <article
            className={styles.treatmentCard}
            data-accent={treatment.accent}
            key={treatment.id}
          >
            <div className={styles.cardTopline}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <span>{treatment.category}</span>
            </div>
            <div className={styles.cardOrb} aria-hidden="true" />
            <div className={styles.cardContent}>
              <h3>{treatment.name}</h3>
              <p>{treatment.description}</p>
              <div className={styles.cardMeta}>
                <span>{treatment.duration_minutes} דקות</span>
                <strong>{formatPrice(treatment.price)}</strong>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
