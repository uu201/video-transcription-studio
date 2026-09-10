"""核心服务的轻量单元测试。"""

from pathlib import Path

from app.services.text_processor import TextProcessor
from app.domain.schemas import ASRResult


def test_text_processor_keeps_content_and_normalizes_whitespace():
    """清洗文本不应丢失正文内容。"""
    result = ASRResult(language="zh", text="  你好！！！\n\n\n世界  ", segments=[], raw_result=[])
    assert TextProcessor().process(result) == "你好！\n\n世界"


def test_settings_and_templates_are_present():
    """发布目录必须包含默认配置和首页模板。"""
    root = Path(__file__).resolve().parents[1]
    assert (root / "config" / "app.yaml").is_file()
    assert (root / "app" / "templates" / "dashboard.html").is_file()
