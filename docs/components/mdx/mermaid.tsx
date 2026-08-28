"use client";

import React, { useEffect, useState, useId } from "react";
import mermaid from "mermaid";
import { useTheme } from "next-themes";
import { CodeBlock, Pre } from "fumadocs-ui/components/codeblock";

mermaid.initialize({
  startOnLoad: false,
  securityLevel: "strict",
});

export function Mermaid({ chart }: { chart: string }) {
  const { resolvedTheme } = useTheme();
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [mounted, setMounted] = useState(false);
  const [isRendering, setIsRendering] = useState(true);
  const id = useId().replace(/:/g, "");

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;

    let isMounted = true;
    setIsRendering(true);
    setError(null);
    setSvg(null);

    const renderChart = async () => {
      try {
        // Re-initialize theme when it changes
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: "strict",
          theme: resolvedTheme === "dark" ? "dark" : "default",
        });

        const result = await mermaid.render(`mermaid-${id}`, chart);

        if (isMounted) {
          setSvg(result.svg);
          setIsRendering(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err : new Error(String(err)));
          setSvg(null);
          setIsRendering(false);
          console.error("Mermaid render error:", err);
        }
      }
    };

    renderChart();

    return () => {
      isMounted = false;
    };
  }, [chart, resolvedTheme, mounted, id]);

  if (!mounted || isRendering) {
    return (
      <div
        className="flex justify-center my-6 min-h-[100px] border border-dashed rounded p-4 text-sm text-muted-foreground animate-pulse"
        role="status"
      >
        Loading diagram...
      </div>
    );
  }

  if (error) {
    return (
      <div className="my-6">
        <div className="mb-2 text-sm text-red-500 font-semibold flex items-center gap-2">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
          Mermaid Render Error
        </div>
        <CodeBlock title="Mermaid (Fallback)">
          <Pre>{chart}</Pre>
        </CodeBlock>
      </div>
    );
  }

  if (!svg) return null;

  return (
    <div
      className="mermaid-wrapper my-6 flex justify-center"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
