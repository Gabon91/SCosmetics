"use client";

import Image from "next/image";
import { useId, useState } from "react";
import styles from "@/app/page.module.css";

type TherapistCardProps = {
  name: string;
  role: string;
  description: string;
  imageSrc: string;
};

export function TherapistCard({
  name,
  role,
  description,
  imageSrc,
}: TherapistCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const detailsId = `${useId()}-details`;

  return (
    <article className={styles.therapistCard}>
      <div className={styles.therapistImageFrame}>
        <Image
          className={styles.therapistImage}
          src={imageSrc}
          alt={`תמונה זמנית עבור ${name}`}
          width={1254}
          height={1254}
        />
      </div>

      <div className={styles.therapistCardContent}>
        <h3>{name}</h3>
        <p className={styles.therapistRole}>{role}</p>

        <button
          className={styles.readMoreButton}
          type="button"
          aria-expanded={isExpanded}
          aria-controls={detailsId}
          onClick={() => setIsExpanded((currentValue) => !currentValue)}
        >
          {isExpanded ? `סגור את המידע על ${name}` : `קרא עוד על ${name}`}
          <span
            className={styles.readMoreIcon}
            data-expanded={isExpanded}
            aria-hidden="true"
          >
            ↓
          </span>
        </button>

        <div
          className={styles.therapistDetails}
          data-expanded={isExpanded}
          id={detailsId}
        >
          <div className={styles.therapistDetailsInner}>
            <p>{description}</p>
          </div>
        </div>
      </div>
    </article>
  );
}
