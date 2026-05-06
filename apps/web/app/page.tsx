import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-5xl font-semibold tracking-tight">Fragwise</h1>
      <p className="text-muted-foreground">
        Open-source fragrance discovery with an AI chatbot guide.
      </p>
      <Button disabled>Coming soon</Button>
    </main>
  );
}
