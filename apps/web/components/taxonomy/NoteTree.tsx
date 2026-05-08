// Phase 4b: recursive note tree (ADR-0033 D-NoteTree).
//
// Top-level branches render collapsed by default. Branch headers
// contain a Link to the branch's detail page; clicking the link does
// NOT toggle the accordion (e.stopPropagation). Leaf nodes render as
// plain Links. Children render via mutually recursive `NoteBranch`.
//
// "use client" because the Accordion primitives from radix-ui require
// client-side state and the inner Link uses an onClick handler to
// stop propagation. The tree data is still fetched server-side and
// passed in as a prop.
"use client";

import Link from "next/link";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import type { NoteTreeNode } from "@/lib/api/fetchers";

export function NoteTree({ nodes }: { nodes: NoteTreeNode[] }) {
  if (nodes.length === 0) {
    return <p className="text-muted-foreground">No notes available.</p>;
  }
  return (
    <Accordion type="multiple" className="border-l border-border pl-4">
      {nodes.map((node) => (
        <NoteBranch key={node.slug} node={node} />
      ))}
    </Accordion>
  );
}

function NoteBranch({ node }: { node: NoteTreeNode }) {
  const hasChildren = !!node.children && node.children.length > 0;
  if (!hasChildren) {
    return (
      <div className="py-1">
        <Link
          href={`/notes/${node.slug}`}
          className="text-sm text-foreground hover:text-accent"
        >
          {node.name}
        </Link>
      </div>
    );
  }
  return (
    <AccordionItem value={node.slug} className="border-none">
      <AccordionTrigger className="font-display text-base hover:no-underline">
        <span className="flex items-center gap-2">
          <Link
            href={`/notes/${node.slug}`}
            className="hover:text-accent"
            onClick={(e) => e.stopPropagation()}
          >
            {node.name}
          </Link>
          <span className="font-mono text-[0.6rem] uppercase tracking-wider text-muted-foreground">
            {node.children!.length}
          </span>
        </span>
      </AccordionTrigger>
      <AccordionContent>
        <Accordion type="multiple" className="border-l border-border pl-4">
          {node.children!.map((child) => (
            <NoteBranch key={child.slug} node={child} />
          ))}
        </Accordion>
      </AccordionContent>
    </AccordionItem>
  );
}
