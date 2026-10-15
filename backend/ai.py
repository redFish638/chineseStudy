"""AI 集成边界，尚未配置服务商，不发送教学或学生数据到外部。"""
from typing import Protocol
from pydantic import BaseModel, Field


class SuggestedPoint(BaseModel):
    name: str
    learning_goal: str
    evidence: str


class SuggestedExercise(BaseModel):
    level: str = Field(pattern='^(基础|巩固|拓展)$')
    material: str
    material_source: str
    prompt: str
    reference: str
    rubric: str


class SuggestedDiagnosis(BaseModel):
    issue: str
    evidence_in_answer: str
    feedback: str
    recommended_level: str = Field(pattern='^(基础|巩固|拓展)$')


class TeachingAI(Protocol):
    """未来服务商适配器需返回结构化建议，由教师确认后通过现有 API 入库。"""
    async def split_article(self, genre: str, article: str) -> list[SuggestedPoint]: ...
    async def create_exercises(self, article: str, point: SuggestedPoint) -> list[SuggestedExercise]: ...
    async def diagnose(self, exercise: SuggestedExercise, answer: str) -> SuggestedDiagnosis: ...
