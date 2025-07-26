# /app/tools/sandbox_log_viewer_tool.py
# title: サンドボックスログ閲覧ツール
# role: AIがサンドボックスの活動ログを確認するためのツール。

import os
import json
from typing import List, Dict, Any
from app.tools.base import Tool
from app.constants import ToolNames
import logging

logger = logging.getLogger(__name__)

class SandboxLogViewerTool(Tool):
    """
    サンドボックスの活動ログを読み取り、表示するためのツール。
    """
    def __init__(self, shared_dir_host_path: str):
        self.name = ToolNames.SANDBOX_LOG_VIEWER
        self.description = (
            "サンドボックス内で過去に実行されたコマンドの履歴、出力、結果を時系列で確認します。"
            "テストの実行結果の確認や、エラーのデバッグに役立ちます。"
            "引数として表示したいログの最大件数を指定できます（例: '10'）。"
        )
        # ログファイルのフルパスを、渡された共有ディレクトリのパスから構築する
        self.log_file_path = os.path.join(
            os.path.abspath(shared_dir_host_path), 
            "logs", 
            "sandbox_activity.log"
        )

    def use(self, query: str) -> str:
        """
        ログファイルから指定された件数の最新ログを読み込んで返す。
        :param query: 読み込むログの最大件数（数値の文字列）。デフォルトは10件。
        """
        # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↓修正開始◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
        # [DEBUG] 探しているログファイルの絶対パスをログに出力
        logger.info(f"[DEBUG] SandboxLogViewerTool is looking for log file at: {self.log_file_path}")
        # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↑修正終わり◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
        try:
            max_lines = int(query) if query.isdigit() else 10
        except ValueError:
            max_lines = 10

        if not os.path.exists(self.log_file_path):
            return "ログファイルが見つかりません。まだコマンドは実行されていないようです。"

        try:
            with open(self.log_file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # 最新のログから指定された件数を取得
            recent_logs = lines[-max_lines:]
            
            if not recent_logs:
                return "ログはまだ記録されていません。"

            # 読みやすい形式に整形
            formatted_logs = []
            for line in recent_logs:
                try:
                    log_data = json.loads(line)
                    timestamp = log_data.get("timestamp_utc", "N/A")
                    command = log_data.get("command", "N/A")
                    exit_code = log_data.get("exit_code", "N/A")
                    output = log_data.get("output", "").strip()
                    
                    # 出力が長い場合は省略
                    if len(output) > 200:
                        output = output[:200] + "... (省略)"

                    formatted_logs.append(
                        f"--- LOG: {timestamp} ---\n"
                        f"COMMAND: {command}\n"
                        f"EXIT_CODE: {exit_code}\n"
                        f"OUTPUT:\n{output}\n"
                    )
                except json.JSONDecodeError:
                    formatted_logs.append(f"--- INVALID LOG ENTRY ---\n{line}\n")
            
            return "\n".join(formatted_logs)

        except Exception as e:
            return f"ログの読み込み中にエラーが発生しました: {e}"