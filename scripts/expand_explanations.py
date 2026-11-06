#!/usr/bin/env python3
"""Apply curated explanations without changing questions, answers, or callout markup.

Usage: python3 scripts/expand_explanations.py --apply
       python3 scripts/expand_explanations.py --check --html docs

Standard library only. All seven pages are validated before any source is written.
The first application requires the exact reviewed source blobs. Later applications
require unchanged non-Explanation content recorded in the audit. Identical exam
MCQs match the complete weekly prompt AND options, and must have the same key.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'assessment/detailed-explanations'
AUDIT = ROOT / 'assessment/explanation-detail-audit.json'
BASE_COMMIT = '3688ff405804b07cd8b63cc431e0900bbea14d01'
WEEKS = {
    5: ('week05-sensory', '99c0401062b5e921467111b43342f7b10c0bfc3c', 'Lectures 13–14; Silverthorn (2019), Chapter 10.'),
    6: ('week06-vision-muscle', '27421638f25206d0439c5069f60120adc646617d', 'Lectures 15–17; Silverthorn (2019), Chapters 10 and 12.'),
    7: ('week07-cardiac', 'e7b0e66beb0644bbeced3ce216f2def53b3132c7', 'Lectures 18–20; Silverthorn (2019), Chapter 14.'),
    8: ('week08-vascular-blood', 'df9444a0cb98427bba830817db3b566648ea7382', 'Lectures 21–23; Silverthorn (2019), Chapters 15 and 16.'),
}
EXAM_BLOBS = {
    1: '89da6ab9be83db8a3e903e129da7afc2a4bfba20',
    2: '5fe28578e8a6b46b2b9037c5448fffa5de12bfd8',
    3: '4c8dcc1d5e794eff5e86475610dd11f25337def6',
}
EXAM_PROMPTS = {
    'e01-q25': (5, 'A sustained pressure stimulus initially causes a high firing rate that then declines. Explain the receptor property involved and how the CNS can still code stimulus duration.'),
    'e01-q26': (6, 'Explain why light hyperpolarizes rods and how this changes transmitter release.'),
    'e01-q27': (6, 'A patient has normal motor-neuron action potentials but a toxin blocks nicotinic ACh receptors. Trace the consequences from the NMJ to muscle force.'),
    'e01-q28': (6, 'Explain how increasing stimulation frequency and increasing motor-unit recruitment each increase skeletal muscle force.'),
    'e02-q27': (7, 'Trace cardiac excitation from SA node to ventricular myocardium and explain the functional role of AV nodal delay.'),
    'e02-q28': (7, 'Relate the QRS complex to ventricular pressure, AV valve closure, semilunar valve opening, and the beginning of ejection.'),
    'e03-q27': (7, 'A person has EDV 125 mL, ESV 55 mL, and HR 80/min. Calculate SV and CO.'),
    'e03-q28': (7, 'Venous return suddenly increases. Predict the immediate effect on EDV, stroke volume, and cardiac output through the Frank–Starling mechanism.'),
}
EXAM_SHORT = {
    1: ['e01-q25', 'e01-q26', 'e01-q27', 'e01-q28'],
    2: ['e01-q27', 'e01-q28', 'e02-q27', 'e02-q28'],
    3: ['e02-q27', 'e02-q28', 'e03-q27', 'e03-q28'],
}
HEAD = re.compile(r'^### Question (?P<num>\d+) — [^\n]+\n', re.M)
EXPLANATION = re.compile(
    r'^(?P<opening>::: \{[^\n]*title="Explanation"[^\n]*\}\n)'
    r'(?P<body>.*?)(?P<closing>^:::[ \t]*(?=\n|\Z))', re.M | re.S)
ANSWER = re.compile(
    r'^(?P<opening>::: \{[^\n]*title="Answer"[^\n]*\}\n)'
    r'(?P<body>.*?)(?P<closing>^:::[ \t]*(?=\n|\Z))', re.M | re.S)
ENTRY = re.compile(r'^## (?P<id>w\d{2}-(?:mc|sr)\d{2}|e\d{2}-q\d{2})[ \t]*$', re.M)


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def normalize(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def words(text: str) -> int:
    text = re.split(r'\n\*\*(?:Review|Course sources):\*\*', text)[0]
    return len(re.findall(r"\b\w+(?:[’'-]\w+)*\b", text))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def blob(text: str) -> str:
    data = text.encode('utf-8')
    return hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()


def protected_content(text: str) -> str:
    return EXPLANATION.sub(lambda m: m['opening'] + '<EXPLANATION_BODY>\n' + m['closing'], text)


def load_narratives() -> dict[str, str]:
    result = {}
    for path in sorted(DATA.glob('*.md')):
        text = path.read_text(encoding='utf-8')
        headings = list(ENTRY.finditer(text))
        for i, h in enumerate(headings):
            key = h['id']
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            body = text[h.end():end].strip()
            require(key not in result, f'Duplicate narrative {key}')
            require(':::' not in body, f'Nested callout delimiter in {key}')
            require('**Review:**' not in body, f'Review footer belongs to renderer: {key}')
            is_mc = '-mc' in key
            minimum = 100 if is_mc else 150
            require(words(body) >= minimum, f'{key}: {words(body)} words; expected >= {minimum}')
            require(len(body.split('\n\n')) >= 3, f'{key}: needs a developed multi-paragraph narrative')
            result[key] = body
    expected = {f'w{w:02d}-mc{i:02d}' for w in WEEKS for i in range(1, 29)}
    expected |= {f'w{w:02d}-sr{i:02d}' for w in WEEKS for i in range(1, 13)}
    expected |= set(EXAM_PROMPTS)
    require(set(result) == expected, f'Narrative coverage mismatch; missing={expected-set(result)}, extra={set(result)-expected}')
    return result


def parse_questions(text: str) -> tuple[str, list[dict]]:
    headings = list(HEAD.finditer(text))
    require(bool(headings), 'No questions found')
    result = []
    for i, h in enumerate(headings):
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        block_text = text[h.start():end]
        a = list(ANSWER.finditer(block_text))
        e = list(EXPLANATION.finditer(block_text))
        require(len(a) == len(e) == 1, f'Question {h["num"]}: expected exactly one Answer and Explanation')
        require(a[0].end() < e[0].start(), f'Question {h["num"]}: Explanation must follow Answer')
        for panel in (a[0], e[0]):
            require('collapse="true"' in panel['opening'], f'Question {h["num"]}: panel is not initially collapsed')
        header_end = block_text.index('\n') + 1
        prompt = block_text[header_end:a[0].start()].strip()
        key = re.search(r'\*\*Correct answer: ([A-D])\.\*\*', a[0]['body'])
        result.append({'number': int(h['num']), 'header': h.group(), 'block': block_text,
                       'prompt': prompt, 'answer': a[0].group(), 'key': key[1] if key else None,
                       'explanation': e[0]['body']})
    require([q['number'] for q in result] == list(range(1, len(result)+1)), 'Question numbering is not consecutive')
    return text[:headings[0].start()], result


def footer(week: int, narrative_id: str) -> str:
    name, _, source = WEEKS[week]
    if narrative_id == 'w08-mc28':
        source = 'Supplied course announcement, “BPK205 Midterm 2,” posted November 4, 2026 (uploaded PDF).'
    require((ROOT / f'study-guides/{name}.qmd').is_file(), f'Missing study guide for Week {week}')
    return f'\n\n**Course sources:** {source}\n\n**Review:** [Week {week} study guide](../study-guides/{name}.qmd).\n'


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(text, encoding='utf-8')
    temp.replace(path)


def build_update() -> tuple[dict[str, str], dict]:
    narratives = load_narratives()
    old_audit = json.loads(AUDIT.read_text(encoding='utf-8')) if AUDIT.exists() else {}
    old_items = {(x['file'], x['question']): x for x in old_audit.get('items', [])}
    old_files = {x['file']: x for x in old_audit.get('files', [])}
    updates, rows, file_rows, weekly_index = {}, [], [], {}
    sources = [(f'practice/{v[0]}.qmd', v[1], w, None) for w, v in WEEKS.items()]
    sources += [(f'practice/practice-midterm2-{n:02d}.qmd', b, None, n) for n, b in EXAM_BLOBS.items()]
    used = set()
    for relative, baseline_blob, week, exam in sources:
        original = (ROOT / relative).read_text(encoding='utf-8')
        skeleton = sha(protected_content(original))
        previously_recorded = old_files.get(relative, {}).get('protected_content_sha256')
        require(blob(original) == baseline_blob or skeleton == previously_recorded,
                f'{relative}: questions or non-Explanation content changed since review; inspect before applying')
        prefix, questions = parse_questions(original)
        expected_count = 40 if week is not None else 28
        expected_mc = 28 if week is not None else 24
        require(len(questions) == expected_count, f'{relative}: unexpected question count')
        require(sum(q['key'] is not None for q in questions) == expected_mc, f'{relative}: MCQ count changed')
        new_blocks = []
        file_items = []
        for q in questions:
            is_mc = q['key'] is not None
            if week is not None:
                m = re.search(r'\{#(w\d{2}-(?:mc|sr)\d{2})\}', q['header'])
                require(m is not None, f'{relative}: question missing stable ID')
                narrative_id = m[1]
                expected_id = f'w{week:02d}-' + (f'mc{q["number"]:02d}' if is_mc else f'sr{q["number"]-28:02d}')
                require(narrative_id == expected_id, f'{relative}: changed question type/order')
                source_week = week
                if is_mc:
                    p = normalize(q['prompt'])
                    require(p not in weekly_index, f'Ambiguous repeated weekly MCQ: {narrative_id}')
                    weekly_index[p] = (narrative_id, week, q['key'])
            elif is_mc:
                p = normalize(q['prompt'])
                require(p in weekly_index, f'{relative} Q{q["number"]}: no exact weekly stem/options match')
                narrative_id, source_week, answer_key = weekly_index[p]
                require(answer_key == q['key'], f'{relative} Q{q["number"]}: inconsistent answer key')
            else:
                require(25 <= q['number'] <= 28, f'{relative}: unexpected short-response number')
                narrative_id = EXAM_SHORT[exam][q['number'] - 25]
                source_week, expected_prompt = EXAM_PROMPTS[narrative_id]
                require(normalize(q['prompt']) == normalize(expected_prompt), f'{relative} Q{q["number"]}: changed essay prompt')
            used.add(narrative_id)
            narrative = narratives[narrative_id]
            body = narrative + footer(source_week, narrative_id)
            new_block = EXPLANATION.sub(lambda m: m['opening'] + body + m['closing'], q['block'], count=1)
            require(protected_content(new_block) == protected_content(q['block']), f'{relative}: non-Explanation change')
            require(ANSWER.search(new_block).group() == q['answer'], f'{relative}: answer changed')
            new_blocks.append(new_block)
            prior = old_items.get((relative, q['number']), {})
            row = {'file': relative, 'question': q['number'], 'type': 'MCQ' if is_mc else 'Short response',
                   'narrative_id': narrative_id, 'words_before': prior.get('words_before', words(q['explanation'])),
                   'words_after': words(narrative), 'paragraphs': len(narrative.split('\n\n')),
                   'initially_collapsed': True, 'answer_unchanged': True}
            rows.append(row)
            file_items.append(row)
        updated = prefix + ''.join(new_blocks)
        require(protected_content(updated) == protected_content(original), f'{relative}: protected text changed')
        require(len(EXPLANATION.findall(updated)) == expected_count, f'{relative}: missing explanation')
        updates[relative] = updated
        counts = [r['words_after'] for r in file_items]
        file_rows.append({'file': relative, 'questions': expected_count, 'mcq': expected_mc,
                          'short_response': expected_count - expected_mc,
                          'explanation_min_words': min(counts), 'explanation_max_words': max(counts),
                          'explanation_mean_words': round(statistics.mean(counts), 1),
                          'protected_content_sha256': skeleton, 'updated_blob_sha': blob(updated)})
    require(used == set(narratives), 'Unused narrative entries')
    require(len(rows) == 244, f'Expected 244 panels, found {len(rows)}')
    record = {'version': '2026-11-05-detailed-v1', 'reviewed_base_commit': BASE_COMMIT,
              'narrative_corpus_sha256': sha(json.dumps(narratives, ensure_ascii=False, sort_keys=True)),
              'total_question_panels': len(rows), 'weekly_panels': 160, 'exam_panels': 84,
              'distinct_authored_narratives': len(narratives),
              'checks': {'question_and_answer_text_preserved': True, 'all_panels_initially_collapsed': True,
                         'weekly_70_30_mix_preserved': True, 'exam_format_and_timing_preserved': True,
                         'exact_match_for_reused_exam_mcqs': True, 'all_essay_prompts_verified': True,
                         'all_explanations_have_study_guide_links': True},
              'files': file_rows, 'items': rows}
    return updates, record


def markdown_audit(record: dict) -> str:
    items = record['items']
    before = [x['words_before'] for x in items]
    after = [x['words_after'] for x in items]
    lines = ['# Detailed Explanation audit', '',
             'All 244 current question panels are covered: 160 weekly questions and 84 questions across three practice exams.', '',
             'The update changes Explanation bodies only. Question prompts, choices, answer keys, numbering, timing instructions, and callout wrappers are preserved byte-for-byte outside those bodies.', '',
             '## Narrative development', '',
             f'- Authored narratives: {record["distinct_authored_narratives"]}; identical exam questions receive the full corresponding narrative, not just a link.',
             f'- Narrative length before: {min(before)}–{max(before)} words; mean {statistics.mean(before):.1f}.',
             f'- Narrative length after: {min(after)}–{max(after)} words; mean {statistics.mean(after):.1f}.',
             '- Counts exclude the source and study-guide footer; word counts are a structural check, not a substitute for content review.', '',
             '| Page | MCQs | Short responses | Explanation words: min–max | Mean |',
             '|---|---:|---:|---:|---:|']
    for f in record['files']:
        lines.append(f'| `{f["file"]}` | {f["mcq"]} | {f["short_response"]} | {f["explanation_min_words"]}–{f["explanation_max_words"]} | {f["explanation_mean_words"]} |')
    lines += ['', '## Checks passed', '',
              'Every question has exactly one Answer panel followed by one Explanation panel, both with `collapse="true"`. Every weekly question has its reviewed stable ID. Each reused exam MCQ matches the full weekly prompt, options, and correct answer. All exam short-response prompts are matched explicitly. Every narrative is multi-paragraph and has a course-source note and working source-level study-guide link.', '',
              'Calculations include the formula, substitution, units, conversion where needed, and interpretation. Mechanism questions explain the causal sequence. MCQs discuss the alternatives; essays explain all requested elements and relevant assumptions. Content is grounded in the supplied lectures and Silverthorn chapters; the examination-format item cites the supplied announcement. This is an editorial and structural audit, not a claim of independent expert certification.', '',
              '## Maintenance', '',
              'Curated narratives are in `assessment/detailed-explanations/`. Run `python3 scripts/expand_explanations.py --apply` after revising narratives; then render and run `python3 scripts/expand_explanations.py --check --html docs`. The updater refuses unreviewed changes to question or answer text. No original source PDFs are added to the public repository.', '']
    return '\n'.join(lines)


class PageInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.headers = []
        self.ids = {}
        self.duplicates = []
        self.links = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        element_id = a.get('id')
        if element_id:
            if element_id in self.ids:
                self.duplicates.append(element_id)
            self.ids[element_id] = a
        if 'callout-header' in (a.get('class') or '').split() and a.get('data-bs-toggle') == 'collapse':
            self.headers.append(a)
        if tag == 'a' and a.get('href'):
            self.links.append(a['href'])


def inspect_html(output_dir: Path, record: dict) -> dict:
    result = []
    for f in record['files']:
        relative = str(Path(f['file']).with_suffix('.html'))
        path = output_dir / relative
        require(path.is_file(), f'Missing rendered page: {relative}')
        parser = PageInspector()
        parser.feed(path.read_text(encoding='utf-8'))
        expected = 2 * f['questions']
        require(len(parser.headers) == expected, f'{relative}: expected {expected} collapsible panels, got {len(parser.headers)}')
        require(not parser.duplicates, f'{relative}: duplicate IDs: {parser.duplicates}')
        for a in parser.headers:
            require(a.get('aria-expanded') == 'false', f'{relative}: a panel starts expanded')
            require('collapsed' in (a.get('class') or '').split(), f'{relative}: missing collapsed header state')
            selector = a.get('data-bs-target') or ''
            target = a.get('aria-controls') or selector.lstrip('#')
            require(target in parser.ids, f'{relative}: missing collapse target {target}')
            classes = (parser.ids[target].get('class') or '').split()
            require(selector == '#' + target or
                    (selector.startswith('.') and selector[1:] in classes),
                    f'{relative}: collapse selector does not match its controlled panel')
            require('collapse' in classes and 'show' not in classes, f'{relative}: panel body initially open')
        guide_links = [h for h in parser.links if '../study-guides/' in h]
        require(len(guide_links) >= f['questions'], f'{relative}: missing study-guide links')
        for href in guide_links:
            target = href.split('#')[0].split('?')[0]
            require(target.endswith('.html') and (path.parent / target).is_file(), f'{relative}: broken guide link {href}')
        result.append({'page': relative, 'questions': f['questions'], 'closed_answer_and_explanation_panels': expected,
                       'duplicate_ids': 0, 'study_guide_links_valid': True})
    return {'pages': result, 'total_closed_panels': sum(r['closed_answer_and_explanation_panels'] for r in result),
            'all_passed': True}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--apply', action='store_true')
    group.add_argument('--check', action='store_true')
    ap.add_argument('--html', type=Path)
    args = ap.parse_args()
    updates, record = build_update()
    report_text = json.dumps(record, ensure_ascii=False, indent=2) + '\n'
    if args.apply:
        for relative, text in updates.items():
            if (ROOT / relative).read_text(encoding='utf-8') != text:
                atomic_write(ROOT / relative, text)
        atomic_write(AUDIT, report_text)
        atomic_write(ROOT / 'EXPLANATION_DETAIL_AUDIT.md', markdown_audit(record))
    else:
        for relative, text in updates.items():
            require((ROOT / relative).read_text(encoding='utf-8') == text, f'{relative}: curated explanations not applied')
        require(AUDIT.exists() and AUDIT.read_text(encoding='utf-8') == report_text, 'Source audit is missing or stale')
    if args.html:
        rendered = inspect_html(args.html.resolve(), record)
        atomic_write(ROOT / 'assessment/explanation-html-audit.json', json.dumps(rendered, indent=2) + '\n')
        print(f'Rendered HTML: {len(rendered["pages"])} pages, {rendered["total_closed_panels"]} panels initially closed; links valid.')
    print('PASS: 244 detailed explanations; questions, choices, answer keys, counts, and exam instructions unchanged.')
    for f in record['files']:
        print(f'{f["file"]}: {f["questions"]} explanations, {f["explanation_min_words"]}–{f["explanation_max_words"]} words, mean {f["explanation_mean_words"]}')


if __name__ == '__main__':
    main()
