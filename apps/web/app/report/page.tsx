"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { nextReview } from "@/lib/pedagogy";

type Concept = { id: string; name: string };
type Lesson = {
  title: string;
  concepts: Concept[];
  beats: unknown[];
  final_quiz: unknown[];
  total_words: number;
  mean_groundedness: number | null;
};

const WEAK = "ohms_law";

const spring = { type: "spring" as const, stiffness: 220, damping: 26, mass: 0.7 };
const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.06 } } };
const item = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: spring },
};

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <motion.section variants={item} style={{ marginTop: 72 }}>
      <p className="t-micro dim">{label}</p>
      {children}
    </motion.section>
  );
}

function Report() {
  const lang = useSearchParams().get("lang") === "hi" ? "hi" : "en";
  const [lesson, setLesson] = useState<Lesson | null>(null);

  useEffect(() => {
    fetch("/data/lessons.json")
      .then((r) => r.json())
      .then((l: Record<string, Lesson>) => setLesson(l[lang]));
  }, [lang]);

  if (!lesson) return <main style={{ minHeight: "100vh" }} />;

  const weak = lesson.concepts.find((c) => c.id === WEAK) ?? lesson.concepts[0];
  const strong = lesson.concepts.filter((c) => c.id !== weak.id);

  const stats: [string, string][] = [
    ["Final score", "80%"],
    ["Concepts taught", String(lesson.concepts.length)],
    ["Grounded on source", lesson.mean_groundedness?.toFixed(2) ?? "-"],
    ["Lesson length", `${Math.round(lesson.total_words / 150)} min`],
  ];

  const misconceptions: [string, number][] = [
    ["ohms_law_inverse_confusion", 2],
    ["resistance_vs_resistivity", 1],
  ];

  const revision: [string, string][] = [
    [weak.name, nextReview(false, 0)],
    ...strong.map((c, n): [string, string] => [c.name, nextReview(true, n + 1)]),
  ];

  return (
    <main style={{ minHeight: "100vh", padding: "88px 8vw 160px" }}>
      <motion.div
        variants={stagger}
        initial="hidden"
        animate="show"
        style={{ maxWidth: 900 }}
      >
        <motion.p variants={item} className="t-micro accent">
          Learning report
        </motion.p>
        <motion.h1 variants={item} className="display t-hero" style={{ marginTop: 16 }}>
          {lesson.title}
        </motion.h1>

        <motion.div
          variants={stagger}
          style={{ display: "flex", gap: 64, marginTop: 64, flexWrap: "wrap" }}
        >
          {stats.map(([k, v]) => (
            <motion.div key={k} variants={item}>
              <div
                className="display"
                style={{ fontSize: 56, lineHeight: 1, fontVariantNumeric: "tabular-nums" }}
              >
                {v}
              </div>
              <div className="t-micro dim" style={{ marginTop: 12 }}>
                {k}
              </div>
            </motion.div>
          ))}
        </motion.div>

        <Section label="Needs improvement">
          <p className="display t-h1" style={{ marginTop: 12 }}>
            {weak.name}
          </p>
          <p className="t-body muted" style={{ marginTop: 14, maxWidth: 640 }}>
            You answered that current rises when resistance rises. That is the
            <span className="accent"> ohms_law_inverse_confusion </span>
            misconception. At constant voltage, current is inversely proportional to
            resistance: I = V/R. Raising R lowers I, so doubling the resistance halves
            the current rather than doubling it.
          </p>
        </Section>

        <Section label="Strong areas">
          <div style={{ marginTop: 14 }}>
            {strong.map((c) => (
              <p key={c.id} className="display t-h2" style={{ margin: "10px 0" }}>
                {c.name}
              </p>
            ))}
          </div>
        </Section>

        <Section label="Misconceptions hit">
          <div className="mono t-small muted" style={{ marginTop: 16, lineHeight: 2.2 }}>
            {misconceptions.map(([id, n]) => (
              <div key={id}>
                <span className="accent">{String(n).padStart(2, "0")}</span>
                <span className="dim">{"  ×  "}</span>
                {id}
              </div>
            ))}
          </div>
        </Section>

        <Section label="Revision schedule">
          <div className="mono t-small muted" style={{ marginTop: 16, lineHeight: 2.2 }}>
            {revision.map(([name, date]) => (
              <div key={name}>
                <span className="accent">{date}</span>
                <span className="dim">{"  ·  "}</span>
                {name}
              </div>
            ))}
          </div>
        </Section>

        <Section label="Recommended next">
          <p className="t-body" style={{ marginTop: 14, maxWidth: 640 }}>
            Revise Ohm&apos;s Law, then continue to 11.6 Resistance of a System of
            Resistors.
          </p>
        </Section>

        <motion.div variants={item} style={{ marginTop: 80 }}>
          <a
            href="/"
            className="ghost"
            style={{ display: "inline-block", textDecoration: "none" }}
          >
            Teach me something else
          </a>
        </motion.div>
      </motion.div>
    </main>
  );
}

export default function Page() {
  return (
    <Suspense fallback={<main style={{ minHeight: "100vh" }} />}>
      <Report />
    </Suspense>
  );
}
