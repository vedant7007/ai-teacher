# Multilingual

## Shipped end to end

**English**, **Hindi**, **Hinglish** (Roman-script code-mixed). Configured but
not verified end to end: Telugu, Tamil, Marathi, Bengali, Spanish, French. These
appear in the UI as unavailable rather than being offered and failing.

Configuration: `services/speech/voices.yaml`, one entry per language with a
voice, a fallback voice, a speaking rate and a `shipped` flag.

## Cross-lingual grounding

The source document's language and the teaching language are independent. A
query is embedded as given **and** as its translation, and the result sets are
unioned before RRF fusion, so a Hindi question retrieves from an English
textbook and the reverse. Citations always point at the original-language span.

Both NCERT seed chapters are present in English and Hindi, letting us verify the
English-source-to-Hindi-teaching path against a true parallel text.

## Hinglish

Hinglish deliberately uses the Indian **English** voice. A Hindi voice reading
Roman-script Hindi mispronounces heavily, while the English voice handles
code-mixed text well.

## What Devanagari cost us

Two bugs, both silent, both now covered by tests:

- The danda `।` (U+0964) sits **inside** the `ऀ-ॿ` Unicode block, so a
  range-based normaliser preserved it. Every sentence-final word then failed to
  match its spoken token, collapsing animation cues in 25 of 26 beats.
- Some words are never voiced at all (a bare `Ω`), which desynced everything
  after them until the aligner learned to look ahead.

Detail in [VOICE.md](VOICE.md).
