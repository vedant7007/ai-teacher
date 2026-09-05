"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion, useSpring, useTransform } from "framer-motion";

const SPRING = { stiffness: 220, damping: 26 };
const EASE = [0.22, 1, 0.36, 1] as const;

const PAGE = 1120;
const rise = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.28, ease: EASE } },
};

function Section({
  id,
  eyebrow,
  children,
  pad = 128,
}: {
  id?: string;
  eyebrow?: string;
  children: React.ReactNode;
  pad?: number;
}) {
  return (
    <section id={id} style={{ padding: `${pad}px 40px`, scrollMarginTop: 40 }}>
      <div style={{ maxWidth: PAGE, margin: "0 auto" }}>
        {eyebrow ? (
          <p className="t-micro accent" style={{ margin: "0 0 40px" }}>
            {eyebrow}
          </p>
        ) : null}
        {children}
      </div>
    </section>
  );
}

/* ---------------------------------------------------------- 4. the learner model */

const PHASES = [
  {
    v: 0.25,
    head: "Beat 3 introduces the concept",
    body: "Mastery sits at the Bayesian prior. Nothing about this student has been observed yet.",
    bad: false,
  },
  {
    v: 0.18,
    head: "Checkpoint answered wrongly",
    body: "The grader never returns a verdict of incorrect. It matches the answer against a named misconception.",
    bad: true,
  },
  {
    v: 0.18,
    head: "Re-explained with a different analogy family",
    body: "The first pass used a water-pipe analogy, so the second is forbidden from using it and switches to a mechanical one.",
    bad: true,
  },
  {
    v: 0.87,
    head: "Fresh diagnostic question answered correctly",
    body: "BKT updates, the concept is queued for SM-2 review, and the lesson resumes at the same beat rather than restarting.",
    bad: false,
  },
];

function LearnerModelDemo() {
  const [i, setI] = useState(0);
  const p = useSpring(PHASES[0].v, SPRING);
  const width = useTransform(p, (v) => `${v * 100}%`);
  const readout = useTransform(p, (v) => v.toFixed(2));

  useEffect(() => {
    const t = setInterval(() => setI((n) => (n + 1) % PHASES.length), 2400);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    p.set(PHASES[i].v);
  }, [i, p]);

  const phase = PHASES[i];

  return (
    <div style={{ maxWidth: 840 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 24 }}>
        <span className="t-micro dim">concept · ohms_law · p(known)</span>
        <motion.span className="mono accent" style={{ fontSize: 40, lineHeight: 1 }}>
          {readout}
        </motion.span>
      </div>

      <div className="rail" style={{ marginTop: 16, height: 3 }}>
        <motion.div
          className="rail-fill"
          style={{ width, background: phase.bad ? "var(--bad)" : "var(--accent)" }}
        />
      </div>

      <div style={{ marginTop: 24, minHeight: 120 }}>
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.24, ease: EASE }}
        >
          <p className="display t-h2" style={{ margin: 0 }}>
            {phase.head}
          </p>
          <p className="t-body muted" style={{ margin: "12px 0 0", maxWidth: 640 }}>
            {phase.body}
          </p>
        </motion.div>
      </div>

      <motion.p
        className="mono t-small"
        animate={{ opacity: phase.bad ? 1 : 0.3 }}
        transition={{ duration: 0.24 }}
        style={{ margin: "28px 0 0", color: phase.bad ? "var(--bad)" : "var(--dim)" }}
      >
        misconception · ohms_law_inverse_confusion
      </motion.p>
    </div>
  );
}

/* ---------------------------------------------------------- content */

const PROBLEM = [
  {
    h: "A recorded lecture cannot see you",
    p: "It plays the same forty minutes to the student who already knows this and to the one who lost the thread on slide two. Nothing it does next depends on anything you did.",
  },
  {
    h: "A chatbot waits to be asked",
    p: "It answers the question you managed to form. A student who has misunderstood something does not know which question to ask, and that is precisely the moment teaching is needed.",
  },
  {
    h: "Neither one holds a model of you",
    p: "No estimate of what you know, no record of the specific wrong idea you are carrying, no plan for when to bring it back. Teaching without that is broadcasting.",
  },
];

const STEPS = [
  { n: "01", k: "Upload", d: "Textbook, notes, or a bare topic" },
  { n: "02", k: "Plan", d: "One structured generation call" },
  { n: "03", k: "Teach", d: "Voice, avatar, synced visuals" },
  { n: "04", k: "Adapt", d: "Grade, name, re-explain" },
  { n: "05", k: "Assess", d: "Report and revision schedule" },
];

const FEATURES: [string, string][] = [
  ["RAG grounding with page citations", "Every factual claim carries a source span you can open on the page it came from."],
  ["English, Hindi, Hinglish", "Switch language mid-lesson; mastery and concept position are preserved."],
  ["Avatar and natural voice", "Word-level timings drive visemes, captions, and slide build-up from one clock."],
  ["Misconception detection", "A seeded taxonomy of named wrong models, not a verdict of incorrect."],
  ["BKT mastery tracking", "A live p(known) per concept, visible on screen and visibly steering the lesson."],
  ["SM-2 spaced repetition", "Weak concepts come back on a computed due date rather than on a whim."],
  ["Subject-aware visuals", "Equations, graphs, diagrams, concept maps, and executed code traces."],
  ["Offline local models", "The whole pipeline runs against a local Ollama model with no network at all."],
];

const ARCH = `Next.js  ──►  FastAPI
                 │
                 ├──  ingest     parse · chunk · embed
                 ├──  plan       one Gemini call  →  LessonPlan
                 ├──  speech     edge-tts         →  word timings
                 ├──  visual     five renderer kinds
                 ├──  tutor      grade  →  classify  →  adapt
                 └──  learner    BKT mastery · SM-2 review`;

const NUMBERS: [string, string][] = [
  ["1.42s", "five adaptation assertions green, offline"],
  ["63", "tests passing"],
  ["10/10", "retrieval accuracy on the seeded textbook"],
  ["0", "fabricated citations"],
  ["16", "total Gemini requests spent"],
  ["40", "beats in the demo lesson"],
];

const STACK = [
  "Next.js 16",
  "FastAPI",
  "Gemini Flash (free tier)",
  "Groq (free tier)",
  "sentence-transformers MiniLM (MIT)",
  "edge-tts (GPL-3.0)",
  "PyMuPDF (AGPL)",
  "Playwright (Apache-2.0)",
  "ffmpeg (LGPL)",
  "Ollama (MIT)",
];

/* ---------------------------------------------------------- page */

export default function Landing() {
  return (
    <main style={{ overflowX: "hidden" }}>
      {/* 1. hero */}
      <section
        style={{
          position: "relative",
          minHeight: "92vh",
          display: "flex",
          alignItems: "center",
          padding: "96px 40px",
        }}
      >
        <div
          aria-hidden
          style={{
            position: "absolute",
            inset: 0,
            pointerEvents: "none",
            background:
              "radial-gradient(760px 480px at 20% 12%, rgba(242,166,90,.10), transparent 66%)," +
              "radial-gradient(900px 620px at 90% 92%, rgba(242,166,90,.05), transparent 70%)," +
              "radial-gradient(1200px 700px at 50% 0%, rgba(237,234,228,.035), transparent 62%)",
          }}
        />
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: EASE }}
          style={{ position: "relative", width: "100%", maxWidth: PAGE, margin: "0 auto" }}
        >
          <p className="t-micro accent" style={{ margin: "0 0 32px" }}>
            Bharat Academix · AI Innovation Hackathon 2026 · Code Gauntlet
          </p>

          <h1 className="display t-hero" style={{ margin: 0, maxWidth: 940 }}>
            An AI that teaches
            <br />
            because it knows
            <br />
            what you do not.
          </h1>

          <p className="t-body muted" style={{ margin: "32px 0 0", maxWidth: 560 }}>
            It reads your textbook, plans a lesson for your level and your minutes, teaches
            it aloud with visuals, stops to question you, and names the exact misconception
            behind a wrong answer before trying again differently.
          </p>

          <div style={{ marginTop: 56, display: "flex", gap: 16, alignItems: "center" }}>
            <Link href="/learn" className="cta" style={{ textDecoration: "none" }}>
              Start a lesson
            </Link>
            <a href="#how" className="ghost" style={{ textDecoration: "none" }}>
              How it works
            </a>
          </div>
        </motion.div>
      </section>

      {/* 2. the problem */}
      <Section eyebrow="Why this is not a video, and not a chatbot">
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: 56,
          }}
        >
          {PROBLEM.map((c) => (
            <motion.div
              key={c.h}
              variants={rise}
              initial="hidden"
              whileInView="show"
              viewport={{ once: true, amount: 0.5 }}
            >
              <h3 className="display t-h2" style={{ margin: 0 }}>
                {c.h}
              </h3>
              <p className="t-body muted" style={{ margin: "16px 0 0" }}>
                {c.p}
              </p>
            </motion.div>
          ))}
        </div>
      </Section>

      {/* 3. how it works */}
      <Section id="how" eyebrow="How it works">
        <motion.div
          initial="hidden"
          whileInView="show"
          viewport={{ once: true, amount: 0.4 }}
          transition={{ staggerChildren: 0.09 }}
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: 32,
          }}
        >
          {STEPS.map((s) => (
            <motion.div key={s.n} variants={rise}>
              <div className="rail" style={{ marginBottom: 24 }}>
                <div className="rail-fill" style={{ width: "32%" }} />
              </div>
              <span className="mono t-small dim">{s.n}</span>
              <p className="display t-h2" style={{ margin: "8px 0 0" }}>
                {s.k}
              </p>
              <p className="t-small muted" style={{ margin: "8px 0 0" }}>
                {s.d}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </Section>

      {/* 4. the learner model */}
      <Section eyebrow="The differentiator · an inspectable learner model">
        <h2 className="display t-h1" style={{ margin: "0 0 16px", maxWidth: 760 }}>
          Pedagogy as state, not as prose.
        </h2>
        <p className="t-body muted" style={{ margin: "0 0 64px", maxWidth: 620 }}>
          Mastery is a number the system actually holds and actually acts on. Watch it fall
          on a wrong answer and recover only once the concept has genuinely been retaught.
        </p>
        <LearnerModelDemo />
      </Section>

      {/* 5. features */}
      <Section eyebrow="What is in it">
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(380px, 1fr))",
            columnGap: 72,
            rowGap: 40,
          }}
        >
          {FEATURES.map(([h, d]) => (
            <motion.div
              key={h}
              variants={rise}
              initial="hidden"
              whileInView="show"
              viewport={{ once: true, amount: 0.6 }}
              style={{ display: "flex", gap: 20, alignItems: "baseline" }}
            >
              <span className="mono t-small accent" style={{ opacity: 0.65 }}>
                ─
              </span>
              <div>
                <p className="t-body" style={{ margin: 0, fontWeight: 500 }}>
                  {h}
                </p>
                <p className="t-small muted" style={{ margin: "6px 0 0" }}>
                  {d}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </Section>

      {/* 6. architecture */}
      <Section eyebrow="Architecture">
        <div style={{ overflowX: "auto" }}>
          <pre
            className="mono t-small"
            style={{
              margin: 0,
              padding: "48px 0",
              color: "var(--muted)",
              lineHeight: 2,
              whiteSpace: "pre",
              borderTop: "1px solid var(--line)",
              borderBottom: "1px solid var(--line)",
            }}
          >
            {ARCH}
          </pre>
        </div>
        <p className="t-small dim" style={{ margin: "24px 0 0", maxWidth: 640 }}>
          No orchestration framework. Plain Python, five prompts, one structured generation
          per lesson, and everything else routed to a free or local model.
        </p>
      </Section>

      {/* 7. numbers */}
      <Section eyebrow="Measured">
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            columnGap: 56,
            rowGap: 64,
          }}
        >
          {NUMBERS.map(([n, d]) => (
            <motion.div
              key={d}
              variants={rise}
              initial="hidden"
              whileInView="show"
              viewport={{ once: true, amount: 0.6 }}
            >
              <p className="display accent" style={{ margin: 0, fontSize: 56, lineHeight: 1 }}>
                {n}
              </p>
              <p className="t-small muted" style={{ margin: "12px 0 0", maxWidth: 230 }}>
                {d}
              </p>
            </motion.div>
          ))}
        </div>
      </Section>

      {/* 8. stack */}
      <Section eyebrow="Built on" pad={96}>
        <p className="mono t-small dim" style={{ margin: 0, lineHeight: 2.2 }}>
          {STACK.join("   ·   ")}
        </p>
      </Section>

      {/* 9. footer */}
      <footer style={{ padding: "64px 40px 96px", borderTop: "1px solid var(--line)" }}>
        <div
          style={{
            maxWidth: PAGE,
            margin: "0 auto",
            display: "flex",
            flexWrap: "wrap",
            gap: 32,
            justifyContent: "space-between",
            alignItems: "baseline",
          }}
        >
          <div>
            <p className="t-body" style={{ margin: 0 }}>
              Team Code Gauntlet
            </p>
            <p className="t-small muted" style={{ margin: "8px 0 0" }}>
              Vedant Manmath Idlgave · Vidya Jyothi Institute of Technology (VJIT), Hyderabad
            </p>
          </div>
          <a
            className="t-small accent"
            href="https://github.com/vedant7007/ai-teacher"
            target="_blank"
            rel="noreferrer"
            style={{ textDecoration: "none" }}
          >
            github.com/vedant7007/ai-teacher
          </a>
        </div>
      </footer>
    </main>
  );
}
