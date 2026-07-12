"""共通例外。不足知識は補完せず明示的に失敗させる。"""


class KnowledgeValidationError(Exception):
    """正本との不一致(サイズ/SHA-256/構文/キー/参照)。"""


class KnowledgeGapError(Exception):
    """正本に定義が無い(勝手に補完してはならない)。正本側への追加提案対象。"""


class ForbiddenPhraseError(Exception):
    """生成文が禁止語フィルタに抵触。"""

    def __init__(self, hits: list[str]):
        self.hits = hits
        super().__init__(f"forbidden phrases detected: {hits}")


class DegradedStateError(Exception):
    """知識ベースがdegraded状態のため鑑定機能を提供できない。"""
