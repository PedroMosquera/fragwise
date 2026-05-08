import type { Metadata, Viewport } from "next";
import { Fraunces, Manrope, JetBrains_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

// Context7-verified: next/font/google subsets/variable/display API
// for Next.js 16. latin-ext is included so glossary terms with
// diacritics ("Fougère") render without fallback.
const fraunces = Fraunces({
  subsets: ["latin", "latin-ext"],
  variable: "--font-display",
  display: "swap",
  weight: ["400", "500", "600"],
});

const manrope = Manrope({
  subsets: ["latin", "latin-ext"],
  variable: "--font-sans",
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Fragwise",
  description: "Open-source fragrance discovery with an AI chatbot guide.",
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? "https://fragwise.app",
  ),
};

// R3 fix C4: only `viewport.colorScheme` should emit the meta tag.
// The previous design also set `metadata.other["color-scheme"]`,
// producing a duplicate `<meta name="color-scheme">`. Drop the
// metadata.other path; rely on viewport.colorScheme alone (Next.js
// 14+). Pair with `color-scheme: light` in tokens.css for the
// CSS-side declaration. ADR-0037: 4a is light-only.
export const viewport: Viewport = {
  colorScheme: "light",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${fraunces.variable} ${manrope.variable} ${jetbrainsMono.variable} antialiased`}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          forcedTheme="light"
          enableSystem={false}
          disableTransitionOnChange
        >
          {children}
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
