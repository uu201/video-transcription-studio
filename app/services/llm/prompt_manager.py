"""Prompt 模板管理。"""


class PromptManager:
    """集中管理首版分析模板，后续可映射到 prompt_template 表。"""

    DEFAULTS = {
        "summary": "请用一句话总结以下视频文案：\n\n{text}",
        "outline": "请输出以下视频文案的结构大纲：\n\n{text}",
        "key_points": "请列出以下视频文案的核心观点：\n\n{text}",
        "golden_sentences": "请找出以下文案中最有传播力的句子：\n\n{text}",
    }

    def build(self, name: str, text: str) -> str:
        """按名称渲染模板。"""
        return self.DEFAULTS.get(name, self.DEFAULTS["summary"]).format(text=text)
