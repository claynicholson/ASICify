import { Nav } from "@/components/nav";
import { Footer } from "@/components/footer";
import { Hero } from "@/components/landing/hero";
import { HowItWorks } from "@/components/landing/how-it-works";
import { Differentiators } from "@/components/landing/differentiators";
import { VsClosedSilicon } from "@/components/landing/vs-closed-silicon";
import { CodeSnippet } from "@/components/landing/code-snippet";

export default function HomePage() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <HowItWorks />
        <Differentiators />
        <VsClosedSilicon />
        <CodeSnippet />
      </main>
      <Footer />
    </>
  );
}
