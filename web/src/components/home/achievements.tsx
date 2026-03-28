"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useTranslations } from "@/lib/i18n";
import { LEARNING_PATH, LAYERS } from "@/lib/constants";
import { Trophy, Star, Zap, BookOpen, Code2, Brain, Target, Award } from "lucide-react";
import { cn } from "@/lib/utils";

const ACHIEVEMENTS = [
  {
    id: "first_step",
    title: "First Step",
    description: "Complete your first session",
    icon: Star,
    color: "from-yellow-400 to-orange-500",
    requirement: (completed: string[]) => completed.length >= 1,
  },
  {
    id: "tools_master",
    title: "Tools Master",
    description: "Complete the Tools layer (s01-s02)",
    icon: Code2,
    color: "from-blue-400 to-cyan-500",
    requirement: (completed: string[]) => 
      LEARNING_PATH.slice(0, 2).every(v => completed.includes(v)),
  },
  {
    id: "planner",
    title: "Master Planner",
    description: "Complete the Planning layer (s03-s05, s07)",
    icon: Target,
    color: "from-emerald-400 to-teal-500",
    requirement: (completed: string[]) => 
      ["s03", "s04", "s05", "s07"].every(v => completed.includes(v)),
  },
  {
    id: "memory_keeper",
    title: "Memory Keeper",
    description: "Complete the Memory layer (s06)",
    icon: Brain,
    color: "from-purple-400 to-pink-500",
    requirement: (completed: string[]) => completed.includes("s06"),
  },
  {
    id: "team_player",
    title: "Team Player",
    description: "Complete the Collaboration layer (s09-s12)",
    icon: Award,
    color: "from-red-400 to-rose-500",
    requirement: (completed: string[]) => 
      ["s09", "s10", "s11", "s12"].every(v => completed.includes(v)),
  },
  {
    id: "halfway",
    title: "Halfway There",
    description: "Complete 6 sessions",
    icon: Zap,
    color: "from-amber-400 to-orange-500",
    requirement: (completed: string[]) => completed.length >= 6,
  },
  {
    id: "scholar",
    title: "Scholar",
    description: "Complete all 12 sessions",
    icon: BookOpen,
    color: "from-indigo-400 to-purple-500",
    requirement: (completed: string[]) => completed.length >= 12,
  },
  {
    id: "legend",
    title: "Agent Legend",
    description: "Master the entire harness engineering journey",
    icon: Trophy,
    color: "from-yellow-400 via-amber-500 to-orange-600",
    requirement: (completed: string[]) => completed.length >= 12,
  },
];

const PROGRESS_STORAGE_KEY = "learn-claude-code-progress";

interface AchievementsProps {
  collapsed?: boolean;
}

export function Achievements({ collapsed = false }: AchievementsProps) {
  const t = useTranslations("home");
  const headerLabelRaw = t("achievements");
  const headerLabel = typeof headerLabelRaw === "string" ? headerLabelRaw : "Achievements";
  const subLabelRaw = t("achievements_sub");
  const subLabel = typeof subLabelRaw === "string" ? subLabelRaw : "Unlock badges as you progress";
  const [completed, setCompleted] = useState<string[]>([]);
  const [unlockedAchievements, setUnlockedAchievements] = useState<string[]>([]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem(PROGRESS_STORAGE_KEY);
      if (stored) {
        const progress = JSON.parse(stored);
        setCompleted(progress.completedVersions || []);
      }
    }
  }, []);

  useEffect(() => {
    const unlocked = ACHIEVEMENTS
      .filter(achievement => achievement.requirement(completed))
      .map(a => a.id);
    setUnlockedAchievements(unlocked);
  }, [completed]);

  if (collapsed) {
    return (
      <div className="rounded-xl border border-[var(--color-border)] bg-gradient-to-br from-[var(--color-bg)] to-[var(--color-bg-secondary)] p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Trophy size={18} className="text-amber-500" />
            <span className="text-sm font-semibold">{t("achievements") || "Achievements"}</span>
          </div>
          <span className="text-xs text-[var(--color-text-secondary)]">
            {unlockedAchievements.length} / {ACHIEVEMENTS.length}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-[var(--color-border)] bg-gradient-to-br from-[var(--color-bg)] to-[var(--color-bg-secondary)] p-6 shadow-sm">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-gradient-to-br from-amber-400 to-orange-500 p-2">
            <Trophy size={20} className="text-white" />
          </div>
          <div>
            <h3 className="text-lg font-semibold">{headerLabel}</h3>
            <p className="text-xs text-[var(--color-text-secondary)]">
              {subLabel}
            </p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-amber-500">
            {unlockedAchievements.length}
          </div>
          <div className="text-xs text-[var(--color-text-secondary)]">
            of {ACHIEVEMENTS.length} unlocked
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {ACHIEVEMENTS.map((achievement, index) => {
          const isUnlocked = unlockedAchievements.includes(achievement.id);
          const Icon = achievement.icon;

          return (
            <motion.div
              key={achievement.id}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: isUnlocked ? 1 : 0.5, scale: 1 }}
              transition={{ delay: index * 0.05 }}
              className={cn(
                "relative overflow-hidden rounded-xl border p-4 transition-all",
                isUnlocked
                  ? "border-amber-500/30 bg-gradient-to-br from-amber-500/5 to-orange-500/5"
                  : "border-[var(--color-border)] bg-[var(--color-bg)]"
              )}
            >
              {/* Background gradient for unlocked */}
              {isUnlocked && (
                <div
                  className={cn(
                    "absolute inset-0 bg-gradient-to-br opacity-10",
                    achievement.color
                  )}
                />
              )}

              <div className="relative flex items-start gap-3">
                {/* Icon */}
                <div
                  className={cn(
                    "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br",
                    isUnlocked ? achievement.color : "from-zinc-400 to-zinc-500"
                  )}
                >
                  <Icon size={18} className="text-white" />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h4 className={cn(
                      "text-sm font-semibold",
                      isUnlocked ? "text-[var(--color-text)]" : "text-[var(--color-text-secondary)]"
                    )}>
                      {t(`achievements.${achievement.id}.title`) || achievement.title}
                    </h4>
                    {isUnlocked && (
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        className="h-2 w-2 rounded-full bg-amber-500"
                      />
                    )}
                  </div>
                  <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
                    {t(`achievements.${achievement.id}.description`) || achievement.description}
                  </p>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
