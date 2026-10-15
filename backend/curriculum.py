"""Source-attributed curriculum metadata; directories never masquerade as texts."""
import json
from pathlib import Path
import re

DIRECTORY_SOURCES = [
    {'name':'统编五册目录核对（公开镜像所载印次）', 'url':'https://github.com/Hello-Fx/TchMaterial/tree/main/语文'},
    {'name':'跨印次课文索引（116条参考）', 'url':'https://github.com/Midshow/yuwen-jiaocan/blob/main/references/课文索引.md'},
    {'name':'2020课标推荐参考清单（72篇）', 'url':'https://github.com/zhshy/gaozhong-yuwen-kebiao/blob/main/references/fulu.md'},
]

def title_key(title):
    return re.sub(r'[^\w]', '', title.replace('（节选）','').replace('（并序）','并序').replace('曾晳','曾皙'))


def extend_catalog(catalog):
    records = json.loads((Path(__file__).parent/'data/curriculum.json').read_text())
    original = list(catalog)
    for row in records:
        match = next((x for x in original if title_key(x['title']) == title_key(row['title'])), None)
        metadata = {k:row[k] for k in ['books','recommended','sections','directory_note']}
        if match:
            match.update(metadata)
            continue  # Preserve existing article bodies, analyses, and stable identifiers.
        readable = bool(row['content'].strip())
        catalog.append(dict(id=row['id'],title=row['title'],author=row['author'],genre=row['genre'],
            collection='高中课文' if row['books'] else '推荐篇目', content=row['content'],points=[],
            edition='统编参考目录 / 2020推荐参考（非所有版本完整收录）',
            source='公开古典原文整理；未附审校知识点。' if readable else '仅篇名与目录信息，尚未收录可用原文。',
            source_url=row['text_source_url'] or DIRECTORY_SOURCES[0 if row['books'] else 2]['url'],
            scope=row['text_status'],text_status=row['text_status'],curriculum_added=True,**metadata))
    for entry in catalog:
        entry.setdefault('books',[])
        entry.setdefault('recommended',False)
        entry.setdefault('sections',[])
        entry['available'] = bool(entry['content'].strip())
        entry['has_analysis'] = bool(entry['points'])
        entry.setdefault('text_status',entry['scope'])
    # Curriculum browsing comes first; preserve the ordering of the original curated picks.
    catalog.sort(key=lambda x: (not bool(x['books']), x['collection']=='公开真题材料'))
