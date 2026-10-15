"""Exam provenance is separate from work titles and author bylines."""
import json
from pathlib import Path
import re

REVIEWED=json.loads((Path(__file__).parent/'data/exam_metadata.json').read_text())


def work_metadata(kind,index,body,fallback):
    reviewed=REVIEWED.get(kind,{}).get(str(index))
    if reviewed: return reviewed['title'],reviewed['author']
    citations=re.findall(r'(?:节选自|选自|摘编自)\s*([^《\n]{0,30})《([^》]+)》',body)
    if kind=='classical':
        if not citations: citations=[('',title) for title in re.findall(r'[（(]\s*《([^》]+)》[）)]',body[-1000:])]
        if citations:
            titles=list(dict.fromkeys(re.sub(r'\s+','',t).replace('•','·').replace('*','·').replace('通鉴经事本末','通鉴纪事本末') for _,t in citations))
            compilers={'明史':'张廷玉等','宋史':'脱脱等','旧唐书':'刘昫等','北史':'李延寿','宋书':'沈约','后汉书':'范晔','晋书':'房玄龄等','史记':'司马迁','宋史纪事本末':'陈邦瞻','通鉴纪事本末':'袁枢','说苑':'刘向（编）','战国策':'刘向（编）'}
            authors=list(dict.fromkeys(compilers.get(t.split('·')[0],'编者待核对') for t in titles))
            return ' / '.join(titles)+'（节选）',' / '.join(authors)
        return '篇名待核对','编者待核对'
    if kind=='practical' and str(index)=='11':return '一代通儒顾炎武','署名待核对'
    if not re.search(r'材料[一二三四]',body):
        lines=[x.strip() for x in body.splitlines() if x.strip()]
        for i,line in enumerate(lines[:12]):
            text=re.sub(r'\s+','',line)
            if text in {'文学','实用','古代诗歌'}:continue
            if not 2<=len(text)<=25 or re.search(r'阅读|完成|小题|材料|文本[一二三]|摘编|选自|[，,。！？；：]|分[）)]|^[\d一二三四五六]+[、．.]',text):continue
            if re.search(r'[《》〈〉]',text):continue
            author='署名待核对'
            if i+1<len(lines):
                possible=re.sub(r'^(?:【[^】]+】|\[[^]]+\])','',re.sub(r'\s+','',lines[i+1]))
                if re.fullmatch(r'[\u4e00-\u9fff·•]{2,12}',possible):author=possible.replace('•','·')
            if text=='朱东润自传':author='朱东润'
            return text,author
    publications={'人民日报','光明日报','参考消息','中国青年报','文汇报'}
    works=[]
    for author,title in citations:
        title=re.sub(r'\s+','',title);author=re.sub(r'\s+','',author).replace('•','·')
        if title in publications or any(t==title for t,_ in works):continue
        if not re.fullmatch(r'[\u4e00-\u9fff·]{2,12}',author) or author in {'社论','记者','编者'}:author='署名待核对'
        works.append((title,author))
    if works:return ' / '.join(t for t,_ in works),' / '.join(a for _,a in works)
    return '篇名待核对','署名待核对'
