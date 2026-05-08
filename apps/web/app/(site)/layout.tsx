import { Header } from "@/components/site/Header";
import { Footer } from "@/components/site/Footer";
import { SkipToContent } from "@/components/site/SkipToContent";

export default function SiteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <SkipToContent />
      <Header />
      <main id="main-content" className="min-h-[calc(100dvh-4rem)]">
        {children}
      </main>
      <Footer />
    </>
  );
}
