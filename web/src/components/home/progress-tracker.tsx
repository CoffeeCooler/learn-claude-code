"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { useLocale, useTranslations } from "@/lib/i18n";
import { LEARNING_PATH, VERSION_META } from "@/lib/constants";
import { CheckCircle2, Circle, Play } from "lucide-react";
import { cn } from "@/lib/utils";

const PROGRESS_STORAGE_KEY = "learn-claude-code-progress";

interface ProgressData {
  completedVersions: string[];
  lastVisited: string | null;
  lastVisitedAt: number | null;
}

export function ProgressTracker() {
  const locale = useLocale();
  const t = useTranslations("home");
  const [progress, setProgress] = useState<ProgressData>({
    completedVersions: [],
    lastVisited: null,
    lastVisitedAt: null,
  });

  // Load progress from localStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem(PROGRESS_STORAGE_KEY);
      if (stored) {
        setProgress(JSON.parse(stored));
      }
    }
  }, []);

  // Save progress when it changes
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem(PROGRESS_STORAGE_KEY, JSON.stringify(progress));
    }
  }, [progress]);

  const completedCount = progress.completedVersions.length;
  const totalCount = LEARNING_PATH.length;
  const progressPercent = Math.round((completedCount / totalCount) * 100);

  // Mark a version as completed
  const markCompleted = (versionId: string) => {
    setProgress((prev) => ({
      ...prev,
      completedVersions: prev.completedVersions.includes(versionId)
        ? prev.completedVersions
        : [...prev.completedVersions, versionId],
      lastVisited: versionId,
      lastVisitedAt: Date.now(),
    }));
  };

  // Reset progress
  const resetProgress = () => {
    setProgress({
      completedVersions: [],
      lastVisited: null,
      lastVisitedAt: null,
    });
  };

  return (
    <div className="rounded-2xl border border-[var(--color-border)] bg-gradient-to-br from-[var(--color-bg)] to-[var(--color-bg-secondary)] p-6 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-semibold">{t("your_progress") || "Your Progress"}</h3>
        {completedCount > 0 && (
          <button
            onClick={resetProgress}
            className="text-xs text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors"
          >
            {t("reset") || "Reset"}
          </button>
        )}
      </div>

      {/* Progress bar */}
      <div className="mb-6">
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="text-[var(--color-text-secondary)]">
            {completedCount} of {totalCount} {t("completed") || "completed"}
          </span>
          <span className="font-medium">{progressPercent}%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-[var(--color-bg-secondary)]">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${progressPercent}%` }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-emerald-500"
          />
        </div>
      </div>

      {/* Version checklist */}
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {LEARNING_PATH.map((versionId, index) => {
          const isCompleted = progress.completedVersions.includes(versionId);
          const isLastVisited = progress.lastVisited === versionId;
          const meta = VERSION_META[versionId];

          return (
            <motion.button
              key={versionId}
              onClick={() => markCompleted(versionId)}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.05 }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className={cn(
                "flex items-center gap-2 rounded-lg border p-3 text-left transition-all",
                isCompleted
                  ? "border-emerald-500/30 bg-emerald-500/5 hover:border-emerald-500/50"
                  : "border-[var(--color-border)] hover:border-[var(--color-text-secondary)]",
                isLastVisited && !isCompleted && "border-blue-500/30 bg-blue-500/5"
              )}
            >
              {isCompleted ? (
                <CheckCircle2 size={16} className="text-emerald-500" />
              ) : (
                <Circle size={16} className="text-[var(--color-text-secondary)]" />
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-medium">{versionId}</span>
                  {isLastVisited && !isCompleted && (
                    <Play size={10} className="text-blue-500" />
                  )}
                </div>
                <p className="truncate text-xs text-[var(--color-text-secondary)]">
                  {t(versionId) || meta?.title}
                </p>
              </div>
            </motion.button>
          );
        })}
      </div>

      {/* Quick stats */}
      <div className="mt-6 grid grid-cols-3 gap-4 rounded-lg bg-[var(--color-bg-secondary)] p-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-500">
            {completedCount}
          </div>
          <div className="text-xs text-[var(--color-text-secondary)]">
            {t("completed") || "Completed"}
          </div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-purple-500">
            {totalCount - completedCount}
          </div>
          <div className="text-xs text-[var(--color-text-secondary)]">
            {t("remaining") || "Remaining"}
          </div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-emerald-500">
            {progressPercent}%
          </div>
          <div className="text-xs text-[var(--color-text-secondary)]">
            {t("progress") || "Progress"}
          </div>
        </div>
      </div>
    </div>
  );
}
