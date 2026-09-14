"use client";

import Image from "next/image";
import { useId, useState } from "react";
import styles from "@/app/page.module.css";

type ExpandableCardProps = {
  title: string;
  subtitle: string;
  description: string;
  imageSrc: string;
  imageAlt: string;
  readMoreLabel: string;
  closeLabel: string;
};

export function ExpandableCard({
  title,
  subtitle,
  description,
  imageSrc,
  imageAlt,
  readMoreLabel,
  closeLabel,
}: ExpandableCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const detailsId = `${useId()}-details`;

  return (
    <article className={styles.expandableCard}>
      <div className={styles.expandableImageFrame}>
        <Image className={styles.expandableImage} src={imageSrc} alt={imageAlt} width={1254} height={1254} />
      </div>
      <div className={styles.expandableCardContent}>
        <h3>{title}</h3>
        <p className={styles.expandableSubtitle}>{subtitle}</p>
        <button
          className={styles.readMoreButton}
          type="button"
          aria-expanded={isExpanded}
          aria-controls={detailsId}
          onClick={() => setIsExpanded((current) => !current)}
        >
          {isExpanded ? closeLabel : readMoreLabel}
          <span className={styles.readMoreIcon} data-expanded={isExpanded} aria-hidden="true">↓</span>
        </button>
        <div className={styles.expandableDetails} data-expanded={isExpanded} id={detailsId}>
          <div className={styles.expandableDetailsInner}><p>{description}</p></div>
        </div>
      </div>
    </article>
  );
}
