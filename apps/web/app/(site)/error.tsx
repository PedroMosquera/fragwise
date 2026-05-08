"use client";
import { useEffect } from "react";
import { Container } from "@/components/site/Container";
import { Button } from "@/components/ui/button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);
  return (
    <Container className="py-24 text-center">
      <h1 className="font-display text-4xl">Something went wrong.</h1>
      <p className="mt-4 text-muted-foreground">
        We logged the error. Try again, or browse the catalogue.
      </p>
      <Button className="mt-8" onClick={reset}>
        Try again
      </Button>
    </Container>
  );
}
