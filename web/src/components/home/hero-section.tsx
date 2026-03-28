"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { useLocale } from "@/lib/i18n";
import { ArrowRight, Code, Brain, Zap, Layers } from "lucide-react";

interface HeroSectionProps {
  title: string;
  subtitle: string;
  startLabel: string;
}

const FEATURE_CARDS = [
  {
    icon: Code,
    title: "12 Progressive Sessions",
    description: "From a simple loop to autonomous multi-agent teams",
    color: "from-blue-500 to-cyan-500",
  },
  {
    icon: Brain,
    title: "Real Agent Patterns",
    description: "Learn the actual architecture used in production AI agents",
    color: "from-purple-500 to-pink-500",
  },
  {
    icon: Zap,
    title: "Interactive Simulators",
    description: "Watch agent loops execute step by step",
    color: "from-amber-500 to-orange-500",
  },
  {
    icon: Layers,
    title: "5 Architectural Layers",
    description: "Tools, Planning, Memory, Concurrency, Collaboration",
    color: "from-emerald-500 to-teal-500",
  },
];

export function HeroSection({ title, subtitle, startLabel }: HeroSectionProps) {
  const locale = useLocale();

  return (
    <section className="relative overflow-hidden px-2 pt-8 text-center sm:pt-20">
      {/* Animated background gradient */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute left-1/4 top-1/4 h-64 w-64 animate-pulse rounded-full bg-blue-500/10 blur-3xl" />
        <div className="absolute right-1/4 top-1/3 h-64 w-64 animate-pulse rounded-full bg-purple-500/10 blur-3xl delay-1000" />
        <div className="absolute bottom-1/4 left-1/3 h-64 w-64 animate-pulse rounded-full bg-emerald-500/10 blur-3xl delay-2000" />
      </div>

      {/* Hero content */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
      >
        <h1 className="text-3xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
          <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-emerald-600 bg-clip-text text-transparent">
            {title}
          </span>
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-base text-[var(--color-text-secondary)] sm:text-xl">
          {subtitle}
        </p>

        {/* CTA Button */}
        <motion.div
          className="mt-8"
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Link
            href={`/${locale}/timeline`}
            className="inline-flex min-h-[44px] items-center gap-2 rounded-lg bg-gradient-to-r from-blue-600 to-purple-600 px-8 py-4 text-sm font-medium text-white shadow-lg transition-all hover:shadow-xl hover:from-blue-700 hover:to-purple-700 dark:from-blue-500 dark:to-purple-500 dark:hover:from-blue-600 dark:hover:to-purple-600"
          >
            {startLabel}
            <ArrowRight size={18} />
          </Link>
        </motion.div>
      </motion.div>

      {/* Feature cards */}
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.3, ease: "easeOut" }}
        className="mx-auto mt-16 grid max-w-5xl grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        {FEATURE_CARDS.map((card, index) => (
          <motion.div
            key={card.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 * index }}
            whileHover={{ y: -4, transition: { duration: 0.2 } }}
            className="group relative overflow-hidden rounded-2xl border border-[var(--color-border)] bg-gradient-to-br from-[var(--color-bg)] to-[var(--color-bg-secondary)] p-5 shadow-sm transition-all hover:shadow-md"
          >
            {/* Gradient overlay on hover */}
            <div
              className={`absolute inset-0 bg-gradient-to-br ${card.color} opacity-0 transition-opacity group-hover:opacity-5`}
            />
            
            {/* Icon */}
            <div className={`mb-3 inline-flex rounded-lg bg-gradient-to-br ${card.color} p-2.5`}>
              <card.icon size={20} className="text-white" />
            </div>

            {/* Content */}
            <h3 className="text-sm font-semibold">{card.title}</h3>
            <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
              {card.description}
            </p>
          </motion.div>
        ))}
      </motion.div>
    </section>
  );
}
