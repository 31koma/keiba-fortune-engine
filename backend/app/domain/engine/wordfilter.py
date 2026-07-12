"""禁止語フィルタ。語彙は正本(horse_expression_templates.language_policy.forbidden_expressions)。
鑑定文生成後に必ず通す。抵触時の挙動(reject/redact/regenerate)は設定。
regenerateはAI未接続のため現段階ではrejectと同じ扱い(明示エラー)。
"""
from app.core.errors import ForbiddenPhraseError
from app.knowledge.loader import KnowledgeStore


class ForbiddenFilter:
    def __init__(self, kb: KnowledgeStore, mode: str = "reject"):
        lp = kb.horse_templates["language_policy"]
        raw: list[str] = lp["forbidden_expressions"]["list"]
        # 「やる気がある/ない」「〜と感じている」等を検査可能な部分文字列に展開
        pats: set[str] = set()
        for item in raw:
            for piece in item.replace("〜", "").split("/"):
                piece = piece.strip()
                if piece:
                    pats.add(piece)
        self.patterns = sorted(pats)
        self.mode = mode
        self.disclaimer: str = lp["required_disclaimer_ja"]
        self.status = f"active({len(self.patterns)} patterns, mode={mode})"

    def find(self, text: str) -> list[str]:
        return [p for p in self.patterns if p in text]

    def apply(self, text: str) -> str:
        hits = self.find(text)
        if not hits:
            return text
        if self.mode == "redact":
            for h in hits:
                text = text.replace(h, "■" * len(h))
            return text
        # reject / regenerate(未接続) → 明示エラー
        raise ForbiddenPhraseError(hits)
