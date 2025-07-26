# /app/sandbox/sandbox_manager.py
# title: Dockerサンドボックスマネージャー
# role: AIのためのDockerサンドボックス環境のライフサイクル管理とコマンド実行を行う。自己修復機能と活動ログ記録機能を持つ。

import docker
from docker.models.containers import Container
from docker.errors import ImageNotFound, BuildError, APIError, DockerException
import os
from typing import Optional, Tuple
import logging
# ◾️◾️◾️◾️◾️◾️◾️◾️◾◾️◾️↓修正開始◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
import json
from datetime import datetime, timezone
# ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↑修正終わり◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️

logger = logging.getLogger(__name__)

class SandboxManager:
    """
    AIのためのDockerサンドボックス環境を管理するクラス。
    コンテナのライフサイクル（作成、実行、停止、削除）を管理し、
    安全なコード実行環境を提供します。
    問題が発生した際には、自己修復（再構築）機能を持ちます。
    """
    def __init__(self, image_name: str = "luca5-sandbox:latest", shared_dir_host_path: str = "sandbox/shared_dir") -> None:
        """
        :param image_name: サンドボックスとして使用するDockerイメージ名
        :param shared_dir_host_path: ホストOS上の共有ディレクトリのパス
        """
        try:
            self.client = docker.from_env()
        except DockerException:
            logger.error("Dockerデーモンに接続できません。Dockerがインストールされ、実行されていることを確認してください。")
            raise
        self.image_name = image_name
        self.container_name = image_name.replace(":", "-")
        self.container: Optional[Container] = None
        
        self.shared_dir_host_abs_path = os.path.abspath(shared_dir_host_path)
        self.shared_dir_container_path = "/app/shared_dir"
        
        # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↓修正開始◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
        # ログディレクトリとログファイルパスを設定
        self.log_dir_host_path = os.path.join(self.shared_dir_host_abs_path, "logs")
        self.log_file_host_path = os.path.join(self.log_dir_host_path, "sandbox_activity.log")

        # ホスト側の共有ディレクトリとログディレクトリが存在しない場合は作成
        if not os.path.exists(self.log_dir_host_path):
            os.makedirs(self.log_dir_host_path)
        # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↑修正終わり◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
        
        self._ensure_image_exists()

    # ... (変更なし) ...
    def _ensure_image_exists(self) -> None:
        """Dockerイメージが存在しない場合にビルドする"""
        try:
            self.client.images.get(self.image_name)
            logger.info(f"Dockerイメージ '{self.image_name}' は既に存在します。")
        except ImageNotFound:
            logger.warning(f"Dockerイメージ '{self.image_name}' が見つかりません。ビルドを開始します...")
            # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↓修正開始◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
            # イメージをビルドする前に、古いコンテナが残っていれば削除する
            self.stop_sandbox()
            self.build_image()
            # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↑修正終わり◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️

    def build_image(self, dockerfile_path: str = './sandbox') -> None:
        """指定されたDockerfileからサンドボックス用のDockerイメージをビルドします。"""
        logger.info(f"Building Docker image '{self.image_name}' from '{dockerfile_path}'...")
        try:
            self.client.images.build(path=dockerfile_path, tag=self.image_name, rm=True)
            logger.info("Image built successfully.")
        except BuildError as e:
            logger.error(f"Error building image: {e}")
            for line in e.build_log:
                if 'stream' in line:
                    logger.error(line['stream'].strip())
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during image build: {e}")
            raise

    # ... (rebuild_sandbox, start_sandboxは変更なし) ...
    def rebuild_sandbox(self) -> None:
        """
        サンドボックスを強制的に停止・削除し、新たに起動し直す（自己修復）。
        """
        logger.info(f"Rebuilding sandbox '{self.container_name}'...")
        self.stop_sandbox()
        self.start_sandbox()

    def start_sandbox(self) -> None:
        """サンドボックスコンテナを起動します。"""
        logger.info("Starting a new sandbox container...")
        try:
            self.container = self.client.containers.run(
                self.image_name,
                name=self.container_name,
                detach=True,
                tty=True,
                volumes={
                    self.shared_dir_host_abs_path: {
                        'bind': self.shared_dir_container_path,
                        'mode': 'rw'
                    }
                }
            )
            logger.info(f"Sandbox started with container ID: {self.container.id[:12]}")
            logger.info(f"Host directory '{self.shared_dir_host_abs_path}' is mounted to '{self.shared_dir_container_path}' in the container.")
        except APIError as e:
            logger.error(f"Error starting container: {e}")
            self.container = None
            raise

    def execute_command(self, command: str) -> Tuple[int, str]:
        """
        サンドボックス内でコマンドを実行します。
        問題（コンテナの停止、APIエラーなど）が検知された場合は、
        サンドボックスを自動的に再構築します。
        実行結果はログファイルに記録されます。
        """
        try:
            # コンテナの状態を確認し、必要であれば再構築または起動する
            try:
                self.container = self.client.containers.get(self.container_name)
                if self.container.status != 'running':
                    logger.warning(f"Container '{self.container_name}' found but not running (status: {self.container.status}). Rebuilding.")
                    self.rebuild_sandbox()
            except docker.errors.NotFound:
                logger.info(f"Container '{self.container_name}' not found. Starting a new one.")
                self.start_sandbox()

            if not self.container:
                 message = "Sandbox container could not be started even after attempting to start/rebuild."
                 self._log_activity(command, -1, message)
                 return -1, message

            logger.info(f"Executing command in sandbox: '{command}'")
            
            # シェルを介してコマンドを実行
            safe_command = command.replace('"', '\\"')
            exit_code, output = self.container.exec_run(f'sh -c "{safe_command}"')
            
            result = output.decode('utf-8').strip()
            
            # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↓修正開始◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
            self._log_activity(command, exit_code, result)
            # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↑修正終わり◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
            
            logger.info(f"Exit Code: {exit_code}")
            logger.info(f"Output:\n{result}")

            return exit_code, result

        except APIError as e:
            logger.error(f"An APIError occurred during command execution: {e}. The sandbox may be corrupted.")
            logger.info("Rebuilding the sandbox as a precaution...")
            error_message = (
                "サンドボックスでAPIエラーが発生したため、環境を再構築しました。"
                "コマンドの実行は失敗しました。以前のファイルや状態は失われています。"
                f"エラー詳細: {e}"
            )
            self._log_activity(command, -1, error_message, is_error=True)
            try:
                self.rebuild_sandbox()
            except Exception as rebuild_e:
                logger.error(f"Failed to rebuild sandbox after API error: {rebuild_e}")
                error_message += f"\nSandbox rebuild failed: {rebuild_e}"

            return -1, error_message

    def stop_sandbox(self) -> None:
        """
        サンドボックスコンテナを停止し、削除します。
        """
        logger.info(f"Attempting to stop and remove sandbox container '{self.container_name}'...")
        try:
            container_to_stop = self.client.containers.get(self.container_name)
            logger.info(f"Found container '{container_to_stop.name}'. Stopping and removing it.")
            container_to_stop.stop()
            container_to_stop.remove()
        except docker.errors.NotFound:
            logger.info(f"Container '{self.container_name}' not found. Nothing to stop.")
        except APIError as e:
            logger.error(f"Error stopping or removing container: {e}")
        finally:
            self.container = None

    # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↓修正開始◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
    def _log_activity(self, command: str, exit_code: int, output: str, is_error: bool = False) -> None:
        """
        サンドボックスの活動をログファイルに記録する。
        """
        log_entry = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "command": command,
            "exit_code": exit_code,
            "output": output,
            "type": "error" if is_error or exit_code != 0 else "command"
        }
        try:
            with open(self.log_file_host_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except IOError as e:
            logger.error(f"Failed to write to log file '{self.log_file_host_path}': {e}")
    # ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↑修正終わり◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️

    def __del__(self) -> None:
        """
        SandboxManagerオブジェクトが破棄されるときにコンテナを停止します。
        """
        self.stop_sandbox()