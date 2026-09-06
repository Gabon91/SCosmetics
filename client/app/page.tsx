import { getTreatments } from "./lib/treatments";
import { AboutSection } from "@/components/home/AboutSection";
import { ContactSection } from "@/components/home/ContactSection";
import { Footer } from "@/components/home/Footer";
import { Header } from "@/components/home/Header";
import { HeroSection } from "@/components/home/HeroSection";
import { TeamSection } from "@/components/home/TeamSection";
import { TreatmentsSection } from "@/components/home/TreatmentsSection";

export default async function Home() {
  const treatments = await getTreatments();

  return (
    <main>
      <Header />
      <HeroSection />
      <AboutSection />
      <TreatmentsSection treatments={treatments} />
      <TeamSection />
      <ContactSection />
      <Footer />
    </main>
  );
}
