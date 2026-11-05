#!/usr/bin/env python3
"""Populate independently collapsed Explanation panels from reviewed Markdown.

Canonical narratives live in assessment/explanations/. Questions and answer keys
are retained; an explicit wording clarification narrows the cardiac-cell census.
Repeated exam MCQs are matched using their complete stem AND options, never by
question number or topic alone. This script is idempotent and fails on gaps.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEEKS = {
    5: 'week05-sensory',
    6: 'week06-vision-muscle',
    7: 'week07-cardiac',
    8: 'week08-vascular-blood',
}
HEAD = re.compile(r'^### Question (\d+)[^\n]*\n', re.M)
PANEL = re.compile(r'^::: \{[^\n]*title="Explanation"[^\n]*\}\n.*?^:::[ \t]*$', re.M | re.S)
ANSWER = re.compile(r'^::: \{[^\n]*title="Answer"[^\n]*\}\n(.*?)^:::[ \t]*$', re.M | re.S)
EXAM_SR = {1: [1, 2, 3, 4], 2: [3, 4, 5, 6], 3: [5, 6, 7, 8]}
EXAM_WEEK = {1: 5, 2: 6, 3: 6, 4: 6, 5: 7, 6: 7, 7: 7, 8: 7}


def load_narratives() -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted((ROOT / 'assessment/explanations').glob('*.md')):
        text = path.read_text(encoding='utf-8')
        headings = list(re.finditer(r'^## ([a-z0-9-]+)\s*$', text, re.M))
        for i, match in enumerate(headings):
            key = match.group(1)
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            body = text[match.end():end].strip()
            if key in out or not body:
                raise ValueError(f'Duplicate or empty narrative: {key}')
            if len(re.findall(r"\b[\w]+(?:[’'-][\w]+)*\b", body)) < 100:
                raise ValueError(f'Narrative too brief for review standard: {key}')
            out[key] = body
    expected = {f'w{w:02d}-{kind}{n:02d}' for w in WEEKS for kind, count in [('mc', 28), ('sr', 12)] for n in range(1, count + 1)}
    expected |= {f'exam-sr{n:02d}' for n in range(1, 9)}
    if set(out) != expected:
        raise ValueError(f'Narrative inventory mismatch; missing={sorted(expected-set(out))}; extra={sorted(set(out)-expected)}')
    return out


def split_questions(text: str):
    matches = list(HEAD.finditer(text))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        yield int(match.group(1)), match.start(), end, text[match.start():end]


def stem_key(block: str) -> str:
    without_heading = block.split('\n', 1)[1]
    stem = without_heading.split('::: {.callout-tip', 1)[0]
    return re.sub(r'\s+', ' ', stem).strip()


def source_note(key: str, week: int) -> str:
    if key.startswith('exam-sr'):
        n = int(key[-2:])
        return {1:'Lecture 13; Silverthorn (2019), Chapter 10.',2:'Lecture 15; Silverthorn (2019), Chapter 10.',3:'Lectures 16–17; Silverthorn (2019), Chapter 12.',4:'Lecture 17; Silverthorn (2019), Chapter 12.',5:'Lecture 19; Silverthorn (2019), Chapter 14.',6:'Lectures 19–20; Silverthorn (2019), Chapter 14; supplied mock-midterm cardiac-cycle task.',7:'Lecture 20; Silverthorn (2019), Chapter 14.',8:'Lecture 20; Silverthorn (2019), Chapter 14.'}[n]
    n = int(key[-2:]); sr = '-sr' in key
    if week == 5:
        lecture = 'Lecture 14' if (sr and 6 <= n <= 10) or (not sr and 14 <= n <= 24) else 'Lecture 13'
        return lecture + '; Silverthorn (2019), Chapter 10.'
    if week == 6:
        if (sr and n <= 4) or (not sr and (n <= 9 or n == 27)):
            return 'Lecture 15; Silverthorn (2019), Chapter 10.'
        return 'Lectures 16–17; Silverthorn (2019), Chapter 12; NMJ details in Lecture 16.'
    if week == 7:
        return 'Lectures 18–20; Silverthorn (2019), Chapter 14.'
    if not sr and n == 28:
        return 'Supplied “Topic: BPK205 Midterm 2” announcement, posted November 4, 2026.'
    if (sr and n >= 9) or (not sr and n >= 18):
        return 'Lecture 23; Silverthorn (2019), Chapter 16.'
    return 'Lectures 21–22; Silverthorn (2019), Chapter 15; supplied MAP tutorial where applicable.'


def render_panel(body: str, key: str, panel_id: str, week: int) -> str:
    note = source_note(key, week)
    return (f'::: {{.callout-note .question-explanation #explanation-{panel_id} collapse="true" title="Explanation"}}\n'
            + body + '\n\n**Course basis:** ' + note
            + f'\n\n**Review:** [Week {week} study guide](../study-guides/{WEEKS[week]}.qmd).\n:::')


def main() -> None:
    narratives = load_narratives()
    # Make a narrowly targeted correction to an overbroad biological claim.
    p = ROOT / 'practice/week07-cardiac.qmd'
    s = p.read_text(encoding='utf-8')
    s = s.replace('Most cells in the myocardium are:', 'Of the two excitable cardiac muscle-cell populations emphasized in lecture, the more abundant are:')
    s = s.replace('Most cardiac cells are contractile myocytes.', 'Contractile myocytes form the force-producing bulk of the cardiac muscle-cell population.')
    p.write_text(s, encoding='utf-8')
    index: dict[str, tuple[str, int]] = {}
    for week, name in WEEKS.items():
        text = (ROOT / 'practice' / f'{name}.qmd').read_text(encoding='utf-8')
        for number, _, _, block in split_questions(text):
            key = re.search(r'\{#(w\d{2}-(?:mc|sr)\d{2})\}', block.split('\n', 1)[0])
            if not key:
                raise ValueError(f'No stable question ID: {name} Q{number}')
            if number <= 28:
                signature = stem_key(block)
                if signature in index:
                    raise ValueError(f'Ambiguous weekly MCQ signature: {name} Q{number}')
                index[signature] = (key.group(1), week)
    report = []
    all_paths = [ROOT/'practice'/f'{n}.qmd' for n in WEEKS.values()]
    all_paths += [ROOT/'practice'/f'practice-midterm2-{n:02d}.qmd' for n in range(1, 4)]
    for path in all_paths:
        original = path.read_text(encoding='utf-8')
        replacements = []
        exam_match = re.search(r'midterm2-(\d+)', path.stem)
        exam = int(exam_match.group(1)) if exam_match else None
        week = next((w for w, name in WEEKS.items() if name == path.stem), None)
        entries = list(split_questions(original))
        expected_count = 28 if exam else 40
        if [x[0] for x in entries] != list(range(1, expected_count + 1)):
            raise ValueError(f'Question numbering/count mismatch: {path}')
        for number, start, end, block in entries:
            if exam:
                panel_id = f'exam{exam:02d}-q{number:02d}'
                if number <= 24:
                    if stem_key(block) not in index:
                        raise ValueError(f'Unmatched complete exam MCQ: {path.name} Q{number}')
                    key, source_week = index[stem_key(block)]
                else:
                    n = EXAM_SR[exam][number-25]
                    key, source_week = f'exam-sr{n:02d}', EXAM_WEEK[n]
            else:
                key = re.search(r'\{#(w\d{2}-(?:mc|sr)\d{2})\}', block.split('\n', 1)[0]).group(1)
                panel_id, source_week = key, week
            panels = list(PANEL.finditer(block))
            answers = list(ANSWER.finditer(block))
            if len(panels) != 1 or len(answers) != 1:
                raise ValueError(f'Expected one Answer and one Explanation: {path.name} Q{number}')
            body = narratives[key]
            m = panels[0]
            replacement = render_panel(body, key, panel_id, source_week)
            new_block = block[:m.start()] + replacement + block[m.end():]
            if ANSWER.search(new_block).group(1) != answers[0].group(1):
                raise AssertionError('Answer was altered while applying an explanation')
            replacements.append((start, end, new_block))
            words = len(re.findall(r"\b[\w]+(?:[’'-][\w]+)*\b", body))
            report.append({'page':str(path.relative_to(ROOT)), 'question':number, 'panel_id':panel_id, 'narrative_id':key, 'source_week':source_week, 'type':'mcq' if number <= (24 if exam else 28) else 'short-response', 'narrative_words':words, 'paragraphs':len(body.split('\n\n')), 'sha256':hashlib.sha256(body.encode()).hexdigest()})
        text = original
        for start, end, new_block in reversed(replacements):
            text = text[:start] + new_block + text[end:]
        marker = '<!-- detailed-explanations-v1 -->'
        if marker not in text:
            insertion = ('\n'+marker+'\n\n**Using the panels:** Try the question first. Open **Answer** to check the result, then open **Explanation** separately for the mechanism, reasoning, relevant distinctions, and worked steps. Both panels start closed.\n\n')
            front_end = re.search(r'\A---\n.*?\n---\n', text, re.S)
            text = text[:front_end.end()] + insertion + text[front_end.end():]
        path.write_text(text, encoding='utf-8')
    # Repair Python-escape artifacts in the original generated mathematics.
    for path in (ROOT/'study-guides').glob('*.qmd'):
        text = path.read_text(encoding='utf-8').replace('\times', r'\times')
        path.write_text(text, encoding='utf-8')
    summary = {'total_questions':len(report), 'weekly_questions':sum(1 for r in report if '/week' in r['page']), 'exam_questions':sum(1 for r in report if 'midterm' in r['page']), 'unique_narratives':len(narratives), 'minimum_words':min(r['narrative_words'] for r in report), 'maximum_words':max(r['narrative_words'] for r in report), 'mean_words':round(sum(r['narrative_words'] for r in report)/len(report),1), 'initially_collapsed':True, 'separate_answer_and_explanation':True}
    if summary['total_questions'] != 244:
        raise AssertionError(summary)
    (ROOT/'assessment/explanation-detail-audit.json').write_text(json.dumps({'summary':summary,'questions':report},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
