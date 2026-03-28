"use client";

import { ReactNode } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface FeatureCardProps {
  icon: ReactNode;
  title: string;
  description: string;
  gradient: string;
  delay?: number;
}

export function FeatureCard({
  icon,
  title,
  description,
  gradient,
  delay = 0,
}: FeatureCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      whileHover={{ y: -8, transition: { duration: 0.2 } }}
      className="group relative overflow-hidden rounded-2xl border border-[var(--color-border)] bg-gradient-to-br from-[var(--color-bg)] to-[var(--color-bg-secondary)] p-6 shadow-sm transition-all hover:shadow-xl"
    >
      {/* Animated gradient background */}
      <div
        className={cn(
          "absolute inset-0 bg-gradient-to-br opacity-0 transition-opacity group-hover:opacity-5",
          gradient
        )}
      />

      {/* Icon */}
      <div
        className={cn(
          "mb-4 inline-flex rounded-xl bg-gradient-to-br p-3 text-white shadow-lg",
          gradient
        )}
      >
        {icon}
      </div>

      {/* Content */}
      <h3 className="text-base font-semibold">{title}</h3>
      <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
        {description}
      </p>
    </motion.div>
  );
}
