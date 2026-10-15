"""Packaged original readings and licensed reading questions; no runtime crawling."""
import json
from pathlib import Path

from .builtin_notes import rule_notes,RULE_SOURCE

DATA=Path(__file__).parent/'data'
READINGS=json.loads((DATA/'expanded_readings.json').read_text())
MODERN=json.loads((DATA/'expanded_modern_questions.json').read_text())
POINT_FIELDS=('name','evidence','learning_goal','explanation','foundation','consolidation','extension')


def extend_catalog(entries):
    for row in READINGS+MODERN:
        notes=rule_notes(row['title'],row['genre'],row['body'])
        entries.append(dict(id=row['id'].replace('expanded:','extra-').replace(':','-'),
            title=row['title'],author=row['author'],genre=row['genre'],content=row['body'],
            collection='公开真题材料' if row.get('questions') else '训练材料',
            points=[{key:n[key] for key in POINT_FIELDS} for n in notes],analysis_source=RULE_SOURCE,
            source=row['source_label'],source_url=row['source_url'],scope=row['scope'],text_status=row['scope'],
            books=[],recommended=False,sections=[],directory_note='',textbook_editions=[],
            available=True,has_analysis=bool(notes),has_guide=False,guide=None,reading_url='',reading_note='',
            full_text='',full_text_label='',supplemental=True,exam_year=row.get('year',''),exam_region=row.get('region','')))
