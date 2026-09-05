"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { motion } from "framer-motion";

const LIVE = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
  { code: "hinglish", label: "Hinglish" },
];
// Configured in services/speech/voices.yaml with real voice ids, but outside the
// tested path. Shown rather than hidden, and disabled rather than faked.
const SOON = ["తెలుగు", "தமிழ்", "मराठी", "বাংলা", "Español", "Français"];

const EXAMPLE =
  "I am a beginner. Teach me Chapter 11 in 20 minutes using simple examples. " +
  "Ask me questions during the lesson and test me at the end.";

export default function Intake() {
  const router = useRouter();
  const [instruction, setInstruction] = useState(EXAMPLE);
  const [lang, setLang] = useState("en");

  const start = () => router.push(`/lesson?lang=${lang === "hinglish" ? "en" : lang}`);

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-8">
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="w-full"
        style={{ maxWidth: 780 }}
      >
        <p className="t-micro accent" style={{ marginBottom: 24 }}>
          Bharat Academix · AI Innovation Hackathon 2026
        </p>

        <h1 className="display t-hero" style={{ margin: 0 }}>
          What should I<br />teach you today?
        </h1>

        <p className="t-body muted" style={{ marginTop: 20, maxWidth: 560 }}>
          Describe it the way you would to a tutor. I read your textbook, plan the
          lesson, teach it, and change what comes next based on how you answer.
        </p>

        <div style={{ marginTop: 48 }}>
          <input
            className="field"
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && start()}
            aria-label="What should I teach you"
          />
        </div>

        <div style={{ marginTop: 40 }}>
          <p className="t-micro dim" style={{ marginBottom: 14 }}>Teaching language</p>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {LIVE.map((l) => (
              <button
                key={l.code}
                className="pill"
                data-on={lang === l.code}
                onClick={() => setLang(l.code)}
              >
                {l.label}
              </button>
            ))}
            {SOON.map((l) => (
              <button key={l} className="pill" disabled title="Configured, not yet tested end to end">
                {l}
              </button>
            ))}
          </div>
          <p className="t-small dim" style={{ marginTop: 12 }}>
            Six further languages are configured with real voices and are being
            verified end to end.
          </p>
        </div>

        <div style={{ marginTop: 48, display: "flex", gap: 12, alignItems: "center" }}>
          <button className="cta" onClick={start}>Begin the lesson</button>
          <span className="t-small dim">
            NCERT Class 10 Science, Chapter 11: Electricity
          </span>
        </div>
      </motion.div>
    </main>
  );
}
