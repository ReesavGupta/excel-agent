# app/config.py
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    # File handling
    MAX_FILE_SIZE_MB: int = 100
    SUPPORTED_FORMATS: list | None = None
    CHUNK_SIZE: int = 1000
    
    # LLM Configuration
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    MODEL_NAME: str = "gpt-4"
    MAX_TOKENS: int = 2000
    TEMPERATURE: float = 0.1
    
    # Performance
    QUERY_TIMEOUT: int = 10
    MAX_CONCURRENT_USERS: int = 5
    
    def __post_init__(self):
        if self.SUPPORTED_FORMATS is None:
            self.SUPPORTED_FORMATS = ['.xlsx', '.xls']