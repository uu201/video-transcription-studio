"""API 依赖对象。"""

from fastapi import Request

from app.config import Settings
from app.db.database import Database
from app.services.scanner import Scanner
from app.workers.worker import TaskWorker


def settings(request: Request) -> Settings:
    """读取应用配置。"""
    return request.app.state.settings


def database(request: Request) -> Database:
    """读取数据库实例。"""
    return request.app.state.database


def scanner(request: Request) -> Scanner:
    """读取扫描服务。"""
    return request.app.state.scanner


def worker(request: Request) -> TaskWorker:
    """读取任务 Worker。"""
    return request.app.state.worker
