"""Audited poem-only spans from the unchanged GAOKAO-Bench source snapshot.

Keep source annotations and question requirements outside the poem body.
No spelling or punctuation corrections are inferred from the source text.
"""
import json
import re
from pathlib import Path

BODIES = json.loads((Path(__file__).parent/'data/exam_poetry_bodies.json').read_text())


def exam_poetry(record):
    raw = record['question'].strip()
    # Some source records flatten all line breaks, including numbered questions.
    question = next((m for m in re.finditer(r'[（(]\s*1\s*[）)]|(?:^|\n)\s*(?:1[0-9]|[1-9])[.．、]', raw) if m.start() > 50), None)
    prompt = raw[question.start():].strip() if question else raw
    prefix = raw[:question.start()] if question else raw
    note = re.search(r'【注(?:释)?】|\[注\](?=①|至公：)', prefix)
    annotations = prefix[note.start():].strip() if note else ''
    order = {'6':'诗歌顺序：第一首《含山店梦觉作》（韦庄）；第二首《宿渔家》（郭震）。',
             '28':'诗歌顺序：第一首《画眉鸟》（欧阳修）；第二首《画眉禽》（文同）。'}.get(str(record['index']), '')
    return BODIES[str(record['index'])], '\n\n'.join(x for x in [order, annotations, prompt] if x)
