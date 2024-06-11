from sqlalchemy import Column, Integer, String, Text, Enum

from database import BaseModel


class OpenaiCallLog(BaseModel):
    __tablename__ = 'openai_call_log'

    user_id = Column(Integer, nullable=False, server_default='0')
    input_str = Column(Text, nullable=False, default="", server_default="")
    output_str = Column(Text, nullable=False, default="", server_default="")
    revised_prompt = Column(Text, nullable=False, default="", server_default="")  # 文转图后，openai返回的提示词
    input_tokens = Column(Integer, nullable=False, server_default="0")
    prompt_tokens = Column(Integer, nullable=False, server_default="0")
    output_tokens = Column(Integer, nullable=False, server_default="0")
    completion_tokens = Column(Integer, nullable=False, server_default="0")
    total_tokens = Column(Integer, nullable=False, server_default="0")
    model_type = Column(String(100), nullable=False, server_default="")
