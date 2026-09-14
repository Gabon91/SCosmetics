import type { Equipment } from "@/app/lib/site";
import styles from "@/app/page.module.css";
import { ExpandableCard } from "./ExpandableCard";

export function EquipmentSection({ content, equipment }: { content: Record<string, string>; equipment: Equipment[] }) {
  return (
    <section className={styles.equipmentSection} id="equipment">
      <div className={styles.teamHeading}>
        <span className={styles.sectionNumber}>מכשור וחומרים</span>
        <h2>{content.equipment_title ?? "טכנולוגיה שמותאמת לטיפול שלך."}</h2>
        <p className={styles.equipmentIntro}>{content.equipment_intro ?? "אנחנו בוחרות את המכשור לפי מטרת הטיפול וצרכי העור, עם תשומת לב לפרטים הקטנים."}</p>
      </div>
      {equipment.length > 0 && (
        <div className={styles.equipmentGrid}>
          {equipment.map((item) => (
            <ExpandableCard
              key={item.id}
              title={item.name}
              subtitle={item.manufacturer || "מכשור מקצועי"}
              description={item.description}
              imageSrc={item.image_url || "/images/logo-scosmetics.png"}
              imageAlt={`תמונה של ${item.name}`}
              readMoreLabel={`קרא עוד על ${item.name}`}
              closeLabel={`סגור את המידע על ${item.name}`}
            />
          ))}
        </div>
      )}
      <div className={styles.materialsBox}>
        <h3>{content.materials_title ?? "חומרים שנבחרים בקפידה."}</h3>
        <p>{content.materials_body ?? "התאמת תכשירים וחומרים מקצועיים מתבצעת לאחר אבחון אישי ובהתאם לסוג העור ולמטרות הטיפול."}</p>
      </div>
    </section>
  );
}
