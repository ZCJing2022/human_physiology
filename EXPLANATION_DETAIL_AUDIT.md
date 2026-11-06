# Detailed Explanation audit

All 244 current question panels are covered: 160 weekly questions and 84 questions across three practice exams.

The update changes Explanation bodies only. Question prompts, choices, answer keys, numbering, timing instructions, and callout wrappers are preserved byte-for-byte outside those bodies.

## Narrative development

- Authored narratives: 168; identical exam questions receive the full corresponding narrative, not just a link.
- Narrative length before: 8–39 words; mean 16.6.
- Narrative length after: 144–289 words; mean 170.5.
- Counts exclude the source and study-guide footer; word counts are a structural check, not a substitute for content review.

| Page | MCQs | Short responses | Explanation words: min–max | Mean |
|---|---:|---:|---:|---:|
| `practice/week05-sensory.qmd` | 28 | 12 | 149–226 | 172.5 |
| `practice/week06-vision-muscle.qmd` | 28 | 12 | 144–210 | 168.9 |
| `practice/week07-cardiac.qmd` | 28 | 12 | 144–289 | 173.2 |
| `practice/week08-vascular-blood.qmd` | 28 | 12 | 149–231 | 173.9 |
| `practice/practice-midterm2-01.qmd` | 24 | 4 | 144–241 | 166.8 |
| `practice/practice-midterm2-02.qmd` | 24 | 4 | 144–239 | 167.1 |
| `practice/practice-midterm2-03.qmd` | 24 | 4 | 144–243 | 167.9 |

## Checks passed

Every question has exactly one Answer panel followed by one Explanation panel, both with `collapse="true"`. Every weekly question has its reviewed stable ID. Each reused exam MCQ matches the full weekly prompt, options, and correct answer. All exam short-response prompts are matched explicitly. Every narrative is multi-paragraph and has a course-source note and working source-level study-guide link.

Calculations include the formula, substitution, units, conversion where needed, and interpretation. Mechanism questions explain the causal sequence. MCQs discuss the alternatives; essays explain all requested elements and relevant assumptions. Content is grounded in the supplied lectures and Silverthorn chapters; the examination-format item cites the supplied announcement. This is an editorial and structural audit, not a claim of independent expert certification.

## Maintenance

Curated narratives are in `assessment/detailed-explanations/`. Run `python3 scripts/expand_explanations.py --apply` after revising narratives; then render and run `python3 scripts/expand_explanations.py --check --html docs`. The updater refuses unreviewed changes to question or answer text. No original source PDFs are added to the public repository.
