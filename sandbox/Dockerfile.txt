# /sandbox/Dockerfile
# title: サンドボックス環境用Dockerfile
# role: AIがコマンドを実行するための隔離されたPython環境を定義する。

# ベースイメージとして軽量なPythonイメージを選択
FROM python:3.10-slim

# ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↓修正開始◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️
# 作業ディレクトリを設定
WORKDIR /app

# テストフレームワーク pytest をインストール
RUN pip install pytest
# ◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️↑修正終わり◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️◾️

# コンテナが起動し続けるように、無限ループを実行
# これにより、exec_runで都度コマンドを実行できる状態を維持します
CMD ["tail", "-f", "/dev/null"]