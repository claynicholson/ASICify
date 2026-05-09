import { Nav } from "@/components/nav";
import { Footer } from "@/components/footer";
import { Hero } from "@/components/landing/hero";
import { HowItWorks } from "@/components/landing/how-it-works";
import { Differentiators } from "@/components/landing/differentiators";
import { CodeSnippet } from "@/components/landing/code-snippet";
import { UseCases } from "@/components/landing/use-cases";

export default function HomePage() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <HowItWorks />
        <Differentiators />
        <UseCases />
        <CodeSnippet />
      </main>
      <Footer />
    </>
  );
}
