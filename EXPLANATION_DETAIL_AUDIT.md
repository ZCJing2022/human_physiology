# Detailed Explanation audit

All 244 current question panels are covered: 160 weekly questions and 84 questions across three practice exams.

The update changes Explanation bodies only. Question prompts, choices, answer keys, numbering, timing instructions, and callout wrappers are preserved byte-for-byte outside those bodies.

## Narrative development

- Authored narratives: 168; identical exam questions receive the full corresponding narrative, not just a link.
- Original short explanations: 8–39 words; mean 16.6.
- Current narrative length: 106–235 words; mean 134.2.
- Counts exclude the source and study-guide footer; word counts are a structural check, not a substitute for content review.

| Page | MCQs | Short responses | Explanation words: min–max | Mean |
|---|---:|---:|---:|---:|
| `practice/week05-sensory.qmd` | 28 | 12 | 106–170 | 133.6 |
| `practice/week06-vision-muscle.qmd` | 28 | 12 | 110–171 | 133.3 |
| `practice/week07-cardiac.qmd` | 28 | 12 | 111–235 | 136.5 |
| `practice/week08-vascular-blood.qmd` | 28 | 12 | 111–192 | 137.9 |
| `practice/practice-midterm2-01.qmd` | 24 | 4 | 115–191 | 131.7 |
| `practice/practice-midterm2-02.qmd` | 24 | 4 | 111–186 | 132.5 |
| `practice/practice-midterm2-03.qmd` | 24 | 4 | 111–190 | 132.4 |

## Checks passed

Every question has exactly one Answer panel followed by one Explanation panel, both with `collapse="true"`. Every weekly question has its reviewed stable ID. Each reused exam MCQ matches the full weekly prompt, options, and correct answer. All exam short-response prompts are matched explicitly. Every narrative is multi-paragraph and has a course-source note and working source-level study-guide link.

Calculations include the formula, substitution, units, conversion where needed, and interpretation. Mechanism questions explain the causal sequence. MCQs discuss the alternatives; essays explain all requested elements and relevant assumptions. Content is grounded in the supplied lectures and Silverthorn chapters; the examination-format item cites the supplied announcement. This is an editorial and structural audit, not a claim of independent expert certification.

## Maintenance

Curated narratives are in `assessment/detailed-explanations/`. Run `python3 scripts/expand_explanations.py --apply` after revising narratives; then render and run `python3 scripts/expand_explanations.py --check --html docs`. The updater refuses unreviewed changes to question or answer text. No original source PDFs are added to the public repository.
