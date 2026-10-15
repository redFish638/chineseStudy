"""Reusable teaching categories; article-specific names and evidence stay intact."""
import hashlib
import re
import unicodedata

from . import bank


def categories(name, description=''):
    # Saved descriptions also contain comparison tasks. They must not turn a
    # suggested future exercise into a category of the current article.
    if '\n解析：' in description:
        description = description.split('\n解析：', 1)[1].split('\n基础：', 1)[0]
    tags = bank.point_tags(name, description)
    if tags:
        return [dict(id='tag-'+tag, name=bank.TAG_LABELS[tag], tag=tag) for tag in tags]
    normalized = ' '.join(unicodedata.normalize('NFKC', name).casefold().split())
    return [dict(id=hashlib.sha256(normalized.encode()).hexdigest(), name=name, tag='')]


def grounded_note(note, body):
    if not note.get('evidence') or note['evidence'] not in body:
        return False
    explanation = re.sub(r'\s+', '', note.get('explanation', ''))
    # A generic technique paragraph does not establish a device in this text.
    return not (note.get('origin')=='source' and any(x in explanation for x in
        ['句首发语词', '分析谓语', '同时还要注意结构上的对称']))


def related_materials(group, records):
    if not group['tag']:
        return []
    eligible = []
    for record in records:
        notes = [n for n in record['notes'] if group['tag'] in n.get('tags', []) and grounded_note(n, record['body'])]
        if notes:
            eligible.append({**record, 'notes':notes})
    _, ranked = bank.recommend(eligible, group['name'], '', '', '', '', group['tag'])
    return [r for r in ranked if r['match_evidence'] and not any(
        bank.same_work(r, a['_content'], a['title']) for a in group['articles'].values())]


def article_links(title, body):
    title = {'錦瑟':'锦瑟', '蜀道難':'蜀道难'}.get(title,title)
    return [n for n in bank.KNOWLEDGE_LINKS.get(title, []) if n['evidence'] in body]
