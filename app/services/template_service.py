# app/services/template_service.py
# テンプレートを管理するサービスクラス
from app.domain.models.template_model import TemplateModel
from app.repositories.template_repository import TemplateRepository

class TemplateService:
    def __init__(self, template_repository: TemplateRepository):
        self.template_repository = template_repository

    def get_template(self, template_id: str) -> TemplateModel:
        return self.template_repository.find_by_id(template_id)

    def get_all_templates(self) -> list[TemplateModel]:
        return self.template_repository.find_all()