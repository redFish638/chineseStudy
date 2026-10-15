"""Public-source material bank, controlled knowledge tags, and explainable retrieval."""
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from . import catalog

DATA = Path(__file__).parent/'data'
SOURCE_TYPES = {'textbook': '课文选篇', 'gaokao': '高考真题', 'mock': '模拟试题', 'public': '公开文集', 'bank': '其他题库'}
TAXONOMY = [
    ('imagery', '意象与意境', r'意象|意境|景物|景色|写景|环境描写|山水|写山|田园|边塞'),
    ('emotion', '思想情感', r'情感|感情|思乡|思念|情绪|心境|感慨|身世|悲秋|伤今|主旨|寄托|抒情'),
    ('metaphor', '比喻', r'比喻|喻体|本体'),
    ('personification', '拟人', r'拟人'),
    ('symbol', '象征与托物言志', r'象征|托物言志'),
    ('parallel', '对偶与排比', r'对偶|对仗|对举|排比'),
    ('real-imagined', '虚实结合与联想', r'虚实|虚写|实写|想象|联想'),
    ('synesthesia', '通感', r'通感|感官转换'),
    ('contrast', '对比与衬托', r'对比|对照|衬托|烘托|反衬'),
    ('motion', '动静结合与以声衬静', r'动静|衬静|以声|鸟鸣|犬吠鸡鸣'),
    ('wording', '炼字与词句赏析', r'炼字|叠词|动词|词语|关键词|词句|语言节奏|语言风格'),
    ('character', '人物形象', r'人物|形象特点|性格|品质'),
    ('detail', '细节描写', r'细节|动作描写|心理描写|神态描写|肖像'),
    ('structure', '情节与结构', r'结构|情节|照应|线索|伏笔|铺垫|章法|首尾|开头|结尾'),
    ('narration', '叙述视角与顺序', r'叙述|叙事|人称|插叙|倒叙|顺叙|视角'),
    ('argument', '论点与论证', r'论点|论证|论据|观点|主张'),
    ('information', '信息筛选与概括', r'筛选|概括|归纳|信息|材料比较|文本理解|题意'),
    ('classical-word', '文言实词与古今异义', r'实词|古今异义|语境释义|文言词义'),
    ('classical-particle', '文言虚词', r'虚词'),
    ('conversion', '词类活用', r'活用|意动|使动'),
    ('translation', '文言句式与翻译', r'翻译|句式|省略句|判断句|宾语前置|状语后置|被动句|倒装'),
]
TAG_LABELS = {key: label for key, label, _ in TAXONOMY}
TAG_PATTERNS = {key: re.compile(pattern) for key, _, pattern in TAXONOMY}
METHODS = {'metaphor','personification','symbol','parallel','real-imagined','synesthesia','motion','contrast','narration','classical-word','classical-particle','conversion','translation'}


def normalized(text):
    return ''.join(re.findall(r'\w', unicodedata.normalize('NFKC', text).lower()))


def body_hash(text):
    return hashlib.sha256(normalized(text).encode()).hexdigest()


def tags_in(text):
    return [key for key, pattern in TAG_PATTERNS.items() if pattern.search(text)]


def point_tags(name, description=''):
    found = tags_in(name)
    if '论证' in name or '论点' in name or '论据' in name:
        return ['argument']
    methods = [x for x in found if x in METHODS]
    return methods or found or tags_in(description)[:3]


def safe_score(value):
    try: return max(1, min(100, int(value)))
    except (ValueError, TypeError): return 10


def split_question(question, genre):
    # Preserve the original complete question if segmentation is uncertain.
    minimum = 50 if genre == '诗歌' else 180
    pattern = r'(?:^|\n)\s*(?:[（(]\s*[1-4]\s*[）)]|(?:1[0-9]|[1-9])[．.、])'
    for match in re.finditer(pattern, question):
        if match.start() >= minimum:
            return question[:match.start()].strip(), question[match.start():].strip()
    return question.strip(), question.strip()


def extract_title(material, fallback):
    for line in material.splitlines()[:12]:
        text = re.sub(r'\s+', '', line)
        if 2 <= len(text) <= 25 and not re.search(r'阅读|完成|小题|第.*题|注|分）|分\)|（\d|\(\d|——|\d[．.]', text):
            if not re.search(r'[，。！？；：“”]', text):
                return text
    return fallback


def notes_from_analysis(text, material):
    notes = []
    for tag in tags_in(text):
        match = TAG_PATTERNS[tag].search(text)
        start = max(0, match.start()-60)
        excerpt = text[start:start+450].strip()
        notes.append({'name': TAG_LABELS[tag], 'tags': [tag],
                      'evidence': catalog.quoted_evidence(excerpt+'\n'+text, material),
                      'explanation': excerpt})
    return notes


def material_record(id, title, author, genre, source_type, body, source_url, source_label,
                    notes, questions, year='', region='', review='公开来源整理，需教师复核', tags=None):
    tag_ids = tags if tags is not None else list(dict.fromkeys(t for note in notes for t in note['tags']))
    result = dict(id=id, title=title[:200], author=author[:100], genre=genre, source_type=source_type,
                  body=body, content_hash=body_hash(body), source_url=source_url, source_label=source_label,
                  year=year, region=region[:100], review=review, tags=tag_ids, notes=notes, questions=questions)
    result['revision'] = hashlib.sha256(json.dumps(result, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return result


def seed_records():
    result = []
    curated = [x for x in catalog.CATALOG if not x['id'].startswith('gaokao-') and not x.get('curriculum_added')]
    for entry in curated:
        notes = [{**p, 'tags':point_tags(p['name'])} for p in entry['points']]
        questions = []
        for i, p in enumerate(entry['points']):
            for level, key in [('基础','foundation'), ('巩固','consolidation'), ('拓展','extension')]:
                questions.append({'id':f'curated:{entry["id"]}:{i}:{level}', 'prompt':p[key]+'。请结合原文作答。',
                                  'reference':'教师需按题意完善：'+p['explanation'],
                                  'analysis':'自编练习草稿；需教师完善采分点。', 'max_score':10, 'level':level, 'tags':point_tags(p['name']), 'source':'自编草稿'})
        result.append(material_record('curated:'+entry['id'], entry['title'],entry['author'],entry['genre'],
                      'textbook' if entry['collection']=='高中课文' else 'bank', entry['content'],entry.get('source_url',''),entry['source'],notes,questions))
    datasets = [('poetry','gaokao_poetry.json','诗歌','古代诗歌阅读'),
                ('classical','gaokao_classical.json','文言文','文言文阅读'),
                ('literary','gaokao_literary.json','阅读','文学类阅读'),
                ('practical','gaokao_practical.json','阅读','实用类阅读')]
    filenames = {'poetry':'Ancient_Poetry','classical':'Classical_Chinese','literary':'Literary_Text','practical':'Practical_Text'}
    for key, filename, genre, kind in datasets:
        records = json.loads((DATA/filename).read_text())['example']
        source_url = 'https://github.com/OpenLMLab/GAOKAO-Bench/blob/main/Data/Subjective_Questions/2010-2022_Chinese_Language_'+filenames[key]+'_Reading.json'
        for record in records:
            id = f'gaokao:{key}:{record["index"]}'
            body, prompt = split_question(record['question'], genre)
            title = extract_title(body, kind)
            published = record.get('analysis','') or record.get('answer','')
            notes = notes_from_analysis(published, body)
            # Exam-specific features such as translation may be requested in the prompt.
            tag_ids = list(dict.fromkeys([t for n in notes for t in n['tags']]+tags_in(prompt)))
            question = {'id':id+':original','prompt':prompt,'reference':record.get('answer',''),
                        'analysis':record.get('analysis',''),'max_score':safe_score(record.get('score')), 'level':'未分层',
                        'tags':tag_ids,'source':'原题整理（非官方校订版）'}
            result.append(material_record(id,title,'见材料署名',genre,'gaokao',body,source_url,
                          'GAOKAO-Bench公开数据，Apache-2.0；年份卷别据原数据',notes,[question],
                          year=str(record['year']),region=str(record['category']),tags=tag_ids))
    poems = json.loads((DATA/'tang_poems.json').read_text())
    curated_names = {(normalized(x['title'].split('（')[0]),normalized(x['author'])) for x in curated}
    for i, poem in enumerate(poems):
        title, author = poem.get('title','无题'), poem.get('author','佚名')
        if (normalized(title),normalized(author)) in curated_names: continue
        paragraphs = poem.get('paragraphs',[])
        if not paragraphs: continue
        body = '\n'.join(paragraphs)
        tags = tags_in(' '.join(poem.get('tags',[])))
        result.append(material_record(f'poetry:tang:{i}',title,author,'诗歌','public',body,
                      'https://github.com/chinese-poetry/chinese-poetry/blob/master/全唐诗/唐诗三百首.json',
                      'chinese-poetry公开文集，MIT；保留原数据字形',[],[],tags=tags,
                      review='主题标签来自原文集，不等于题目考点；暂无配套解析和原题'))
    known = {x['content_hash'] for x in result}
    for entry in catalog.CATALOG:
        if not entry.get('curriculum_added') or not entry['available']: continue
        digest = body_hash(entry['content'])
        if digest in known: continue
        known.add(digest)
        result.append(material_record('curriculum:'+entry['id'],entry['title'],entry['author'],entry['genre'],
                      'textbook' if entry['books'] else 'public',entry['content'],entry['source_url'],
                      entry['source']+' '+entry['text_status'],[],[],tags=[],
                      review='公开原文或选录，教材范围与字句待核对；暂无审校知识点与配套题目'))
    return result


def same_work(candidate, current_body, current_title):
    a, b = normalized(candidate['body']), normalized(current_body)
    if a == b or (min(len(a),len(b)) >= 35 and (a in b or b in a)):
        return True
    # Editions can differ in punctuation/characters; identical work titles still need exclusion.
    title = normalized(current_title.split('（')[0].split('(')[0])
    other = normalized(candidate['title'].split('（')[0].split('(')[0])
    generic={normalized(x) for x in ['文言文阅读','古代诗歌阅读','文学类阅读','实用类阅读','文学类文本阅读','实用类文本阅读','阅读材料','无题','杂诗']}
    return bool(title and title == other and title not in generic)


def recommend(records, point_name, point_description, current_body, current_title, current_genre, tag=None):
    query_tags = [tag] if tag else point_tags(point_name, point_description)
    ranked = []
    seen = set()
    for record in records:
        if same_work(record, current_body, current_title): continue
        overlap = [t for t in query_tags if t in record['tags']]
        if not overlap: continue
        notes = [n for n in record['notes'] if any(t in overlap for t in n.get('tags',[]))]
        evidence = next((n['evidence'] for n in notes if n.get('evidence') in record['body']), '')
        score = 30*len(overlap)+(10 if notes else 0)+(5 if record['questions'] else 0)+(3 if record['genre']==current_genre else 0)
        ranked.append((score, record, overlap, notes, evidence))
    ranked.sort(key=lambda x:(-x[0],x[1]['id']))
    result=[]
    for score, record, overlap, notes, evidence in ranked:
        if record['content_hash'] in seen: continue
        seen.add(record['content_hash'])
        result.append({**record, 'match_tags':overlap, 'match_reason':'共同知识点：'+'、'.join(TAG_LABELS[t] for t in overlap),
                       'match_basis':'来源解析标签' if notes else '来源主题标签（关联较弱）', 'match_evidence':evidence,
                       'match_explanation':notes[0].get('explanation','') if notes else '仅按文集主题标签匹配，尚无教研解析，需核对是否适合此知识点。'})
    return query_tags,result
