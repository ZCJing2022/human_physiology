# Explanation concision audit

All 244 explanations were shortened: 160 weekly questions and 84 questions across three practice exams. The 168 distinct narratives are propagated to repeated questions using the existing exact-match checks.

Average narrative length: **170.5 to 134.2 words**, a **21.2% reduction**. Current range: 106–235 words, excluding course-source and review footers.

The edits remove selected repeated setup, recaps, and exam-writing commentary, with targeted sentence rewrites. They are individually curated edits, not automatic truncation. More complex mechanisms and worked problems retain additional space.

| Page | Questions | Previous mean | Revised mean | Reduction |
|---|---:|---:|---:|---:|
| `practice/week05-sensory.qmd` | 40 | 172.5 | 133.6 | 22.6% |
| `practice/week06-vision-muscle.qmd` | 40 | 168.9 | 133.3 | 21.1% |
| `practice/week07-cardiac.qmd` | 40 | 173.2 | 136.5 | 21.2% |
| `practice/week08-vascular-blood.qmd` | 40 | 173.9 | 137.9 | 20.7% |
| `practice/practice-midterm2-01.qmd` | 28 | 166.8 | 131.7 | 21.0% |
| `practice/practice-midterm2-02.qmd` | 28 | 167.1 | 132.5 | 20.7% |
| `practice/practice-midterm2-03.qmd` | 28 | 167.9 | 132.4 | 21.2% |

## Preservation checks

Question prompts, choices, answer keys, numbering, timing instructions, and callout wrappers are unchanged byte-for-byte outside Explanation bodies. Every display-calculation block is unchanged. The explanations retain multiple paragraphs, course-source notes, and review links. Source checks preserve the initially collapsed Answer and Explanation settings. Rendered HTML is checked separately by the publishing workflow.

This is an editorial and structural check, not independent expert certification of the physiology. Future wording edits belong in `assessment/detailed-explanations/`; regenerate pages with `scripts/expand_explanations.py`. The concision migration is a historical, pinned one-time edit, not part of routine publishing.
