export type Equipment = {
  id: number;
  name: string;
  manufacturer: string;
  description: string;
  image_url: string;
  treatment_ids: number[];
};

export type TeamMember = {
  id: number;
  name: string;
  title: string;
  description: string;
  image_url: string;
  featured: boolean;
  display_order: number;
};

export type SiteData = { content: Record<string, string>; equipment: Equipment[]; team: TeamMember[] | null };

const fallbackEquipment: Equipment[] = [{
  id: 0,
  name: "מכשיר לייזר להסרת שיער",
  manufacturer: "",
  description: "טכנולוגיה להסרת שיער במסגרת תוכנית טיפול אישית המותאמת ללקוחה.",
  image_url: "/images/Hair_Removal_Soprano.png",
  treatment_ids: [],
}];

export async function getSiteData(): Promise<SiteData> {
  const base = process.env.API_BASE_URL ?? "http://127.0.0.1:8004/api/v1";
  try {
    const [contentResponse, equipmentResponse, teamResponse] = await Promise.all([
      fetch(`${base}/site/content`, { cache: "no-store", signal: AbortSignal.timeout(1500) }),
      fetch(`${base}/site/equipment`, { cache: "no-store", signal: AbortSignal.timeout(1500) }),
      fetch(`${base}/site/team`, { cache: "no-store", signal: AbortSignal.timeout(1500) }),
    ]);
    if (!contentResponse.ok || !equipmentResponse.ok || !teamResponse.ok) throw new Error("Site API unavailable");
    return {
      content: (await contentResponse.json()) as Record<string, string>,
      equipment: (await equipmentResponse.json()) as Equipment[],
      team: (await teamResponse.json()) as TeamMember[],
    };
  } catch {
    return { content: {}, equipment: fallbackEquipment, team: null };
  }
}
