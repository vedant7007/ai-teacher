"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { nextReview } from "@/lib/pedagogy";

function Report() {
  const lang = useSearchParams().get("lang") === "hi" ? "hi" : "en";
  const [lesson, setLesson] = useState<any>(null);

  useEffect(() => {
    fetch("/data/lessons.json").then((r) => r.json()).then((l) => setLesson(l[lang]));
  }, [lang]);

  if (!lesson) return <main style={{ minHeight: "100vh" }} />;

  const rows = [
    ["Score", "80%"],
    ["Concepts taught", String(lesson.concepts.length)],
    ["Grounded on source", lesson.mean_groundedness?.toFixed(2) ?? "-"],
    ["Lesson length", `${Math.round(lesson.total_words / 150)} min`],
  ];

  return (
    <main style={{ minHeight: "100vh", padding: "80px 8vw" }}>
      <motion.div
        initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        style={{ maxWidth: 860 }}
      >
        <p className="t-micro accent">Learning report</p>
        <h1 className="display t-hero" style={{ marginTop: 16 }}>{lesson.title}</h1>

        <div style={{ display: "flex", gap: 56, marginTop: 56, flexWrap: "wrap" }}>
          {rows.map(([k, v], n) => (
            <motion.div key={k}
              initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.08 * n, duration: 0.4 }}>
              <div className="display" style={{ fontSize: 52, lineHeight: 1 }}>{v}</div>
              <div className="t-micro dim" style={{ marginTop: 10 }}>{k}</div>
            </motion.div>
          ))}
        </div>

        <section style={{ marginTop: 72 }}>
          <p className="t-micro dim">Needs improvement</p>
          <p className="display t-h1" style={{ marginTop: 12 }}>Ohm's Law</p>
          <p className="t-body muted" style={{ marginTop: 12, maxWidth: 620 }}>
            You answered that current rises when resistance rises. That is the
            <span className="accent"> ohms_law_inverse_confusion </span>
            misconception: at constant voltage current is inversely proportional
            to resistance, so I = V/R means doubling R halves I.
          </p>
        </section>

        <section style={{ marginTop: 56 }}>
          <p className="t-micro dim">Revision schedule</p>
          <div className="mono t-body" style={{ marginTop: 14, lineHeight: 2.1 }}>
            <div>Ohm's Law <span className="dim">· review</span> {nextReview(false, 0)}</div>
            {lesson.concepts.slice(1).map((c: any, n: number) => (
              <div key={c.id}>{c.name} <span className="dim">· review</span> {nextReview(true, n + 1)}</div>
            ))}
          </div>
        </section>

        <section style={{ marginTop: 56 }}>
          <p className="t-micro dim">Recommended next</p>
          <p className="t-body" style={{ marginTop: 12 }}>
            Revise Ohm's Law, then continue to 11.6 Resistance of a System of Resistors.
          </p>
        </section>

        <a href="/" className="ghost" style={{ display: "inline-block", marginTop: 64, textDecoration: "none" }}>
          Teach me something else
        </a>
      </motion.div>
    </main>
  );
}

export default function Page() {
  return <Suspense fallback={<main style={{ minHeight: "100vh" }} />}><Report /></Suspense>;
}
