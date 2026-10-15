"""知语教学工作流。默认本地 SQLite，DATABASE_URL 支持 PostgreSQL/MySQL。"""
import hashlib
import json
import hmac
import os
import secrets
import time
import unicodedata
from contextlib import asynccontextmanager
from pathlib import Path
import threading

from . import analysis, catalog, bank
from .curriculum import DIRECTORY_SOURCES
from .builtin_notes import RULE_SOURCE, AUTHORED_SOURCE, rule_notes

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, create_engine, delete, select, func, or_
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

ROOT = Path(__file__).resolve().parent.parent
URL = os.getenv('DATABASE_URL', f'sqlite:///{ROOT}/data/zhiyu.db')
if URL.startswith('sqlite:'):
    (ROOT / 'data').mkdir(exist_ok=True)
engine = create_engine(URL, pool_pre_ping=True, connect_args={'check_same_thread': False} if URL.startswith('sqlite:') else {})
DB = sessionmaker(engine, expire_on_commit=False)
SECURE = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'

class Base(DeclarativeBase):
    pass

class Admin(Base):
    __tablename__ = 'zhiyu_admins'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))

class LoginSession(Base):
    __tablename__ = 'zhiyu_login_sessions'
    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires: Mapped[int] = mapped_column(Integer)

class Article(Base):
    __tablename__ = 'zhiyu_articles'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    genre: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)

class Point(Base):
    __tablename__ = 'zhiyu_points'
    id: Mapped[int] = mapped_column(primary_key=True)
    article_id: Mapped[int] = mapped_column(ForeignKey('zhiyu_articles.id'), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default='')

class Question(Base):
    __tablename__ = 'zhiyu_questions'
    id: Mapped[int] = mapped_column(primary_key=True)
    point_id: Mapped[int] = mapped_column(ForeignKey('zhiyu_points.id'), index=True)
    level: Mapped[str] = mapped_column(String(10))
    material: Mapped[str] = mapped_column(Text)
    prompt: Mapped[str] = mapped_column(Text)
    reference: Mapped[str] = mapped_column(Text)
    rubric: Mapped[str] = mapped_column(Text)
    max_score: Mapped[int] = mapped_column(Integer, default=10)

class Assignment(Base):
    __tablename__ = 'zhiyu_assignments'
    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey('zhiyu_questions.id'), index=True)
    student: Mapped[str] = mapped_column(String(100))
    created: Mapped[int] = mapped_column(Integer)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey('zhiyu_assignments.id'), nullable=True)

class Submission(Base):
    __tablename__ = 'zhiyu_submissions'
    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey('zhiyu_assignments.id'), unique=True)
    answer: Mapped[str] = mapped_column(Text)
    submitted: Mapped[int] = mapped_column(Integer)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feedback: Mapped[str] = mapped_column(Text, default='')
    issue: Mapped[str] = mapped_column(String(300), default='')
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)

class BankMaterial(Base):
    __tablename__ = 'zhiyu_bank_materials'
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    author: Mapped[str] = mapped_column(String(100))
    genre: Mapped[str] = mapped_column(String(20), index=True)
    source_type: Mapped[str] = mapped_column(String(20), index=True)
    body: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    source_label: Mapped[str] = mapped_column(Text)
    year: Mapped[str] = mapped_column(String(20))
    region: Mapped[str] = mapped_column(String(100))
    review: Mapped[str] = mapped_column(String(200))
    tags_json: Mapped[str] = mapped_column(Text)
    notes_json: Mapped[str] = mapped_column(Text)
    revision: Mapped[str] = mapped_column(String(64))
    managed: Mapped[bool] = mapped_column(Boolean, default=True)

class BankExercise(Base):
    __tablename__ = 'zhiyu_bank_exercises'
    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    material_id: Mapped[str] = mapped_column(ForeignKey('zhiyu_bank_materials.id'), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    reference: Mapped[str] = mapped_column(Text)
    analysis: Mapped[str] = mapped_column(Text)
    max_score: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(20))
    tags_json: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(200))


def bank_exercise_dict(row):
    return {**{key:getattr(row,key) for key in ['id','prompt','reference','analysis','max_score','level','source']},
            'tags':json.loads(row.tags_json)}


def material_notes(row):
    return json.loads(row.notes_json) or rule_notes(row.title,row.genre,row.body)


def bank_material_dict(row, questions=()):
    notes = material_notes(row)
    return {**{key:getattr(row,key) for key in ['id','title','author','genre','source_type','body','content_hash','source_url','source_label','year','region','review']},
            'managed':row.managed,'tags':list(dict.fromkeys(json.loads(row.tags_json)+[t for n in notes for t in n.get('tags',[])])), 'notes':notes,
            'questions':[bank_exercise_dict(x) for x in questions]}


def assign_bank_material(row, record):
    for key in ['title','author','genre','source_type','body','content_hash','source_url','source_label','year','region','review','revision']:
        setattr(row,key,record[key])
    row.tags_json=json.dumps(record['tags'],ensure_ascii=False)
    row.notes_json=json.dumps(record['notes'],ensure_ascii=False)


def add_bank_exercise(db, material_id, item):
    db.add(BankExercise(id=item['id'],material_id=material_id,
        **{key:item[key] for key in ['prompt','reference','analysis','max_score','level','source']},
        tags_json=json.dumps(item['tags'],ensure_ascii=False)))


def seed_material_bank(db):
    existing={row.id:row for row in db.scalars(select(BankMaterial))}
    for record in bank.seed_records():
        row=existing.get(record['id'])
        if row and (not row.managed or row.revision==record['revision']): continue
        if not row:
            row=BankMaterial(id=record['id'],managed=True)
            db.add(row)
        assign_bank_material(row,record)
        db.flush()
        db.execute(delete(BankExercise).where(BankExercise.material_id==row.id))
        for question in record['questions']: add_bank_exercise(db,row.id,question)


def digest(password, salt=None):
    salt = salt or secrets.token_hex(16)
    value = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return f'{salt}:{value}'

def verify(password, stored):
    return hmac.compare_digest(digest(password, stored.split(':')[0]), stored)

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    with DB() as db:
        if not db.scalar(select(Admin)):
            password = os.getenv('ZHIYU_ADMIN_PASSWORD', '')
            if len(password) < 12:
                raise RuntimeError('首次启动需设置 ZHIYU_ADMIN_PASSWORD（至少12位）；不要使用服务器登录密码。')
            db.add(Admin(username=os.getenv('ZHIYU_ADMIN_USER', 'teacher'), password_hash=digest(password)))
        seed_material_bank(db)
        db.commit()
    yield

app = FastAPI(title='知语教学 API', lifespan=lifespan, docs_url=None, redoc_url=None)

@app.middleware('http')
async def security(request: Request, call_next):
    # Cookie authentication requires same-origin browser writes; student bearer links are also same-origin.
    if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
        if request.headers.get('sec-fetch-site') == 'cross-site':
            return Response(status_code=403)
        origin = request.headers.get('origin')
        expected = os.getenv('PUBLIC_ORIGIN', str(request.base_url).rstrip('/'))
        if origin and origin.rstrip('/') != expected.rstrip('/'):
            return Response(status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response

def db_session():
    with DB() as db:
        yield db

def teacher(request: Request, db: Session = Depends(db_session)):
    raw = request.cookies.get('zhiyu_session', '')
    row = db.get(LoginSession, hashlib.sha256(raw.encode()).hexdigest())
    if not row or row.expires < time.time():
        raise HTTPException(401, '请先登录教师账号')

class InputModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

class LoginIn(InputModel):
    model_config = ConfigDict(str_strip_whitespace=False, extra="forbid")
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)

# Bounded per-process login throttle; nginx adds a shared limit in deployment.
attempts = {}
@app.post('/api/login')
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(db_session)):
    key = request.client.host if request.client else 'local'
    now = time.time()
    attempts[key] = [t for t in attempts.get(key, []) if now-t < 300]
    if len(attempts[key]) >= 10:
        raise HTTPException(429, '尝试过多，请五分钟后重试')
    attempts[key].append(now)
    admin = db.scalar(select(Admin).where(Admin.username == body.username))
    if not admin or not verify(body.password, admin.password_hash):
        raise HTTPException(401, '用户名或密码错误')
    attempts.pop(key, None)
    token = secrets.token_urlsafe(32)
    db.execute(delete(LoginSession).where(LoginSession.expires < int(now)))
    db.add(LoginSession(token=hashlib.sha256(token.encode()).hexdigest(), expires=int(now)+43200))
    db.commit()
    response.set_cookie('zhiyu_session', token, httponly=True, secure=SECURE, samesite='strict', max_age=43200)
    return {'ok': True}

@app.post('/api/logout', dependencies=[Depends(teacher)])
def logout(request: Request, response: Response, db: Session = Depends(db_session)):
    raw = request.cookies.get('zhiyu_session', '')
    db.execute(delete(LoginSession).where(LoginSession.token == hashlib.sha256(raw.encode()).hexdigest()))
    db.commit()
    response.delete_cookie('zhiyu_session')
    return {'ok': True}

def rowdict(row, keys):
    return {key: getattr(row, key) for key in keys.split()}

def require(db, model, id):
    row = db.get(model, id)
    if not row:
        raise HTTPException(404, '记录不存在')
    return row

@app.get('/api/workspace', dependencies=[Depends(teacher)])
def workspace(db: Session = Depends(db_session)):
    return {
        'articles': [rowdict(x, 'id title genre content') for x in db.scalars(select(Article).order_by(Article.id.desc()))],
        'points': [rowdict(x, 'id article_id name description') for x in db.scalars(select(Point))],
        'questions': [rowdict(x, 'id point_id level material prompt reference rubric max_score') for x in db.scalars(select(Question))],
        'assignments': [rowdict(x, 'id token question_id student created parent_id') for x in db.scalars(select(Assignment).order_by(Assignment.id.desc()))],
        'submissions': [rowdict(x, 'id assignment_id answer submitted score feedback issue reviewed') for x in db.scalars(select(Submission))]
    }

class ArticleIn(InputModel):
    title: str = Field(min_length=1, max_length=200)
    genre: str = Field(pattern='^(阅读|诗歌|文言文)$')
    content: str = Field(min_length=1, max_length=100000)

@app.post('/api/articles', dependencies=[Depends(teacher)])
def add_article(body: ArticleIn, db: Session = Depends(db_session)):
    row = Article(**body.model_dump()); db.add(row); db.commit()
    return {'id': row.id}

class PointIn(InputModel):
    article_id: int
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=5000)

@app.post('/api/points', dependencies=[Depends(teacher)])
def add_point(body: PointIn, db: Session = Depends(db_session)):
    require(db, Article, body.article_id)
    row = Point(**body.model_dump()); db.add(row); db.commit()
    return {'id': row.id}

def knowledge_groups(db):
    """A live index of confirmed/saved Point records; no speculative catalog tags."""
    counts = dict(db.execute(select(Question.point_id,func.count()).group_by(Question.point_id)).all())
    grouped = {}
    for point, article in db.execute(select(Point,Article).join(Article,Point.article_id==Article.id).order_by(Point.id)):
        normalized = ' '.join(unicodedata.normalize('NFKC',point.name).casefold().split())
        key = hashlib.sha256(normalized.encode()).hexdigest()
        group = grouped.setdefault(key,dict(id=key,name=point.name,names=[],articles={},point_count=0,question_count=0))
        if point.name not in group['names']: group['names'].append(point.name)
        item = group['articles'].setdefault(article.id,dict(id=article.id,title=article.title,genre=article.genre,points=[],question_count=0))
        count = counts.get(point.id,0)
        item['points'].append(dict(id=point.id,name=point.name,description=point.description,question_count=count))
        item['question_count'] += count
        group['point_count'] += 1
        group['question_count'] += count
    return grouped


def knowledge_summary(group):
    return {**{k:group[k] for k in ['id','name','names','point_count','question_count']},
            'article_count':len(group['articles']),
            'articles':[{k:a[k] for k in ['id','title','genre']} for a in group['articles'].values()]}


@app.get('/api/knowledge-library',dependencies=[Depends(teacher)])
def knowledge_library(q:str='',genre:str='',offset:int=0,limit:int=20,db:Session=Depends(db_session)):
    if len(q)>200 or offset<0 or not 1<=limit<=50: raise HTTPException(422,'搜索或分页参数无效')
    if genre and genre not in {'诗歌','文言文','阅读'}: raise HTTPException(422,'未知文体')
    groups = list(knowledge_groups(db).values())
    keyword = unicodedata.normalize('NFKC',q).casefold().strip()
    selected = [g for g in groups if (not genre or any(a['genre']==genre for a in g['articles'].values())) and
                (not keyword or keyword in unicodedata.normalize('NFKC',' '.join(g['names'])+' '+
                    ' '.join(a['title']+' '+' '.join(p['description'] for p in a['points']) for a in g['articles'].values())).casefold())]
    selected.sort(key=lambda g:(-len(g['articles']),g['name'],g['id']))
    return {'items':[knowledge_summary(g) for g in selected[offset:offset+limit]],'total':len(selected),
            'offset':offset,'limit':limit,'stats':{'knowledge_points':len(groups),
            'confirmed_records':sum(g['point_count'] for g in groups),
            'articles':len({a for g in groups for a in g['articles']})}}


@app.get('/api/knowledge-library/{key}',dependencies=[Depends(teacher)])
def knowledge_detail(key:str,db:Session=Depends(db_session)):
    group = knowledge_groups(db).get(key)
    if not group: raise HTTPException(404,'知识点不存在或已更名，请刷新知识点库')
    return {**knowledge_summary(group),'articles':list(group['articles'].values()),
            'notice':'这里仅索引已保存的知识点与教学文章。同名归组不等于已审定语义相同；每篇原文依据与训练目标分别保留。'}


@app.get('/api/catalog', dependencies=[Depends(teacher)])
def article_catalog(db:Session=Depends(db_session)):
    return {'items': catalog.listing(), 'ai_configured': analysis.configured(),
            'bank_materials':db.scalar(select(func.count()).select_from(BankMaterial)),
            'resources': catalog.RESOURCES,
            'editions': [{**edition, 'books': sorted({b for x in catalog.CATALOG for placement in x['textbook_editions'] if placement['id']==edition['id'] for b in placement['books']}),
                          'count': sum(any(p['id']==edition['id'] for p in x['textbook_editions']) for x in catalog.CATALOG)}
                         for edition in catalog.EDITION_OPTIONS],
            'books': sorted({b for x in catalog.CATALOG for b in x['books']}),
            'readable': sum(x['available'] for x in catalog.CATALOG),
            'analyzable': sum(x['has_analysis'] for x in catalog.CATALOG),
            'guided_directories': sum(x['has_guide'] and not x['available'] for x in catalog.CATALOG),
            'directory_sources': DIRECTORY_SOURCES,
            'scope': '统编五册课文、诵读与整本书阅读参考目录，含跨印次差异篇目；另列2020课标72篇推荐参考。尚未覆盖所有教材版本，推荐不等于当前高考范围。'}

@app.post('/api/catalog/{entry_id}/open', dependencies=[Depends(teacher)])
def open_catalog(entry_id: str, db: Session = Depends(db_session)):
    entry = catalog.get_entry(entry_id)
    if not entry:
        raise HTTPException(404, '文章库中未找到该篇目')
    if not entry['available']:
        raise HTTPException(409, '此篇尚未内置可用原文，可先查看原创导读与官方阅读入口；导读不能代替原文进行引文分析')
    article = db.scalar(select(Article).where(Article.title == entry['title'], Article.content == entry['content'], Article.genre == entry['genre']))
    if not article:
        article = Article(title=entry['title'], content=entry['content'], genre=entry['genre'])
        db.add(article)
        db.commit()
    return {'id': article.id, 'has_analysis': entry['has_analysis']}

def all_bank_records(db):
    questions={}
    for question in db.scalars(select(BankExercise)):
        questions.setdefault(question.material_id,[]).append(question)
    return [bank_material_dict(row,questions.get(row.id,())) for row in db.scalars(select(BankMaterial))]


def bank_summary(record):
    summary={key:record[key] for key in ['id','title','author','genre','source_type','source_url','source_label','year','region','review','tags']}
    summary.update(preview=record['body'][:180],question_count=len(record['questions']),
                   levels=sorted({q['level'] for q in record['questions']}),has_notes=bool(record['notes']))
    for key in ['match_tags','match_reason','match_basis','match_evidence','match_explanation']:
        if key in record: summary[key]=record[key]
    return summary


def filter_bank_records(records,q='',genre='',source_type='',tag='',year='',has_questions=False):
    if source_type and source_type not in bank.SOURCE_TYPES: raise HTTPException(422,'未知来源分类')
    if tag and tag not in bank.TAG_LABELS: raise HTTPException(422,'未知知识点标签')
    if len(q)>200: raise HTTPException(422,'搜索词最多200字')
    return [r for r in records if (not q or q.lower() in (r['title']+' '+r['author']+' '+r['body']+' '+r['region']).lower())
            and (not genre or r['genre']==genre) and (not source_type or r['source_type']==source_type)
            and (not tag or tag in r['tags']) and (not year or r['year']==year)
            and (not has_questions or r['questions'])]


@app.get('/api/bank',dependencies=[Depends(teacher)])
def material_bank(q:str='',genre:str='',source_type:str='',tag:str='',year:str='',has_questions:bool=False,
                  offset:int=0,limit:int=20,db:Session=Depends(db_session)):
    if not 0<=offset or not 1<=limit<=50: raise HTTPException(422,'分页参数无效')
    records=all_bank_records(db)
    filtered=filter_bank_records(records,q,genre,source_type,tag,year,has_questions)
    filtered.sort(key=lambda r:(r['source_type'],r['title'],r['id']))
    return {'items':[bank_summary(r) for r in filtered[offset:offset+limit]],'total':len(filtered),
            'offset':offset,'limit':limit,'stats':{'materials':len(records),'questions':sum(len(r['questions']) for r in records),
            'analyzed':sum(bool(r['notes']) for r in records),
            'rule_analyzed':sum(bool(r['notes']) and all(n.get('origin')=='rule' for n in r['notes']) for r in records),
            'tagged':sum(bool(r['tags']) for r in records),'sources':{key:sum(r['source_type']==key for r in records) for key in bank.SOURCE_TYPES}},
            'tags':[{'id':key,'name':value} for key,value in bank.TAG_LABELS.items()],
            'source_types':bank.SOURCE_TYPES,'years':sorted({r['year'] for r in records if r['year']},reverse=True)}


@app.get('/api/bank/materials/{id}',dependencies=[Depends(teacher)])
def bank_detail(id:str,db:Session=Depends(db_session)):
    row=require(db,BankMaterial,id)
    return bank_material_dict(row,list(db.scalars(select(BankExercise).where(BankExercise.material_id==id))))


@app.post('/api/bank/materials/{id}/open',dependencies=[Depends(teacher)])
def open_bank_material(id:str,db:Session=Depends(db_session)):
    row=require(db,BankMaterial,id)
    article=db.scalar(select(Article).where(Article.title==row.title,Article.genre==row.genre,Article.content==row.body))
    if not article:
        article=Article(title=row.title,genre=row.genre,content=row.body)
        db.add(article);db.commit()
    return {'id':article.id,'has_analysis':bool(material_notes(row))}


@app.get('/api/points/{id}/related-materials',dependencies=[Depends(teacher)])
def related_materials(id:int,q:str='',genre:str='',source_type:str='',tag:str='',year:str='',has_questions:bool=False,
                      offset:int=0,limit:int=12,db:Session=Depends(db_session)):
    if offset<0 or not 1<=limit<=50: raise HTTPException(422,'分页参数无效')
    point=require(db,Point,id);article=require(db,Article,point.article_id)
    records=filter_bank_records(all_bank_records(db),q,genre,source_type,tag,year,has_questions)
    query_tags,ranked=bank.recommend(records,point.name,point.description,article.content,article.title,article.genre,tag)
    return {'point':{'id':point.id,'name':point.name,'article':article.title},'query_tags':query_tags,
            'items':[bank_summary(r) for r in ranked[offset:offset+limit]],'total':len(ranked),
            'offset':offset,'limit':limit,'notice':'按统一知识点标签关联，已排除当前作品并按正文去重；不是AI相似度评分，候选材料须教师核对。'}


@app.get('/api/articles/{id}/related-materials',dependencies=[Depends(teacher)])
def article_related(id:int,limit:int=3,db:Session=Depends(db_session)):
    if not 1<=limit<=5: raise HTTPException(422,'每个知识点最多预览5篇')
    article=require(db,Article,id)
    records=all_bank_records(db)
    result=[]
    for point in db.scalars(select(Point).where(Point.article_id==id)):
        tags,ranked=bank.recommend(records,point.name,point.description,article.content,article.title,article.genre)
        result.append({'point_id':point.id,'name':point.name,'tags':tags,'total':len(ranked),
                       'items':[bank_summary(r) for r in ranked[:limit]]})
    return {'items':result}

class BankImportQuestion(InputModel):
    prompt:str=Field(min_length=1,max_length=10000)
    reference:str=Field(default='',max_length=10000)
    analysis:str=Field(default='',max_length=10000)
    max_score:int=Field(default=10,ge=1,le=100)
    level:str=Field(default='未分层',pattern='^(未分层|基础|巩固|拓展)$')

class BankImportMaterial(InputModel):
    title:str=Field(min_length=1,max_length=200)
    author:str=Field(default='',max_length=100)
    genre:str=Field(pattern='^(阅读|诗歌|文言文)$')
    source_type:str=Field(pattern='^(textbook|gaokao|mock|public|bank)$')
    source_label:str=Field(min_length=1,max_length=500)
    source_url:HttpUrl|None=None
    year:str=Field(default='',max_length=20)
    region:str=Field(default='',max_length=100)
    body:str=Field(min_length=1,max_length=15000)
    tags:list[str]=Field(default_factory=list,max_length=18)
    questions:list[BankImportQuestion]=Field(default_factory=list,max_length=20)

class BankImportIn(InputModel):
    materials:list[BankImportMaterial]=Field(min_length=1,max_length=100)

BANK_IMPORT_LOCK=threading.Lock()

@app.post('/api/bank/import',dependencies=[Depends(teacher)])
def import_bank(body:BankImportIn,db:Session=Depends(db_session)):
    if len(body.model_dump_json().encode())>800000: raise HTTPException(413,'单次导入最多800KB，请分批导入')
    if any(tag not in bank.TAG_LABELS for m in body.materials for tag in m.tags):
        raise HTTPException(422,'包含未知标签，请使用题库页列出的标签ID')
    created=questions_added=0
    with BANK_IMPORT_LOCK:
        for item in body.materials:
            source_url=str(item.source_url) if item.source_url else ''
            fingerprint=bank.body_hash(item.body)
            row=db.scalar(select(BankMaterial).where(BankMaterial.content_hash==fingerprint,
                BankMaterial.source_type==item.source_type,BankMaterial.source_url==source_url,
                BankMaterial.year==item.year,BankMaterial.region==item.region,BankMaterial.managed==False))
            if not row:
                record=bank.material_record('import:'+secrets.token_hex(16),item.title,item.author,item.genre,item.source_type,
                    item.body,source_url,item.source_label,[],[],year=item.year,region=item.region,tags=list(dict.fromkeys(item.tags)),
                    review='教师导入，来源及考试分类未外部核验')
                row=BankMaterial(id=record['id'],managed=False)
                assign_bank_material(row,record);db.add(row);db.flush();created+=1
            else:
                row.tags_json=json.dumps(list(dict.fromkeys(json.loads(row.tags_json)+item.tags)),ensure_ascii=False)
            for q in item.questions:
                key=hashlib.sha256(json.dumps([q.prompt,q.reference],ensure_ascii=False).encode()).hexdigest()[:24]
                id=row.id+':'+key
                if db.get(BankExercise,id): continue
                add_bank_exercise(db,row.id,{'id':id,**q.model_dump(),'tags':item.tags,'source':'教师导入，未外部核验'})
                db.flush();questions_added+=1
        db.commit()
    return {'created':created,'merged':len(body.materials)-created,'questions_added':questions_added}

class AnalyzeIn(InputModel):
    mode: str = Field(default='auto', pattern='^(auto|ai)$')

@app.post('/api/articles/{id}/analyze', dependencies=[Depends(teacher)])
def analyze_article(id: int, body: AnalyzeIn, db: Session = Depends(db_session)):
    article = require(db, Article, id)
    try:
        matched = db.scalar(select(BankMaterial).where(BankMaterial.body == article.content))
        if body.mode != 'ai' and matched and not catalog.match_entry(article.content,article.genre):
            notes=material_notes(matched)
            if not notes:
                raise ValueError('该文集篇目暂无教研解析；可作为关联阅读材料，或配置AI后分析。')
            points=[analysis.AnalysisPoint(name=n['name'],evidence=n['evidence'],learning_goal=n.get('learning_goal','能结合原文分析“'+n['name']+'”。'),
                explanation=n['explanation'][:600] or '据来源解析标签，需教师复核。',foundation=n.get('foundation','解释引句中与知识点相关的词句'),
                consolidation=n.get('consolidation','结合原题写出依据与分析'),extension=n.get('extension','比较其他篇目中的相同知识点')).model_dump() for n in notes[:12]]
            source = RULE_SOURCE if all(n.get('origin')=='rule' for n in notes) else AUTHORED_SOURCE if all(n.get('origin')=='authored' for n in notes) else '公开题目解析提取（非AI）'
            result={'source':source,'points':points,'notice':'规则辅助仅辨认可见语言线索，不是逐篇审校结论；其余解析也须教师核对，确认后保存。'}
        else:
            result = analysis.analyze(article, body.mode)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    except RuntimeError as exc:
        raise HTTPException(502, str(exc)) from None
    return {**result, 'article_digest': analysis.fingerprint(article)}

class ConfirmAnalysisIn(InputModel):
    article_digest: str = Field(pattern='^[0-9a-f]{64}$')
    source: str = Field(pattern='^(内置教研解析（非AI）|公开题目解析提取（非AI）|内置研读解析（规则辅助）|内置篇目解析（待审校）|AI辅助解析)$')
    points: list[analysis.AnalysisPoint] = Field(min_length=1, max_length=12)

ANALYSIS_CONFIRM_LOCK = threading.Lock()

@app.post('/api/articles/{id}/confirm-analysis', dependencies=[Depends(teacher)])
def confirm_analysis(id: int, body: ConfirmAnalysisIn, db: Session = Depends(db_session)):
    with ANALYSIS_CONFIRM_LOCK:
        article = require(db, Article, id)
        if analysis.fingerprint(article) != body.article_digest:
            raise HTTPException(409, '文章已修改，请重新分析后保存')
        if any(p.evidence not in article.content for p in body.points):
            raise HTTPException(422, '有引文不在当前原文中，请核对依据')
        names = set(db.scalars(select(Point.name).where(Point.article_id == id)))
        created = 0
        for point in body.points:
            if point.name in names:
                continue
            db.add(Point(article_id=id, name=point.name, description=analysis.description(point, body.source)))
            names.add(point.name)
            created += 1
        db.commit()
        return {'created': created, 'skipped': len(body.points)-created}

class QuestionIn(InputModel):
    point_id: int
    level: str = Field(pattern='^(基础|巩固|拓展)$')
    material: str = Field(min_length=1, max_length=50000)
    prompt: str = Field(min_length=1, max_length=10000)
    reference: str = Field(min_length=1, max_length=10000)
    rubric: str = Field(min_length=1, max_length=10000)
    max_score: int = Field(default=10, ge=1, le=100)

@app.post('/api/questions', dependencies=[Depends(teacher)])
def add_question(body: QuestionIn, db: Session = Depends(db_session)):
    require(db, Point, body.point_id)
    row = Question(**body.model_dump()); db.add(row); db.commit()
    return {'id': row.id}

@app.put('/api/articles/{id}', dependencies=[Depends(teacher)])
def edit_article(id: int, body: ArticleIn, db: Session = Depends(db_session)):
    row = require(db, Article, id)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return {'ok': True}

@app.put('/api/points/{id}', dependencies=[Depends(teacher)])
def edit_point(id: int, body: PointIn, db: Session = Depends(db_session)):
    row = require(db, Point, id)
    if row.article_id != body.article_id:
        raise HTTPException(422, '不能变更知识点所属文章')
    row.name, row.description = body.name, body.description
    db.commit()
    return {'ok': True}

@app.put('/api/questions/{id}', dependencies=[Depends(teacher)])
def edit_question(id: int, body: QuestionIn, db: Session = Depends(db_session)):
    row = require(db, Question, id)
    if db.scalar(select(Assignment).where(Assignment.question_id == id)):
        raise HTTPException(409, '题目已分发，不能修改；请新建题目，保留原作答依据')
    require(db, Point, body.point_id)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    db.commit()
    return {'ok': True}

@app.get('/api/points/{id}/practice-candidates', dependencies=[Depends(teacher)])
def practice_candidates(id: int, db: Session = Depends(db_session)):
    point=require(db,Point,id)
    article=require(db,Article,point.article_id)
    query_tags,ranked=bank.recommend(all_bank_records(db),point.name,point.description,article.content,article.title,article.genre)
    items=[]
    for record in ranked:
        for question in record['questions']:
            if not set(question['tags']).intersection(query_tags): continue
            original=record['source_type']=='gaokao'
            items.append({'id':question['id'],'title':record['title'],'level':'巩固' if question['level']=='未分层' else question['level'],
                'material':record['body'],'prompt':question['prompt'],'reference':question['reference'],
                'rubric':question['analysis'],'max_score':question['max_score'],'matched_point':point.name,
                'source':('GAOKAO-Bench公开整理；原题未分层，暂选巩固为系统建议，需教师调整' if original else
                          '应用自编练习草稿，非高考真题' if record['managed'] else record['source_label'])})
            if len(items)>=36: break
        if len(items)>=36: break
    return {'items':items,'notice':'已从独立题库自动匹配其他作品及配套题，排除当前文章。原题未分层时暂选巩固；请核对具体小题考点、答案与分值。'}

class AssignmentIn(InputModel):
    question_id: int
    student: str = Field(min_length=1, max_length=100)
    parent_id: int | None = None

@app.post('/api/assignments', dependencies=[Depends(teacher)])
def add_assignment(body: AssignmentIn, db: Session = Depends(db_session)):
    question = require(db, Question, body.question_id)
    if body.parent_id is not None:
        parent = require(db, Assignment, body.parent_id)
        previous = require(db, Question, parent.question_id)
        submission = db.scalar(select(Submission).where(Submission.assignment_id == parent.id))
        if parent.student != body.student or previous.point_id != question.point_id or not submission or not submission.reviewed:
            raise HTTPException(422, '巩固任务须关联同一学生、同一知识点且已复核的作答')
    row = Assignment(**body.model_dump(), token=secrets.token_urlsafe(32), created=int(time.time()))
    db.add(row); db.commit()
    return rowdict(row, 'id token')

class ReviewIn(InputModel):
    score: int = Field(ge=0, le=100)
    feedback: str = Field(min_length=1, max_length=10000)
    issue: str = Field(min_length=1, max_length=300)

@app.put('/api/submissions/{id}/review', dependencies=[Depends(teacher)])
def review(id: int, body: ReviewIn, db: Session = Depends(db_session)):
    row = require(db, Submission, id)
    assignment = require(db, Assignment, row.assignment_id)
    question = require(db, Question, assignment.question_id)
    if body.score > question.max_score:
        raise HTTPException(422, '得分不能超过本题满分')
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    row.reviewed = True
    db.commit()
    return {'ok': True}

def by_token(db, token):
    row = db.scalar(select(Assignment).where(Assignment.token == token))
    if not row:
        raise HTTPException(404, '任务链接无效')
    return row

@app.get('/api/tasks/{token}')
def task(token: str, db: Session = Depends(db_session)):
    assignment = by_token(db, token)
    question = require(db, Question, assignment.question_id)
    point = require(db, Point, question.point_id)
    submission = db.scalar(select(Submission).where(Submission.assignment_id == assignment.id))
    result = {'student': assignment.student, 'point': point.name, 'question': rowdict(question, 'level material prompt max_score'), 'submission': None, 'followups': []}
    if submission:
        result['submission'] = rowdict(submission, 'answer reviewed score feedback issue')
        if submission.reviewed:
            result['question']['reference'] = question.reference
            result['question']['rubric'] = question.rubric
            result['followups'] = [rowdict(x, 'token') for x in db.scalars(select(Assignment).where(Assignment.parent_id == assignment.id))]
    return result

class AnswerIn(InputModel):
    answer: str = Field(min_length=1, max_length=20000)

@app.post('/api/tasks/{token}/submit')
def submit(token: str, body: AnswerIn, db: Session = Depends(db_session)):
    assignment = by_token(db, token)
    if not body.answer.strip():
        raise HTTPException(422, '答案不能为空')
    if db.scalar(select(Submission).where(Submission.assignment_id == assignment.id)):
        raise HTTPException(409, '已提交，请等待教师复核')
    db.add(Submission(assignment_id=assignment.id, answer=body.answer, submitted=int(time.time())))
    try:
        db.commit()
    except Exception as exc:
        from sqlalchemy.exc import IntegrityError
        db.rollback()
        if isinstance(exc, IntegrityError):
            raise HTTPException(409, '已提交，请勿重复提交') from exc
        raise
    return {'ok': True}

@app.get('/api/health')
def health(db: Session = Depends(db_session)):
    db.execute(select(1))
    return {'status': 'ok'}

@app.get('/')
def home():
    return FileResponse(ROOT / 'index.html')

@app.get('/app.js')
def javascript():
    return FileResponse(ROOT / 'app.js', media_type='application/javascript')
