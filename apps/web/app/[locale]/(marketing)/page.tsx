import { MarketingFooter, MarketingNav } from "@/components/marketing";
import { Faq } from "@/components/marketing/faq";
import {
  AnalyticsPreview,
  DeepDives,
  FeatureCards,
  FinalCta,
  HeroSection,
  HowItWorks,
  StatsBand,
  Testimonials,
  UseCases,
} from "@/components/marketing/sections";

export default function Home() {
  return (
    <>
      <MarketingNav />
      <HeroSection />
      <StatsBand />
      <FeatureCards />
      <DeepDives />
      <AnalyticsPreview />
      <UseCases />
      <HowItWorks />
      <Testimonials />
      <Faq />
      <FinalCta />
      <MarketingFooter />
    </>
  );
}
