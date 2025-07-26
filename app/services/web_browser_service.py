# app/services/web_browser_service.py
# ウェブブラウザ操作を行うサービスクラス
from langchain_community.document_loaders import WebBaseLoader
from app.domain.models.web_browser_model import WebBrowserModel

class WebBrowserService:
    def __init__(self) -> None:
        pass

    def get_content_from_url(self, url: str) -> WebBrowserModel:
        loader = WebBaseLoader([url])
        docs = loader.load()
        content = "\n\n".join(doc.page_content for doc in docs)
        return WebBrowserModel(url=url, content=content)