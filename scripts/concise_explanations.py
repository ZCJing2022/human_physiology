#!/usr/bin/env python3
"""One-time, reviewed concision edit; only the pinned narrative revision is eligible.

Use --apply to write the curated edits and regenerate the seven question pages.
Use --check to verify this editorial revision. No generic truncation is performed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import statistics
import subprocess
import sys
from pathlib import Path
import expand_explanations as core

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'assessment/detailed-explanations'
REPORT = ROOT / 'assessment/explanation-concision-audit.json'
EXPECTED = {
    'week05.md': '3bd5b626e74f501571059bb6f2801e396457018d',
    'week06.md': 'c5638ea1d5ce7d77b43bd5ae40fe74f7e8f31395',
    'week07.md': 'a80a32fbc0efdc17e17472a73622e6ef1e978fd4',
    'week08.md': 'b19efbfea16d9055fa98c12504e03a4a4cafeee2',
    'exam-short-responses.md': 'd356fa0490fb86acccb19c6714231aed617c44df',
}
UPDATER_BLOB = 'bc4087f370d2c158b7420e824d281f21afed2db7'


def corpus_hash() -> str:
    h = hashlib.sha256()
    for name in sorted(EXPECTED):
        h.update(name.encode())
        h.update((DATA / name).read_bytes())
    return h.hexdigest()


def revise(key: str, body: str, spec: dict) -> str:
    drop = set(spec['drop'])
    replace = {int(k): v for k, v in spec.get('replace', {}).items()}
    core.require(not drop.intersection(replace), f'{key}: conflicting edit')
    result, n = [], 0
    for paragraph in body.split('\n\n'):
        kept = []
        for sentence in re.split(r'(?<=[.!?])\s+(?=[A-Z*(])', paragraph):
            n += 1
            if n not in drop:
                kept.append(replace.get(n, sentence))
        if kept:
            result.append(' '.join(kept))
    core.require(all(1 <= i <= n for i in drop | set(replace)), f'{key}: invalid sentence index')
    updated = '\n\n'.join(result)
    before, after = core.words(body), core.words(updated)
    minimum = 100 if '-mc' in key else 130
    core.require(minimum <= after < before, f'{key}: unexpected length {before} -> {after}')
    core.require(len(result) >= 2, f'{key}: narrative needs at least two paragraphs')
    core.require(re.findall(r'\$\$.*?\$\$', body, re.S) == re.findall(r'\$\$.*?\$\$', updated, re.S),
                 f'{key}: display calculation changed')
    core.require(updated.count('**') % 2 == 0, f'{key}: unmatched emphasis')
    return updated


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--apply', action='store_true')
    group.add_argument('--check', action='store_true')
    args = ap.parse_args()
    if REPORT.exists():
        report = json.loads(REPORT.read_text())
        core.require(corpus_hash() == report['revised_corpus_sha256'], 'Narratives changed after this editorial revision; review rather than reapply the migration')
        subprocess.run([sys.executable, str(ROOT / 'scripts/expand_explanations.py'), '--check'], check=True)
        print('PASS: concise revision already applied; no repeated cuts')
        return
    core.require(args.apply, 'Concision revision has not been applied')
    specs = json.loads((ROOT / 'assessment/explanation-concision-edits.json').read_text())
    old_record = json.loads(core.AUDIT.read_text())
    protected = {f['file']: core.protected_content((ROOT / f['file']).read_text()) for f in old_record['files']}
    updates, seen = {}, set()
    for name, expected in EXPECTED.items():
        path = DATA / name
        original = path.read_text(encoding='utf-8')
        core.require(core.blob(original) == expected, f'{name}: not the reviewed baseline; refusing automatic edits')
        heads = list(core.ENTRY.finditer(original))
        pieces = [original[:heads[0].start()]]
        for i, h in enumerate(heads):
            key = h['id']
            end = heads[i+1].start() if i+1 < len(heads) else len(original)
            core.require(key in specs and key not in seen, f'{key}: missing or duplicate editorial recipe')
            seen.add(key)
            body = original[h.end():end].strip()
            pieces.append(h.group() + '\n\n' + revise(key, body, specs[key]) + '\n\n')
        updates[path] = ''.join(pieces).rstrip() + '\n'
    core.require(seen == set(specs) and len(seen) == 168, 'Editorial coverage mismatch')
    updater = ROOT / 'scripts/expand_explanations.py'
    script = updater.read_text(encoding='utf-8')
    core.require(core.blob(script) == UPDATER_BLOB, 'Updater changed; review before patching validation policy')
    patches = {
        'minimum = 100 if is_mc else 150': 'minimum = 100 if is_mc else 130',
        "len(body.split('\\n\\n')) >= 3": "len(body.split('\\n\\n')) >= 2",
        "'version': '2026-11-05-detailed-v1'": "'version': '2026-11-05-concise-v2'",
        '- Narrative length before:': '- Original short explanations:',
        '- Narrative length after:': '- Current narrative length:',
    }
    for old, new in patches.items():
        core.require(script.count(old) == 1, f'Unexpected updater patch target: {old}')
        script = script.replace(old, new)
    updates[updater] = script
    for path, text in updates.items():
        core.atomic_write(path, text)
    subprocess.run([sys.executable, str(updater), '--apply'], check=True)
    current = json.loads(core.AUDIT.read_text())
    old_items = {(r['file'], r['question']): r for r in old_record['items']}
    items = []
    for row in current['items']:
        previous = old_items[(row['file'], row['question'])]
        before, after = previous['words_after'], row['words_after']
        core.require(after < before, f'{row["file"]} Q{row["question"]}: not shorter')
        items.append({'file': row['file'], 'question': row['question'], 'narrative_id': row['narrative_id'],
                      'words_before': before, 'words_after': after})
    core.require(len(items) == 244, 'Expected all 244 question instances')
    for file, skeleton in protected.items():
        core.require(skeleton == core.protected_content((ROOT / file).read_text()), f'{file}: protected content changed')
    before = [r['words_before'] for r in items]
    after = [r['words_after'] for r in items]
    report = {
        'revision': '2026-11-05-concise-v2',
        'previous_main_commit': 'ad2090d9eb129d89f18a96bed110c246767b8fc7',
        'total_question_panels': 244, 'distinct_narratives': 168,
        'mean_words_before': round(statistics.mean(before), 1),
        'mean_words_after': round(statistics.mean(after), 1),
        'overall_reduction_percent': round(100 * (1 - sum(after)/sum(before)), 1),
        'range_after': [min(after), max(after)],
        'revised_corpus_sha256': corpus_hash(),
        'checks': {'every_explanation_shorter': True, 'questions_answers_and_panel_wrappers_unchanged': True,
                   'all_display_calculations_unchanged': True, 'all_narratives_multi_paragraph': True},
        'items': items,
    }
    core.atomic_write(REPORT, json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    lines = ['# Explanation concision audit', '',
             'All 244 explanations were shortened: 160 weekly questions and 84 questions across three practice exams. The 168 distinct narratives are propagated to repeated questions using the existing exact-match checks.', '',
             f'Average narrative length: **{report["mean_words_before"]} to {report["mean_words_after"]} words**, a **{report["overall_reduction_percent"]}% reduction**. Current range: {min(after)}–{max(after)} words, excluding course-source and review footers.', '',
             'The edits remove selected repeated setup, recaps, and exam-writing commentary, with targeted sentence rewrites. They are individually curated edits, not automatic truncation. More complex mechanisms and worked problems retain additional space.', '',
             '| Page | Questions | Previous mean | Revised mean | Reduction |',
             '|---|---:|---:|---:|---:|']
    for f in current['files']:
        rows = [r for r in items if r['file'] == f['file']]
        b, a = sum(r['words_before'] for r in rows), sum(r['words_after'] for r in rows)
        lines.append(f'| `{f["file"]}` | {len(rows)} | {b/len(rows):.1f} | {a/len(rows):.1f} | {100*(1-a/b):.1f}% |')
    lines += ['', '## Preservation checks', '',
              'Question prompts, choices, answer keys, numbering, timing instructions, and callout wrappers are unchanged byte-for-byte outside Explanation bodies. Every display-calculation block is unchanged. The explanations retain multiple paragraphs, course-source notes, and review links. Source checks preserve the initially collapsed Answer and Explanation settings. Rendered HTML is checked separately by the publishing workflow.', '',
              'This is an editorial and structural check, not independent expert certification of the physiology. Future wording edits belong in `assessment/detailed-explanations/`; regenerate pages with `scripts/expand_explanations.py`. The concision migration is a historical, pinned one-time edit, not part of routine publishing.', '']
    core.atomic_write(ROOT / 'EXPLANATION_CONCISION_AUDIT.md', '\n'.join(lines))
    print(f'PASS: all 244 explanations shorter; average {report["mean_words_before"]} -> {report["mean_words_after"]}; reduction {report["overall_reduction_percent"]}%')


if __name__ == '__main__':
    main()
