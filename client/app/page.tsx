import { getTreatments } from "./lib/treatments";
import { getSiteData } from "./lib/site";
import { AboutSection } from "@/components/home/AboutSection";
import { ContactSection } from "@/components/home/ContactSection";
import { Footer } from "@/components/home/Footer";
import { EquipmentSection } from "@/components/home/EquipmentSection";
import { SiteHeader } from "@/components/shared/SiteHeader";
import { HeroSection } from "@/components/home/HeroSection";
import { TeamSection } from "@/components/home/TeamSection";
import { TreatmentsSection } from "@/components/home/TreatmentsSection";

export default async function Home() {
  const [treatments, site] = await Promise.all([getTreatments(), getSiteData()]);

  return (
    <main>
      <SiteHeader />
      <HeroSection content={site.content} />
      <AboutSection content={site.content} />
      <TreatmentsSection treatments={treatments} />
      <EquipmentSection content={site.content} equipment={site.equipment} />
      <TeamSection team={site.team} />
      <ContactSection content={site.content} />
      <Footer />
    </main>
  );
}
