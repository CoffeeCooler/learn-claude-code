"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "@/lib/i18n";
import { LAYERS } from "@/lib/constants";

const LAYER_COLORS: Record<string, string> = {
  tools: "#3B82F6",
  planning: "#10B981",
  memory: "#8B5CF6",
  concurrency: "#F59E0B",
  collaboration: "#EF4444",
};

export function VerticalAxis() {
  const homeT = useTranslations("home");
  const [active, setActive] = useState<string | null>(null);

  const items = [
    { id: "core-pattern", label: homeT("core_pattern") || "Core Pattern" },
    // Knowledge Graph, Progress sections removed per request
    { id: "message-flow", label: homeT("message_flow") || "Message Growth" },
    { id: "learning-path", label: homeT("learning_path") || "Learning Path" },
    { id: "layers", label: homeT("layers_title") || "Architectural Layers" },
  ];

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActive(entry.target.id || null);
          }
        });
      },
      { root: null, rootMargin: "-30% 0px -50% 0px", threshold: 0.1 }
    );

    items.forEach((it) => {
      const el = document.getElementById(it.id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [items]);

  return (
    <nav className="hidden md:flex fixed left-6 top-24 z-50 h-[60vh] flex-col items-start gap-4">
      {/* vertical line */}
      <div className="absolute left-6 top-0 h-full w-px bg-[var(--color-border)] opacity-30" />

      <ul className="relative z-10 flex flex-col items-start gap-6">
        {items.map((it) => {
          const isActive = active === it.id;
          return (
            <li key={it.id} className="flex items-center gap-3">
              <a href={`#${it.id}`} className={`flex items-center gap-2 text-xs transition-colors ${isActive ? 'text-[var(--color-text)] font-semibold' : 'text-[var(--color-text-secondary)] hover:text-[var(--color-text)]'}`}>
                <span className={`h-2 w-2 rounded-full ${isActive ? 'bg-blue-500' : 'bg-[var(--color-border)]'}`} />
                <span>{it.label}</span>
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
