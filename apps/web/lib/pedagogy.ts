// Client-side port of the deterministic pedagogy core.
//
// The taxonomy JSON and the BKT constants are the SAME ones the Python tests
// assert against (services/pedagogy/). Porting them lets the deployed demo run
// the real adaptive loop with no backend at all, rather than replaying a canned
// sequence. Python remains the source of truth; this is generated data plus
// about forty lines of arithmetic.

export type Misconception = {
  summary: string;
  correct_model: string;
  analogy_family: string;
  analogy: string;
  diagnostic: string;
  concept: string;
  patterns: string[];
};

export const P_INIT = 0.25;
export const P_TRANSIT = 0.15;
export const P_SLIP = 0.1;
export const P_GUESS = 0.2;
export const STRUGGLING = 0.4;
export const MASTERED = 0.85;

const FAMILIES = ["everyday", "mechanical", "computational", "biological", "financial"];

/** One BKT step. Identical maths to services/pedagogy/bkt.py::update. */
export function bktUpdate(pKnown: number, correct: boolean): number {
  const p = Math.min(Math.max(pKnown, 0), 1);
  const num = correct ? p * (1 - P_SLIP) : p * P_SLIP;
  const den = correct
    ? num + (1 - p) * P_GUESS
    : num + (1 - p) * (1 - P_GUESS);
  const post = den ? num / den : p;
  return Math.min(1, post + (1 - post) * P_TRANSIT);
}

export type Match = { id: string; entry: Misconception; pattern: string };

/** Deterministic match, concept-scoped first, exactly as the Python does. */
export function matchMisconception(
  answer: string,
  taxonomy: Record<string, Misconception>,
  conceptId?: string,
): Match | null {
  if (!answer?.trim()) return null;
  const ids = Object.keys(taxonomy).sort((a, b) => {
    const aOwn = taxonomy[a].concept === conceptId ? 0 : 1;
    const bOwn = taxonomy[b].concept === conceptId ? 0 : 1;
    return aOwn - bOwn;
  });
  for (const id of ids) {
    for (const p of taxonomy[id].patterns) {
      try {
        if (new RegExp(p, "iu").test(answer)) return { id, entry: taxonomy[id], pattern: p };
      } catch {
        /* a pattern that will not compile in JS is skipped, not fatal */
      }
    }
  }
  return null;
}

export function differentFamily(used: Set<string>): string {
  return FAMILIES.find((f) => !used.has(f)) ?? "everyday";
}

export type Graded = {
  correct: boolean;
  misconceptionId: string | null;
  matchedBy: "taxonomy" | "default";
  feedback: string;
  action: string;
  reexplanation?: { script: string; family: string; items: string[] };
  newQuestion?: { prompt: string; targets: string | null };
};

function looksCorrect(answer: string, key: string, rubric: string[]): boolean {
  const a = answer.trim().toLowerCase();
  if (!a) return false;
  const k = (key || "").trim().toLowerCase();
  const kn = k.match(/-?\d+\.?\d*/);
  const an = a.match(/-?\d+\.?\d*/);
  if (kn && an && Math.abs(parseFloat(kn[0]) - parseFloat(an[0])) < 0.01) return true;
  if (k && a.includes(k)) return true;
  const words = new Set(
    rubric.flatMap((r) => (r.toLowerCase().match(/\w{4,}/g) ?? [])),
  );
  if (words.size) {
    let hit = 0;
    words.forEach((w) => {
      if (a.includes(w)) hit += 1;
    });
    return hit / words.size >= 0.4;
  }
  return false;
}

/** Grade, then build the re-explanation. Deterministic, no network. */
export function grade(
  answer: string,
  question: { answer_key?: string; rubric?: string[]; concept_id?: string },
  taxonomy: Record<string, Misconception>,
  usedFamilies: Set<string>,
  pKnown: number,
  consecutiveWrong: number,
  hasPrereq: boolean,
): Graded {
  const hit = matchMisconception(answer, taxonomy, question.concept_id);

  if (hit) {
    const family = usedFamilies.has(hit.entry.analogy_family)
      ? differentFamily(usedFamilies)
      : hit.entry.analogy_family;
    return {
      correct: false,
      misconceptionId: hit.id,
      matchedBy: "taxonomy",
      feedback: `That is a really common way to think about it, and it is worth naming: ${hit.entry.summary} Here is what is actually going on. ${hit.entry.correct_model}`,
      action:
        consecutiveWrong + 1 >= 2 && hasPrereq
          ? "step_back_prereq"
          : pKnown < STRUGGLING
            ? "reexplain_analogy"
            : "reexplain_simpler",
      reexplanation: {
        script: `Let me try a completely different picture. ${hit.entry.analogy} ${hit.entry.correct_model}`,
        family,
        items: hit.entry.correct_model
          .split(/(?<=[.।])\s+/)
          .filter((s) => s.trim().length > 8)
          .slice(0, 4),
      },
      newQuestion: { prompt: hit.entry.diagnostic, targets: hit.id },
    };
  }

  if (looksCorrect(answer, question.answer_key ?? "", question.rubric ?? [])) {
    return {
      correct: true,
      misconceptionId: null,
      matchedBy: "taxonomy",
      feedback: "That is right, and your reasoning matches the rubric.",
      action: pKnown >= MASTERED ? "level_up" : "continue",
    };
  }

  return {
    correct: false,
    misconceptionId: "novel_misconception",
    matchedBy: "default",
    feedback:
      "That is not quite it, and I want to understand how you got there before moving on. Let me explain it a different way.",
    action: "reexplain_simpler",
    reexplanation: {
      script: "Let us come at this from a different angle.",
      family: differentFamily(usedFamilies),
      items: [],
    },
    newQuestion: { prompt: "In your own words, what actually happens and why?", targets: null },
  };
}

/** SM-2 due date for a lapsed concept. */
export function nextReview(correct: boolean, repetitions: number): string {
  const days = correct ? (repetitions === 0 ? 1 : repetitions === 1 ? 6 : 15) : 1;
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}
