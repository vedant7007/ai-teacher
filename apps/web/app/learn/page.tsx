"use client";

import { useRouter } from "next/navigation";
import { useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

/* ------------------------------------------------------------------ config */

const EXAMPLE =
  "I am a beginner. Teach me Chapter 11 in 20 minutes using simple examples. " +
  "Ask me questions during the lesson and test me at the end.";

const LIVE = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
  { code: "hinglish", label: "Hinglish" },
] as const;

// Configured in services/speech/voices.yaml with real voice ids, but outside the
// tested path. Shown rather than hidden, disabled rather than faked.
const SOON = ["తెలుగు", "தமிழ்", "मराठी", "বাংলা", "Español", "Français"];

const LEVELS = ["beginner", "intermediate", "advanced"] as const;
const MINUTES = [5, 20, 60] as const;

type LangCode = (typeof LIVE)[number]["code"];
type Level = (typeof LEVELS)[number];

// Real edge-tts voice ids. Hinglish is spoken by the Indian English voices.
const VOICES: Record<LangCode, { id: string; note: string }[]> = {
  en: [
    { id: "en-IN-NeerjaNeural", note: "Indian English, warm" },
    { id: "en-IN-PrabhatNeural", note: "Indian English, measured" },
    { id: "en-US-AriaNeural", note: "US English, bright" },
  ],
  hinglish: [
    { id: "en-IN-NeerjaNeural", note: "Indian English, warm" },
    { id: "en-IN-PrabhatNeural", note: "Indian English, measured" },
  ],
  hi: [
    { id: "hi-IN-SwaraNeural", note: "Hindi, warm" },
    { id: "hi-IN-MadhurNeural", note: "Hindi, measured" },
  ],
};

const TEACHERS = [
  { id: "asha", name: "Asha", skin: "#C68B62", hair: "#2A2118", style: "bun" },
  { id: "ravi", name: "Ravi", skin: "#8C5A3C", hair: "#171310", style: "crop" },
  { id: "mira", name: "Mira", skin: "#E3B58C", hair: "#4A2C1B", style: "bob" },
] as const;

const ACCEPT = ".pdf,.docx,.pptx,.txt";

/* ------------------------------------------------------------------- faces */

function Face({ skin, hair, style }: { skin: string; hair: string; style: string }) {
  return (
    <svg width="44" height="44" viewBox="0 0 44 44" aria-hidden="true">
      {style === "bun" && <circle cx="22" cy="6" r="4.5" fill={hair} />}
      {style === "bob" && <path d="M5 24a17 17 0 0 1 34 0v9h-6V18H11v15H5z" fill={hair} />}
      <path
        d={style === "crop" ? "M6 21a16 16 0 0 1 32 0v3H6z" : "M6 22a16 16 0 0 1 32 0v2H6z"}
        fill={hair}
      />
      <circle cx="22" cy="24" r="14" fill={skin} />
      <path d="M8 21a14 14 0 0 1 28 0c-4-5-9-7-14-7s-10 2-14 7z" fill={hair} />
      <circle cx="17" cy="24" r="1.7" fill="#141210" />
      <circle cx="27" cy="24" r="1.7" fill="#141210" />
      <path
        d="M18 30q4 3 8 0"
        stroke="#141210"
        strokeWidth="1.6"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}

/* -------------------------------------------------------------- primitives */

function Section({
  label,
  children,
  delay = 0,
}: {
  label: string;
  children: React.ReactNode;
  delay?: number;
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 260, damping: 28, delay }}
      style={{ marginTop: 48 }}
    >
      <p className="t-micro dim" style={{ marginBottom: 16 }}>
        {label}
      </p>
      {children}
    </motion.section>
  );
}

const row = { display: "flex", gap: 10, flexWrap: "wrap" as const };

/* -------------------------------------------------------------------- page */

export default function Learn() {
  const router = useRouter();

  const [file, setFile] = useState<string | null>(null);
  const [topic, setTopic] = useState("");
  const [dragging, setDragging] = useState(false);
  const [instruction, setInstruction] = useState(EXAMPLE);
  const [lang, setLang] = useState<LangCode>("en");
  const [level, setLevel] = useState<Level>("beginner");
  const [minutes, setMinutes] = useState<number>(20);
  const [teacher, setTeacher] = useState<string>(TEACHERS[0].id);
  const [voice, setVoice] = useState<string>(VOICES.en[0].id);
  const [checkpoints, setCheckpoints] = useState(true);
  const [finalQuiz, setFinalQuiz] = useState(true);
  const [playing, setPlaying] = useState<string | null>(null);

  const pickRef = useRef<HTMLInputElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  const voices = VOICES[lang];
  const ready = Boolean(file) || topic.trim().length > 1;

  const langLabel = useMemo(
    () => LIVE.find((l) => l.code === lang)?.label ?? "English",
    [lang]
  );

  const chooseLang = (code: LangCode) => {
    setLang(code);
    const next = VOICES[code];
    if (!next.some((v) => v.id === voice)) setVoice(next[0].id);
    stop();
  };

  const stop = () => {
    const a = audioRef.current;
    if (a) {
      a.pause();
      a.currentTime = 0;
    }
    setPlaying(null);
  };

  const playSample = (id: string) => {
    const a = audioRef.current;
    if (!a) return;
    if (playing === id) return stop();
    a.src = lang === "hi" ? "/audio/hi_b1.mp3" : "/audio/en_b1.mp3";
    a.currentTime = 0;
    setPlaying(id);
    void a.play().catch(() => setPlaying(null));
  };

  const take = (f: File | undefined) => {
    if (f) {
      setFile(f.name);
      setTopic("");
    }
  };

  const begin = () => router.push(`/lesson?lang=${lang === "hi" ? "hi" : "en"}`);

  return (
    <main className="min-h-screen px-8" style={{ paddingTop: 88, paddingBottom: 140 }}>
      <audio ref={audioRef} onEnded={stop} preload="none" />

      <div style={{ width: "100%", maxWidth: 780, margin: "0 auto" }}>
        <motion.header
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 240, damping: 26 }}
        >
          <p className="t-micro accent" style={{ marginBottom: 24 }}>
            Set up your lesson
          </p>
          <h1 className="display t-h1" style={{ margin: 0 }}>
            Give me something to teach from.
          </h1>
          <p className="t-body muted" style={{ marginTop: 18, maxWidth: 560 }}>
            A textbook chapter, a set of notes, or just a topic. Everything below
            steers the lesson, and you can see exactly what I understood.
          </p>
        </motion.header>

        {/* ---------------------------------------------------------- source */}
        <Section label="Source" delay={0.06}>
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              take(e.dataTransfer.files[0]);
            }}
            onClick={() => pickRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => e.key === "Enter" && pickRef.current?.click()}
            style={{
              border: `1px dashed ${dragging || file ? "var(--accent)" : "var(--line)"}`,
              background: dragging ? "rgba(242,166,90,.05)" : "transparent",
              borderRadius: 10,
              padding: "38px 28px",
              cursor: "pointer",
              transition: "border-color .2s ease, background .2s ease",
            }}
          >
            <AnimatePresence mode="wait" initial={false}>
              {file ? (
                <motion.div
                  key="file"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ type: "spring", stiffness: 300, damping: 30 }}
                >
                  <p className="t-body" style={{ margin: 0 }}>
                    <span className="mono accent">{file}</span>
                  </p>
                  <p className="t-small muted" style={{ marginTop: 8 }}>
                    Parsed locally · 1 document · structure tree read
                  </p>
                  <button
                    className="ghost"
                    style={{ marginTop: 18, padding: "8px 16px" }}
                    onClick={(e) => {
                      e.stopPropagation();
                      setFile(null);
                    }}
                  >
                    Remove
                  </button>
                </motion.div>
              ) : (
                <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                  <p className="t-body" style={{ margin: 0 }}>
                    Drop a chapter here
                  </p>
                  <p className="t-small dim" style={{ marginTop: 8 }}>
                    PDF, DOCX, PPTX or TXT · or click to browse
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <input
            ref={pickRef}
            type="file"
            accept={ACCEPT}
            hidden
            onChange={(e) => take(e.target.files?.[0])}
          />

          <div style={{ display: "flex", alignItems: "baseline", gap: 16, marginTop: 26 }}>
            <span className="t-micro dim" style={{ whiteSpace: "nowrap" }}>
              or a topic
            </span>
            <input
              className="field"
              style={{ fontSize: 17, padding: "10px 2px" }}
              placeholder="Ohm's law and simple circuits"
              value={topic}
              onChange={(e) => {
                setTopic(e.target.value);
                if (e.target.value) setFile(null);
              }}
              aria-label="Topic to teach"
            />
          </div>
        </Section>

        {/* --------------------------------------------------- instruction */}
        <Section label="Tell me how to teach it" delay={0.12}>
          <textarea
            className="field"
            rows={3}
            style={{ fontSize: 19, lineHeight: 1.5, resize: "none" }}
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            aria-label="Teaching instruction"
          />
        </Section>

        {/* --------------------------------------------------------- rest */}
        <AnimatePresence>
          {ready && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <Section label="Teaching language" delay={0.04}>
                <div style={row}>
                  {LIVE.map((l) => (
                    <button
                      key={l.code}
                      className="pill"
                      data-on={lang === l.code}
                      onClick={() => chooseLang(l.code)}
                    >
                      {l.label}
                    </button>
                  ))}
                  {SOON.map((l) => (
                    <button
                      key={l}
                      className="pill"
                      disabled
                      title="Configured, not yet verified end to end"
                    >
                      {l}
                    </button>
                  ))}
                </div>
              </Section>

              <Section label="Where you are starting" delay={0.08}>
                <div style={row}>
                  {LEVELS.map((l) => (
                    <button
                      key={l}
                      className="pill"
                      data-on={level === l}
                      onClick={() => setLevel(l)}
                      style={{ textTransform: "capitalize" }}
                    >
                      {l}
                    </button>
                  ))}
                </div>
              </Section>

              <Section label="Time you have" delay={0.12}>
                <div style={row}>
                  {MINUTES.map((m) => (
                    <button
                      key={m}
                      className="pill"
                      data-on={minutes === m}
                      onClick={() => setMinutes(m)}
                    >
                      {m} min
                    </button>
                  ))}
                </div>
              </Section>

              <Section label="Your teacher" delay={0.16}>
                <div style={row}>
                  {TEACHERS.map((t) => (
                    <button
                      key={t.id}
                      className="pill"
                      data-on={teacher === t.id}
                      onClick={() => setTeacher(t.id)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 12,
                        padding: "8px 20px 8px 8px",
                      }}
                    >
                      <Face skin={t.skin} hair={t.hair} style={t.style} />
                      {t.name}
                    </button>
                  ))}
                </div>
              </Section>

              <Section label={`Voice · ${langLabel}`} delay={0.2}>
                <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  {voices.map((v) => {
                    const on = voice === v.id;
                    return (
                      <div
                        key={v.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 16,
                          padding: "14px 4px",
                          borderBottom: "1px solid var(--line)",
                        }}
                      >
                        <button
                          onClick={() => setVoice(v.id)}
                          style={{
                            flex: 1,
                            textAlign: "left",
                            background: "transparent",
                            border: 0,
                            cursor: "pointer",
                            padding: 0,
                            color: on ? "var(--accent)" : "var(--fg)",
                            transition: "color .18s ease",
                          }}
                        >
                          <span className="mono t-small">{v.id}</span>
                          <span className="t-small muted" style={{ marginLeft: 12 }}>
                            {v.note}
                          </span>
                        </button>
                        <span
                          className="t-micro"
                          style={{
                            color: on ? "var(--accent)" : "transparent",
                            transition: "color .18s ease",
                          }}
                        >
                          selected
                        </span>
                        <button
                          className="ghost"
                          style={{ padding: "7px 15px", fontSize: 13 }}
                          onClick={() => playSample(v.id)}
                        >
                          {playing === v.id ? "Stop" : "Play sample"}
                        </button>
                      </div>
                    );
                  })}
                </div>
                <p className="t-small dim" style={{ marginTop: 12 }}>
                  The sample is a real edge-tts clip from a rendered lesson beat, not
                  this voice reading your instruction.
                </p>
              </Section>

              <Section label="During the lesson" delay={0.24}>
                <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  {[
                    {
                      on: checkpoints,
                      set: setCheckpoints,
                      label: "Ask me questions during the lesson",
                      note: "Checkpoints after each concept, graded live",
                    },
                    {
                      on: finalQuiz,
                      set: setFinalQuiz,
                      label: "Quiz me at the end",
                      note: "Final assessment plus a learning report",
                    },
                  ].map((t) => (
                    <button
                      key={t.label}
                      onClick={() => t.set(!t.on)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 18,
                        padding: "16px 4px",
                        background: "transparent",
                        border: 0,
                        borderBottom: "1px solid var(--line)",
                        cursor: "pointer",
                        textAlign: "left",
                      }}
                    >
                      <span
                        style={{
                          width: 38,
                          height: 22,
                          borderRadius: 999,
                          flexShrink: 0,
                          background: t.on ? "var(--accent)" : "var(--line)",
                          padding: 3,
                          transition: "background .2s ease",
                        }}
                      >
                        <motion.span
                          layout
                          transition={{ type: "spring", stiffness: 500, damping: 34 }}
                          style={{
                            display: "block",
                            width: 16,
                            height: 16,
                            borderRadius: 999,
                            background: t.on ? "#0A0A0B" : "var(--dim)",
                            marginLeft: t.on ? 16 : 0,
                          }}
                        />
                      </span>
                      <span style={{ flex: 1 }}>
                        <span
                          className="t-body"
                          style={{
                            display: "block",
                            color: t.on ? "var(--fg)" : "var(--dim)",
                            transition: "color .2s ease",
                          }}
                        >
                          {t.label}
                        </span>
                        <span className="t-small dim" style={{ display: "block", marginTop: 4 }}>
                          {t.note}
                        </span>
                      </span>
                    </button>
                  ))}
                </div>
              </Section>

              {/* ------------------------------------------- parsed profile */}
              <Section label="What I understood" delay={0.28}>
                <div style={row}>
                  {[
                    level,
                    langLabel,
                    `${minutes} minutes`,
                    TEACHERS.find((t) => t.id === teacher)?.name ?? "",
                    checkpoints ? "checkpoints on" : "checkpoints off",
                    finalQuiz ? "final quiz" : "no final quiz",
                    file ?? (topic.trim() || "topic"),
                  ].map((chip) => (
                    <motion.span
                      key={chip}
                      layout
                      initial={{ opacity: 0, scale: 0.94 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ type: "spring", stiffness: 320, damping: 26 }}
                      className="t-small"
                      style={{
                        border: "1px solid var(--accent-dim)",
                        color: "var(--accent)",
                        borderRadius: 999,
                        padding: "6px 14px",
                        background: "rgba(242,166,90,.06)",
                      }}
                    >
                      {chip}
                    </motion.span>
                  ))}
                </div>
              </Section>

              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ type: "spring", stiffness: 260, damping: 28, delay: 0.32 }}
                style={{ marginTop: 56, display: "flex", alignItems: "center", gap: 20 }}
              >
                <button className="cta" onClick={begin}>
                  Begin the lesson
                </button>
                <span className="t-small dim">
                  Beat 1 starts playing while the rest of the plan is still being built.
                </span>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {!ready && (
          <p className="t-small dim" style={{ marginTop: 40 }}>
            Add a document or a topic to continue.
          </p>
        )}
      </div>
    </main>
  );
}
