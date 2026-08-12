import pytest
from unittest.mock import patch
from src.agent.llm_factory import create_llm
from src.core.config import Settings

@patch("src.agent.llm_factory.ChatOpenAI")
def test_create_llm_openai_success(mock_openai):
    settings = Settings(llm_provider="openai", llm_model="gpt-4o-mini", openai_api_key="sk-test", google_api_key=None)
    
    llm = create_llm(settings)
    
    assert llm is not None
    mock_openai.assert_called_once_with(model="gpt-4o-mini", api_key="sk-test", temperature=0)

@patch("src.agent.llm_factory.ChatGoogleGenerativeAI")
def test_create_llm_gemini_success(mock_gemini):
    settings = Settings(llm_provider="gemini", llm_model="gemini-3.5-flash", google_api_key="AIza-test", openai_api_key=None)
    
    llm = create_llm(settings)
    
    assert llm is not None
    mock_gemini.assert_called_once_with(model="gemini-3.5-flash", google_api_key="AIza-test", temperature=0)

def test_create_llm_openai_missing_key():
    settings = Settings(llm_provider="openai", llm_model="gpt-4o-mini", openai_api_key=None, google_api_key=None)
    with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
        create_llm(settings)

def test_create_llm_gemini_missing_key():
    settings = Settings(llm_provider="gemini", llm_model="gemini-3.5-flash", openai_api_key=None, google_api_key=None)
    with pytest.raises(ValueError, match="GOOGLE_API_KEY is required"):
        create_llm(settings)

def test_create_llm_invalid_provider():
    settings = Settings(llm_provider="invalid_provider", llm_model="gpt-4o-mini", openai_api_key="sk-test", google_api_key="AIza-test")
    with pytest.raises(ValueError, match="Unsupported LLM provider: invalid_provider"):
        create_llm(settings)
