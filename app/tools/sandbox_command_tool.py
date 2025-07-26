# /app/tools/sandbox_command_tool.py
# title: サンドボックスコマンド実行ツール
# role: AIがDockerサンドボックス環境内でコマンドを実行するためのツール。

from app.tools.base import Tool
from app.sandbox.sandbox_manager import SandboxManager
from app.constants import ToolNames

class SandboxCommandTool(Tool):
    """
    Dockerサンドボックス内でシェルコマンドを実行するためのツール。
    """
    def __init__(self, sandbox_manager: SandboxManager):
        self.name = ToolNames.SANDBOX_COMMAND
        self.description = (
            "隔離された安全なDockerサンドボックス環境で、ファイル操作、コード実行、パッケージインストールなどの"
            "シェルコマンドを実行します。AI自身の実験や検証、ファイルの永続化に使用できます。"
            "コマンドはLinuxシェルコマンドとして解釈されます。"
            "例: 'ls -l shared_dir/' or 'python shared_dir/my_script.py'"
        )
        self.sandbox_manager = sandbox_manager

    def use(self, query: str) -> str:
        """
        指定されたコマンドをサンドボックス内で実行し、結果を返す。
        :param query: 実行するシェルコマンド。
        """
        exit_code, result = self.sandbox_manager.execute_command(query)
        
        # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↓修正開始◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
        # 終了コードが0かどうかで成否を決めつけず、事実をそのまま報告する方式に変更。
        # これにより、pytestのような「テストの失敗」を「コマンドの失敗」と誤認しなくなる。
        return (
            f"コマンドの実行が完了しました。\n"
            f"終了コード: {exit_code}\n"
            f"出力:\n{result}"
        )
        # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↑修正終わり◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️