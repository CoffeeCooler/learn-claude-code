"use client";

import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { Copy, Check, Maximize2, Minimize2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface InteractiveCodeViewerProps {
  code: string;
  language?: string;
  filename?: string;
  highlightLines?: number[];
}

export function InteractiveCodeViewer({
  code,
  language = "python",
  filename,
  highlightLines = [],
}: InteractiveCodeViewerProps) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const lines = useMemo(() => code.split("\n"), [code]);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "relative overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] shadow-sm",
        expanded ? "fixed inset-4 z-50 m-auto max-h-[calc(100vh-2rem)]" : ""
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-4 py-2.5">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="h-3 w-3 rounded-full bg-red-500/70" />
            <div className="h-3 w-3 rounded-full bg-yellow-500/70" />
            <div className="h-3 w-3 rounded-full bg-green-500/70" />
          </div>
          {filename && (
            <span className="ml-2 text-xs font-mono text-[var(--color-text-secondary)]">
              {filename}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={handleCopy}
            className="rounded-md p-1.5 text-[var(--color-text-secondary)] hover:bg-[var(--color-bg)] hover:text-[var(--color-text)] transition-colors"
            title="Copy code"
          >
            {copied ? <Check size={14} /> : <Copy size={14} />}
          </button>
          <button
            onClick={() => setExpanded(!expanded)}
            className="rounded-md p-1.5 text-[var(--color-text-secondary)] hover:bg-[var(--color-bg)] hover:text-[var(--color-text)] transition-colors"
            title={expanded ? "Collapse" : "Expand"}
          >
            {expanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
        </div>
      </div>

      {/* Code content */}
      <div className="overflow-auto">
        <pre className="p-4 text-sm leading-relaxed">
          <code>
            {lines.map((line, index) => {
              const lineNumber = index + 1;
              const isHighlighted = highlightLines.includes(lineNumber);

              return (
                <div
                  key={index}
                  className={cn(
                    "group flex transition-colors",
                    isHighlighted
                      ? "bg-blue-500/10"
                      : "hover:bg-[var(--color-bg-secondary)]"
                  )}
                >
                  {/* Line number */}
                  <span className="select-none pr-4 text-xs text-[var(--color-text-secondary)] opacity-50 group-hover:opacity-100">
                    {lineNumber.toString().padStart(3, " ")}
                  </span>

                  {/* Line content */}
                  <span className="flex-1">{line || " "}</span>
                </div>
              );
            })}
          </code>
        </pre>
      </div>

      {/* Footer stats */}
      <div className="border-t border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-4 py-2 text-xs text-[var(--color-text-secondary)]">
        <div className="flex items-center justify-between">
          <span>{lines.length} lines</span>
          <span className="font-mono">{language}</span>
        </div>
      </div>
    </motion.div>
  );
}
