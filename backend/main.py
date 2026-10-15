"""知语教学工作流。默认本地 SQLite，DATABASE_URL 支持 PostgreSQL/MySQL。"""
import hashlib
import hmac
import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, create_engine, delete, select
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
