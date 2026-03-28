"use client";

import { motion } from "framer-motion";
import { useTranslations } from "@/lib/i18n";
import { VERSION_META, LAYERS } from "@/lib/constants";
import { ArrowRight, FileCode, Wrench, Box, FunctionSquare, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";

interface VersionComparisonCardsProps {
  versionA: string;
  versionB: string;
  locDelta: number;
  newTools: string[];
  newClasses: string[];
  newFunctions: string[];
}

const STAT_CARD_COLORS = {
  tools: "from-blue-500 to-cyan-500",
  classes: "from-purple-500 to-pink-500",
  functions: "from-emerald-500 to-teal-500",
  loc: "from-amber-500 to-orange-500",
};

export function VersionComparisonCards({
  versionA,
  versionB,
  locDelta,
  newTools,
  newClasses,
  newFunctions,
}: VersionComparisonCardsProps) {
  const t = useTranslations("compare");
  const metaA = VERSION_META[versionA];
  const metaB = VERSION_META[versionB];

  const stats = [
    {
      label: "LOC Change",
      value: locDelta > 0 ? `+${locDelta}` : locDelta,
      icon: TrendingUp,
      color: STAT_CARD_COLORS.loc,
      description: `${locDelta > 0 ? "Added" : "Removed"} ${Math.abs(locDelta)} lines`,
    },
    {
      label: "New Tools",
      value: newTools.length,
      icon: Wrench,
      color: STAT_CARD_COLORS.tools,
      description: newTools.length > 0 ? newTools.join(", ") : "No new tools",
    },
    {
      label: "New Classes",
      value: newClasses.length,
      icon: Box,
      color: STAT_CARD_COLORS.classes,
      description: newClasses.length > 0 ? newClasses.join(", ") : "No new classes",
    },
    {
      label: "New Functions",
      value: newFunctions.length,
      icon: FunctionSquare,
      color: STAT_CARD_COLORS.functions,
      description: newFunctions.length > 0 ? newFunctions.join(", ") : "No new functions",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Version headers */}
      <div className="flex items-center justify-between">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="text-center"
        >
          <div className="rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 px-4 py-2 text-white shadow-md">
            <div className="text-2xl font-bold">{versionA}</div>
            <div className="text-xs opacity-90">{metaA?.title}</div>
          </div>
        </motion.div>

        <ArrowRight size={24} className="text-[var(--color-text-secondary)]" />

        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="text-center"
        >
          <div className="rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-600 px-4 py-2 text-white shadow-md">
            <div className="text-2xl font-bold">{versionB}</div>
            <div className="text-xs opacity-90">{metaB?.title}</div>
          </div>
        </motion.div>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, index) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            whileHover={{ y: -4, scale: 1.02 }}
            className={cn(
              "relative overflow-hidden rounded-xl bg-gradient-to-br p-5 text-white shadow-lg",
              stat.color
            )}
          >
            {/* Background pattern */}
            <div className="absolute right-0 top-0 h-20 w-20 opacity-10">
              <stat.icon size={80} />
            </div>

            {/* Content */}
            <div className="relative">
              <div className="flex items-center gap-2">
                <stat.icon size={18} />
                <span className="text-sm font-medium opacity-90">{stat.label}</span>
              </div>
              <div className="mt-2 text-3xl font-bold">{stat.value}</div>
              <div className="mt-1 text-xs opacity-75">{stat.description}</div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Layer progression indicator */}
      {metaA && metaB && metaA.layer !== metaB.layer && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-4"
        >
          <div className="flex items-center gap-3">
            <FileCode size={20} className="text-[var(--color-text-secondary)]" />
            <div>
              <div className="text-sm font-medium">Architectural Layer Change</div>
              <div className="mt-1 flex items-center gap-2 text-xs text-[var(--color-text-secondary)]">
                <span className="font-medium">{LAYERS.find(l => l.id === metaA.layer)?.label}</span>
                <ArrowRight size={12} />
                <span className="font-medium">{LAYERS.find(l => l.id === metaB.layer)?.label}</span>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}
