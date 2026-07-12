"""AI文章補助の連携口(将来用)。実接続はまだ行わない。

役割の限定(本体プロンプト準拠):
- AIは占術計算の主体にしない(計算は知識ベース+決定的プログラム)
- 用途は自然な文章化・比較説明・追加質問への回答に限定
- AI出力も必ず禁止語フィルタを通すこと(呼び出し側の責務)
"""


class AITextAssist:
    def __init__(self, enabled: bool = False):
        self.enabled = enabled

    def polish(self, text: str, context: dict | None = None) -> str:
        """鑑定文の自然化。無効時は原文をそのまま返す(決定的動作)。"""
        if not self.enabled:
            return text
        raise NotImplementedError("AI APIへの実接続は現段階では行わない")
