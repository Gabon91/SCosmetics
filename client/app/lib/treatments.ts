export type Treatment = {
  id: number;
  name: string;
  category: string;
  description: string;
  duration_minutes: number;
  price: number;
  accent: "light-pink" | "powder-pink" | "strong-pink" | string;
};

const fallbackTreatments: Treatment[] = [
  {
    id: 1,
    name: "טיפול זוהר לפנים",
    category: "טיפולי פנים",
    description: "ניקוי עמוק, הזנה ולחות למראה רענן ואחיד.",
    duration_minutes: 60,
    price: 420,
    accent: "light-pink",
  },
  {
    id: 2,
    name: "אנטי אייג׳ינג מתקדם",
    category: "אנטי אייג׳ינג",
    description: "פרוטוקול מותאם לחידוש העור, מיצוק ושיפור המרקם.",
    duration_minutes: 75,
    price: 590,
    accent: "powder-pink",
  },
  {
    id: 3,
    name: "הסרת שיער בלייזר",
    category: "טיפולי לייזר",
    description: "טיפול ממוקד בטכנולוגיה מתקדמת ובתוכנית אישית.",
    duration_minutes: 45,
    price: 280,
    accent: "strong-pink",
  },
];

export async function getTreatments(): Promise<Treatment[]> {
  const apiBaseUrl = process.env.API_BASE_URL ?? "http://localhost:8000/api/v1";

  try {
    const response = await fetch(`${apiBaseUrl}/treatments`, {
      cache: "no-store",
      signal: AbortSignal.timeout(1200),
    });

    if (!response.ok) {
      return fallbackTreatments;
    }

    return (await response.json()) as Treatment[];
  } catch {
    return fallbackTreatments;
  }
}
