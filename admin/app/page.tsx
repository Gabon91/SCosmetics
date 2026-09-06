import styles from "./page.module.css";

const kpis = [
  ["תורים היום", "12", "+2 מאתמול"],
  ["הכנסות החודש", "₪18,450", "+14% מהחודש שעבר"],
  ["לקוחות פעילות", "86", "+7 החודש"],
  ["חבילות שנמכרו", "24", "+5 השבוע"],
] as const;

const appointments = [
  ["09:00", "נועה לוי", "טיפול זוהר לפנים", "מאושר"],
  ["10:30", "מיכל כהן", "אנטי אייג׳ינג מתקדם", "מאושר"],
  ["12:00", "דנה ישראלי", "הסרת שיער בלייזר", "ממתין"],
  ["14:15", "שירה אברהם", "טיפול זוהר לפנים", "מאושר"],
] as const;

const treatmentDistribution = [
  ["טיפולי פנים", 76],
  ["אנטי אייג׳ינג", 58],
  ["לייזר", 42],
] as const;

export default function AdminDashboard() {
  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <span className={styles.brandMark}>S</span>
          <div>
            <strong>S Cosmetics</strong>
            <small>Clinic management</small>
          </div>
        </div>

        <nav className={styles.nav} aria-label="ניווט ממשק ניהול">
          <a href="#dashboard"><span>01</span><strong>לוח בקרה</strong></a>
          <a href="#appointments"><span>02</span><strong>יומן ותורים</strong></a>
          <a href="#customers"><span>03</span><strong>לקוחות</strong></a>
          <a href="#treatments"><span>04</span><strong>טיפולים</strong></a>
          <a href="#packages"><span>05</span><strong>חבילות</strong></a>
          <a href="#content"><span>06</span><strong>תוכן האתר</strong></a>
          <a href="#reports"><span>07</span><strong>דוחות</strong></a>
        </nav>

        <div className={styles.userCard}>
          <span className={styles.avatar}>ש</span>
          <div>
            <strong>שלי ישראלי</strong>
            <small>מנהלת מערכת</small>
          </div>
        </div>
      </aside>

      <main className={styles.main} id="dashboard">
        <header className={styles.topbar}>
          <div>
            <span className={styles.eyebrow}>יום חמישי · 27 באוגוסט</span>
            <h1>ערב טוב, שלי</h1>
          </div>
          <button className={styles.primaryButton} type="button">
            + תור חדש
          </button>
        </header>

        <section className={styles.kpiGrid} aria-label="מדדי פעילות מרכזיים">
          {kpis.map(([label, value, change]) => (
            <article className={styles.kpiCard} key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
              <small>{change}</small>
            </article>
          ))}
        </section>

        <section className={styles.dashboardGrid}>
          <article className={styles.panel} id="appointments">
            <div className={styles.panelHeader}>
              <h2>התורים של היום</h2>
              <button type="button">לכל היומן ←</button>
            </div>
            <div className={styles.appointmentList}>
              {appointments.map(([time, customer, treatment, status]) => (
                <div className={styles.appointment} key={`${time}-${customer}`}>
                  <time>{time}</time>
                  <div>
                    <strong>{customer}</strong>
                    <small>{treatment}</small>
                  </div>
                  <span className={styles.status}>{status}</span>
                </div>
              ))}
            </div>
          </article>

          <article className={styles.panel}>
            <div className={styles.panelHeader}>
              <h2>התפלגות טיפולים</h2>
              <button type="button">החודש</button>
            </div>
            <div className={styles.progressList}>
              {treatmentDistribution.map(([label, value]) => (
                <div className={styles.progressRow} key={label}>
                  <div><span>{label}</span><strong>{value}%</strong></div>
                  <div className={styles.progressTrack}>
                    <i style={{ width: `${value}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </article>
        </section>
      </main>
    </div>
  );
}

