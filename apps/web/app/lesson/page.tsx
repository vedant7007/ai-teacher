"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  bktUpdate, grade, nextReview, P_INIT, type Graded, type Misconception,
} from "@/lib/pedagogy";

type Word = { w: string; at: number; d: number };
type Beat = {
  id: string; intent: string; concept_id: string | null; kind: string;
  reason: string; script: string; language: string; analogy_family: string | null;
  groundedness: number | null; duration_ms: number; words: Word[];
  citations: { page_start: number; page_end: number; section: string }[];
  checkpoint: null | {
    id: string; prompt: string; concept_id: string; answer_key: string;
    rubric: string[]; options: string[] | null; targets_misconception: string | null;
  };
};
type Lesson = {
  title: string; language: string; beats: Beat[];
  concepts: { id: string; name: string }[];
  final_quiz: { id: string; prompt: string; answer_key: string; rubric: string[] }[];
  mean_groundedness: number | null;
};

const SPRING = { type: "spring" as const, stiffness: 220, damping: 26 };

function Stage() {
  const router = useRouter();
  const params = useSearchParams();
  const lang = params.get("lang") === "hi" ? "hi" : "en";

  const [lessons, setLessons] = useState<Record<string, Lesson> | null>(null);
  const [tax, setTax] = useState<Record<string, Misconception>>({});
  const [i, setI] = useState(0);
  const [ms, setMs] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [answer, setAnswer] = useState("");
  const [graded, setGraded] = useState<Graded | null>(null);
  const [injected, setInjected] = useState<Record<number, Graded>>({});
  const [mastery, setMastery] = useState<Record<string, number>>({});
  const [flash, setFlash] = useState<string | null>(null);
  const [trace, setTrace] = useState<string[]>([]);
  const [traceOpen, setTraceOpen] = useState(true);
  const [reqs, setReqs] = useState({ spent: 16, saved: 16 });

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const frameRef = useRef<HTMLIFrameElement | null>(null);
  const raf = useRef<number | null>(null);

  useEffect(() => {
    Promise.all([
      fetch("/data/lessons.json").then((r) => r.json()),
      fetch("/data/misconceptions.json").then((r) => r.json()),
    ]).then(([l, t]) => {
      setLessons(l);
      setTax(t);
      const m: Record<string, number> = {};
      (l[lang] as Lesson).concepts.forEach((c) => (m[c.id] = P_INIT));
      setMastery(m);
      setTrace([
        "understand  level=beginner language=" + (lang === "hi" ? "hi-IN" : "en-IN"),
        "plan        concepts=" + (l[lang] as Lesson).concepts.length +
          " beats=" + (l[lang] as Lesson).beats.length,
      ]);
    });
  }, [lang]);

  const lesson = lessons?.[lang];
  const beat = lesson?.beats[i];
  const atCheck = !!beat?.checkpoint && !graded;

  // Drive the slide iframe from the audio clock.
  const tick = useCallback(() => {
    const a = audioRef.current;
    if (!a) return;
    const t = a.currentTime * 1000;
    setMs(t);
    const w = frameRef.current?.contentWindow as unknown as { seek?: (n: number) => void };
    w?.seek?.(t);
    raf.current = requestAnimationFrame(tick);
  }, []);

  useEffect(() => {
    if (playing) raf.current = requestAnimationFrame(tick);
    return () => { if (raf.current) cancelAnimationFrame(raf.current); };
  }, [playing, tick, i]);

  const play = () => { audioRef.current?.play(); setPlaying(true); };

  const onEnded = () => {
    setPlaying(false);
    if (beat?.checkpoint) return;      // never render past an unanswered checkpoint
    next();
  };

  const next = () => {
    if (!lesson) return;
    if (i + 1 >= lesson.beats.length) { router.push(`/report?lang=${lang}`); return; }
    setI(i + 1); setGraded(null); setAnswer(""); setMs(0);
    setTimeout(() => { audioRef.current?.play(); setPlaying(true); }, 120);
  };

  const submit = (text: string) => {
    if (!beat?.checkpoint || !lesson) return;
    const cid = beat.checkpoint.concept_id || beat.concept_id || "unknown";
    const p = mastery[cid] ?? P_INIT;
    const used = new Set(
      lesson.beats.filter((b) => b.concept_id === cid && b.analogy_family)
        .map((b) => b.analogy_family as string),
    );
    const g = grade(text, beat.checkpoint, tax, used, p, 0, false);
    const after = bktUpdate(p, g.correct);

    setGraded(g);
    setInjected({ ...injected, [i]: g });
    setMastery({ ...mastery, [cid]: after });
    setFlash(g.correct ? "up" : "down");
    setTimeout(() => setFlash(null), 900);
    setTrace((t) => [
      ...t,
      `question    beat=${beat.id} concept=${cid}`,
      `evaluate    correct=${g.correct} misconception=${g.misconceptionId ?? "none"} matched_by=${g.matchedBy}`,
      `adapt       action=${g.action} family=${g.reexplanation?.family ?? "-"} mastery ${p.toFixed(3)} -> ${after.toFixed(3)}`,
      g.correct ? "" : `revision    ${cid} due ${nextReview(false, 0)}`,
    ].filter(Boolean));
    setReqs((r) => ({ ...r, saved: r.saved + 1 }));
  };

  if (!lesson || !beat) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <p className="t-micro dim">Preparing the lesson…</p>
      </main>
    );
  }

  const progress = ((i + 1) / lesson.beats.length) * 100;
  const spokenIdx = beat.words.findIndex((w) => ms >= w.at && ms < w.at + w.d);

  return (
    <main style={{ minHeight: "100vh", position: "relative", overflow: "hidden" }}>
      {/* concept rail, top edge, not a widget */}
      <div className="rail" style={{ position: "fixed", top: 0, left: 0, right: 0, zIndex: 40 }}>
        <motion.div className="rail-fill" animate={{ width: `${progress}%` }} transition={SPRING} />
      </div>

      <div style={{ display: "flex", height: "100vh" }}>
        <section style={{ flex: 1, position: "relative", display: "flex",
                          flexDirection: "column", minWidth: 0 }}>
          <header style={{ padding: "22px 40px 0", display: "flex",
                           justifyContent: "space-between", alignItems: "baseline" }}>
            <span className="t-micro dim">
              {beat.intent} · beat {i + 1} of {lesson.beats.length}
            </span>
            <span className="t-micro dim">{lesson.title}</span>
          </header>

          {/* the slide, full bleed, no card */}
          <div style={{ flex: 1, position: "relative", display: "grid", placeItems: "center" }}>
            <div className="avatar-glow" />
            <AnimatePresence mode="wait">
              <motion.div
                key={beat.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.32 }}
                style={{ width: "100%", display: "grid", placeItems: "center" }}
              >
                <iframe
                  ref={frameRef}
                  className="stage-frame"
                  src={`/slides/${lang}_${beat.id}.html`}
                  width={1280}
                  height={720}
                  style={{ width: "min(100%, 1280px)", aspectRatio: "16/9", height: "auto" }}
                  title={`slide ${beat.id}`}
                />
              </motion.div>
            </AnimatePresence>
          </div>

          {/* controls */}
          <div style={{ padding: "0 40px 26px", display: "flex", gap: 12, alignItems: "center" }}>
            {!playing && !atCheck && (
              <button className="cta" onClick={play}>
                {ms > 0 ? "Resume" : "Play the lesson"}
              </button>
            )}
            {playing && <span className="t-micro accent">● teaching</span>}
            {beat.groundedness != null && (
              <span className="t-small dim mono">
                grounded {beat.groundedness.toFixed(2)}
              </span>
            )}
            {beat.citations[0] && (
              <span className="t-small dim">
                source · p{beat.citations[0].page_start} {beat.citations[0].section.slice(0, 28)}
              </span>
            )}
            <span style={{ flex: 1 }} />
            <button className="ghost" onClick={() => setTraceOpen(!traceOpen)}>
              {traceOpen ? "Hide" : "Show"} trace
            </button>
          </div>

          <audio
            ref={audioRef}
            src={`/audio/${lang}_${beat.id}.mp3`}
            onEnded={onEnded}
            preload="auto"
          />
        </section>

        {/* trace drawer */}
        <AnimatePresence>
          {traceOpen && (
            <motion.aside
              className="glass"
              initial={{ x: 340, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 340, opacity: 0 }}
              transition={SPRING}
              style={{ width: 340, padding: "26px 22px", overflowY: "auto" }}
            >
              <p className="t-micro dim">Learner model</p>
              <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 14 }}>
                {lesson.concepts.map((c) => {
                  const v = mastery[c.id] ?? P_INIT;
                  return (
                    <div key={c.id}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span className="t-small">{c.name}</span>
                        <motion.span
                          className="t-small mono"
                          animate={{ color: flash === "down" ? "var(--bad)" : "var(--muted)" }}
                        >
                          {v.toFixed(2)}
                        </motion.span>
                      </div>
                      <div className="rail" style={{ marginTop: 6 }}>
                        <motion.div
                          className="rail-fill"
                          animate={{
                            width: `${v * 100}%`,
                            background: flash === "down" ? "var(--bad)" : "var(--accent)",
                          }}
                          transition={SPRING}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>

              <p className="t-micro dim" style={{ marginTop: 30 }}>Why this visual</p>
              <p className="t-small muted" style={{ marginTop: 8 }}>{beat.reason}</p>

              <p className="t-micro dim" style={{ marginTop: 30 }}>Request budget</p>
              <div className="mono t-small muted" style={{ marginTop: 8, lineHeight: 1.9 }}>
                <div>gemini spent &nbsp;{reqs.spent} / 1500</div>
                <div>saved by cache {reqs.saved}</div>
                <div>this lesson &nbsp;&nbsp;1 request</div>
                <div>grading &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;0 (deterministic)</div>
              </div>

              <p className="t-micro dim" style={{ marginTop: 30 }}>Trace</p>
              <div className="mono" style={{ marginTop: 8, fontSize: 10.5, lineHeight: 1.85 }}>
                {trace.map((t, n) => (
                  <motion.div
                    key={n}
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    className={t.startsWith("adapt") ? "accent" : "dim"}
                  >
                    {t}
                  </motion.div>
                ))}
              </div>
            </motion.aside>
          )}
        </AnimatePresence>
      </div>

      {/* checkpoint overlay */}
      <AnimatePresence>
        {beat.checkpoint && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            style={{
              position: "fixed", inset: 0, zIndex: 60, display: "grid",
              placeItems: "center", background: "rgba(10,10,11,.86)",
              backdropFilter: "blur(10px)",
            }}
          >
            <motion.div
              initial={{ y: 24, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
              transition={SPRING}
              style={{ width: "min(720px, 88vw)" }}
            >
              <p className="t-micro accent">Checkpoint</p>
              <h2 className="display t-h1" style={{ marginTop: 14 }}>
                {beat.checkpoint.prompt}
              </h2>

              {!graded && (
                <>
                  <input
                    className="field"
                    style={{ marginTop: 28 }}
                    placeholder="Type your answer…"
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && answer.trim() && submit(answer)}
                    autoFocus
                  />
                  <div style={{ marginTop: 26, display: "flex", gap: 10, flexWrap: "wrap" }}>
                    <button className="cta" disabled={!answer.trim()} onClick={() => submit(answer)}>
                      Answer
                    </button>
                    {/* seeded so the demo path is one click, not typing */}
                    <button className="ghost" onClick={() => submit("Current increases.")}>
                      Answer wrongly (demo)
                    </button>
                    <button
                      className="ghost"
                      onClick={() => submit(beat.checkpoint!.answer_key)}
                    >
                      Answer correctly (demo)
                    </button>
                  </div>
                </>
              )}

              {graded && (
                <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
                            transition={SPRING} style={{ marginTop: 28 }}>
                  <p className="t-micro" style={{ color: graded.correct ? "var(--accent)" : "var(--bad)" }}>
                    {graded.correct ? "Correct" : `Misconception · ${graded.misconceptionId}`}
                  </p>
                  <p className="t-body" style={{ marginTop: 12 }}>{graded.feedback}</p>
                  {graded.reexplanation && (
                    <>
                      <p className="t-micro dim" style={{ marginTop: 24 }}>
                        Re-explaining with a different analogy · {graded.reexplanation.family}
                      </p>
                      <p className="t-body muted" style={{ marginTop: 10 }}>
                        {graded.reexplanation.script}
                      </p>
                    </>
                  )}
                  {graded.newQuestion && (
                    <>
                      <p className="t-micro dim" style={{ marginTop: 24 }}>New diagnostic question</p>
                      <p className="t-body" style={{ marginTop: 10 }}>{graded.newQuestion.prompt}</p>
                    </>
                  )}
                  <button className="cta" style={{ marginTop: 30 }} onClick={next}>
                    Continue
                  </button>
                </motion.div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}

export default function Page() {
  return (
    <Suspense fallback={<main style={{ minHeight: "100vh" }} />}>
      <Stage />
    </Suspense>
  );
}
