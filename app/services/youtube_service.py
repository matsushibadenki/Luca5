# app/services/youtube_service.py
# YouTubeの動画から文字起こしを取得するサービスクラス
from langchain_community.document_loaders import YoutubeLoader
from app.domain.models.youtube_model import YouTubeModel

class YoutubeService:
    """
    YouTubeの動画から文字起こしを取得するサービス
    """
    def get_transcript(self, url: str) -> YouTubeModel:
        """
        指定されたYouTubeのURLから文字起こしを取得します。

        Args:
            url: YouTube動画のURL

        Returns:
            文字起こしの内容を含むYouTubeModel
        """
        loader = YoutubeLoader.from_youtube_url(
            url,
            add_video_info=True,
            language=["en", "ja"],
            translation="ja",
        )
        docs = loader.load()
        # ドキュメントの内容を結合して返す
        content = "\n\n".join(doc.page_content for doc in docs)
        return YouTubeModel(url=url, transcript=content)