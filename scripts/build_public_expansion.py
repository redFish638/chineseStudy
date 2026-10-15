"""Build a reviewed source snapshot, never crawl at application startup.
Inputs: fresh GuWen original JSON, chinese-poetry Song300 JSON, GAOKAO-Bench zip.
Only public-domain original fields and the Apache-2.0 benchmark are retained.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend import bank


def load(path):return json.loads(Path(path).read_text())
def content(row):return ('\n'.join(row['content']) if isinstance(row['content'],list) else row['content']).strip()
def fingerprint(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build(guwen_path,song_path,exam_path):
    base=[r for r in bank.seed_records() if not r['id'].startswith('expanded:')]
    known={bank.body_hash(r['body']) for r in base}
    readings=[];skipped=[]
    def add(kind,title,author,body,url,label,scope='文集原文'):
        digest=bank.body_hash(body)
        if digest in known:
            skipped.append(dict(kind=kind,title=title,reason='规范化正文重复'));return
        if not title or len(author)<2 or len(body)<12 or len(body.encode())>60000:
            skipped.append(dict(kind=kind,title=title,reason='元数据不完整、正文过短或超出安全录入长度'));return
        known.add(digest)
        key=hashlib.sha256((title+'\n'+author+'\n'+digest).encode()).hexdigest()[:24]
        readings.append(dict(id='expanded:'+kind+':'+key,title=title,author=author,
            genre='文言文' if kind=='guwen' else '诗歌',body=body,source_url=url,source_label=label,scope=scope))
    for row in load(guwen_path):
        author=row['author'].strip()
        if author in {'礼赞','伽腽肭'}:
            skipped.append(dict(kind='guwen',title=row['title'],reason='原始署名需复核'));continue
        add('guwen',row['title'].strip(),author,content(row),
            'https://github.com/weiyinfu/GuWen/blob/master/guwen.json',
            'GuWen 古代公版原文字段；未复制现代译文、鉴赏或注释字段')
    for row in load(song_path):
        body='\n'.join(row['paragraphs']).strip();first=re.split(r'[，。！？；、\n]',body)[0].strip()
        title=row['rhythmic'].strip()+'·'+first
        add('song',title,row['author'].strip(),body,
            'https://github.com/chinese-poetry/chinese-poetry/blob/master/宋词/宋词三百首.json',
            'chinese-poetry 宋词三百首选本，MIT；以词牌及首句识别作品，保留来源署名与字形')
    archive=zipfile.ZipFile(exam_path)
    name=next(n for n in archive.namelist() if '/Data/Objective_Questions/' in n and n.endswith('_Chinese_Modern_Lit.json'))
    raw=archive.read(name);rows=json.loads(raw)['example'];modern=[];by_body={};question_hashes=set();audit=[]
    url='https://github.com/OpenLMLab/GAOKAO-Bench/blob/6dbb24f8d8439041e5431c4c184a582182a6ce9c/Data/Objective_Questions/2010-2022_Chinese_Modern_Lit.json'
    header=re.compile(r'(?m)(?:^|\n)\s*(\d{1,2})[．.、]\s*|[（(]\s*([123])\s*[）)]\s*')
    for row in rows:
        question=row['question'];marks=list(header.finditer(question));valid=[]
        for i,mark in enumerate(marks):
            segment=question[mark.start():marks[i+1].start() if i+1<len(marks) else len(question)]
            if all(re.search(c+r'[．.、]',segment) for c in 'ABCD'):valid.append(mark)
        answers=row['answer']
        if len(valid)!=len(answers) or any(not re.fullmatch('[ABCD]',a) for a in answers):
            audit.append(dict(index=row['index'],accepted=False,reason='题号、选项与答案数量不能可靠对齐'));continue
        body=question[:valid[0].start()].strip()
        body=re.sub(r'^(?:[一二三四五]+、)?现代文阅读[^\n]*\n','',body)
        body=re.sub(r'^\s*\d+[．.]\s*[（(][^\n]*阅读[^\n]*\n','',body)
        if len(body)<180:
            audit.append(dict(index=row['index'],accepted=False,reason='缺少完整阅读材料'));continue
        cite=re.findall(r'(?:摘编自|摘自|选自|摘编)\s*([^《\n]{0,45})《([^》]+)》',body)
        if not cite:
            audit.append(dict(index=row['index'],accepted=False,reason='出处篇名待核对'));continue
        author,title=cite[-1];title=re.sub(r'\s+','',title);author=re.sub(r'\s+','',author)
        # Keep factual attributions. Do not invent a surname from a damaged OCR field.
        known_authors={1:'金开诚',6:'署名待核对',16:'署名待核对',19:'叶嘉莹',21:'周振甫'}
        author=known_authors.get(int(row['index']),author)
        if not re.fullmatch(r'[\u4e00-\u9fff·]{2,12}',author):author='署名待核对'
        titles={19:'论杜甫七律之演进及其承先启后之成就',21:'谈谈〈古文观止〉'}
        title=titles.get(int(row['index']),title)
        digest=bank.body_hash(body)
        packet=by_body.get(digest)
        if packet is None:
            packet=dict(id='expanded:gaokao-modern:'+str(row['index']),title=title,author=author,genre='阅读',
                body=body,source_url=url,source_label='GAOKAO-Bench现代文阅读，Apache-2.0；原数据非官方校订版',
                year=str(row['year']),region=str(row['category']),scope='试题所附材料',questions=[])
            modern.append(packet);by_body[digest]=packet
        for i,mark in enumerate(valid):
            number=int(mark.group(1) or mark.group(2))
            prompt=question[mark.start():valid[i+1].start() if i+1<len(valid) else len(question)].strip()
            # Two 2022 OCR items contain a stray page number immediately before an option.
            prompt=re.sub(r'(?<=[）。])\s*3(?=[ABCD][．.])','\n',prompt)
            key=hashlib.sha256((digest+bank.normalized(prompt)+answers[i]).encode()).hexdigest()
            if key in question_hashes:continue
            question_hashes.add(key)
            full_analysis=row['analysis'].strip()
            am=list(re.finditer(r'(?m)^\s*(?:[（(](\d+)[）)]|【(\d+)题详解】)',full_analysis))
            own=[j for j,m in enumerate(am) if int(m.group(1) or m.group(2))==number]
            if len(own)==1:
                j=own[0];explanation=full_analysis[am[j].start():am[j+1].start() if j+1<len(am) else len(full_analysis)].strip()
            else:explanation='本组来源解析（请定位第'+str(number)+'题）：\n'+full_analysis
            tags=['argument'] if '论证' in prompt[:100] else ['information']
            packet['questions'].append(dict(id=packet['id']+':'+str(number),prompt=prompt,
                reference='正确选项：'+answers[i]+'。',analysis=explanation,max_score=int(row['score']),
                level='未分层',tags=tags,source=str(row['year'])+'年'+str(row['category'])+'；GAOKAO-Bench公开整理'))
        audit.append(dict(index=row['index'],accepted=True,source_answers=len(answers),parsed_questions=len(valid)))
    data=ROOT/'backend/data'
    (data/'expanded_readings.json').write_text(json.dumps(readings,ensure_ascii=False,indent=2)+'\n')
    (data/'expanded_modern_questions.json').write_text(json.dumps(modern,ensure_ascii=False,indent=2)+'\n')
    # Exact upstream file retained for attribution and independent answer-alignment checks.
    (data/'gaokao_modern_objective.json').write_bytes(raw)
    manifest=dict(sources={'guwen_sha256':fingerprint(guwen_path),'song_sha256':fingerprint(song_path),
        'gaokao_commit':'6dbb24f8d8439041e5431c4c184a582182a6ce9c','gaokao_zip_sha256':fingerprint(exam_path)},
        original_readings=len(readings),modern_materials=len(modern),modern_questions=sum(len(r['questions']) for r in modern),
        skipped_originals=skipped,exam_audit=audit,
        external_only=[dict(url='https://github.com/OpenLMLab/GAOKAO-Bench-Updates',reason='2023/2024补充仓库未见独立许可证，本次仅提供入口，未随应用打包')])
    (data/'expansion_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k not in {'sources','skipped_originals','exam_audit','external_only'}},ensure_ascii=False))
    print('exam rejected:',[r for r in audit if not r['accepted']])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--guwen',required=True);parser.add_argument('--song',required=True);parser.add_argument('--gaokao-zip',required=True);args=parser.parse_args()
    build(args.guwen,args.song,args.gaokao_zip)
