"use client";

import { useEffect, useState } from "react";
import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";

type ThemeName = "light" | "dark" | "system";

const ORDER: ThemeName[] = ["light", "dark", "system"];

const NEXT: Record<ThemeName, ThemeName> = {
  light: "dark",
  dark: "system",
  system: "light",
};

const LABEL: Record<ThemeName, string> = {
  light: "Switch theme: currently light",
  dark: "Switch theme: currently dark",
  system: "Switch theme: currently system",
};

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // next-themes returns undefined on first render until it reads
  // localStorage (avoids hydration mismatch). Render a stable
  // placeholder until mounted to keep aria-label deterministic.
  // This is the canonical next-themes mount-guard pattern; the
  // synchronous setState here runs exactly once after first paint.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  const current: ThemeName = mounted
    ? ((ORDER.includes(theme as ThemeName) ? theme : "system") as ThemeName)
    : "light";

  const Icon = current === "light" ? Sun : current === "dark" ? Moon : Monitor;

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      aria-label={LABEL[current]}
      onClick={() => setTheme(NEXT[current])}
      // Keep button visible-but-inert before mount (hydration parity)
      suppressHydrationWarning
    >
      <Icon className="size-4" aria-hidden />
    </Button>
  );
}
