from langchain_core.language_models import BaseChatModel

from src.core.config import Settings
from src.core.logging import get_logger

logger = get_logger(__name__)


def create_groq_llm(settings: Settings) -> BaseChatModel:
    """Create a Groq chat model using the configured Groq model identifier."""
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is required when using the Groq provider")

    from langchain_groq import ChatGroq

    logger.info("llm_factory.creating_groq_model", model=settings.llm_model)

    return ChatGroq(
        model=settings.llm_model,
        api_key=settings.groq_api_key,
        temperature=0,
        timeout=settings.llm_timeout_seconds,
        max_retries=0,
    )


def create_llm(settings: Settings) -> BaseChatModel:
    """Create a LangChain ChatModel based on provider settings."""
    provider = settings.llm_provider.strip().casefold()

    if provider == "gemini":
        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required when using the Gemini provider")

        from langchain_google_genai import ChatGoogleGenerativeAI

        logger.info("llm_factory.creating_gemini_model", model=settings.llm_model)

        return ChatGoogleGenerativeAI(
            model=settings.llm_model,
            google_api_key=settings.google_api_key,
            temperature=0,
            request_timeout=settings.llm_timeout_seconds,
            retries=0,
        )

    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when using the OpenAI provider")

        from langchain_openai import ChatOpenAI

        logger.info("llm_factory.creating_openai_model", model=settings.llm_model)

        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            temperature=0,
            timeout=settings.llm_timeout_seconds,
            max_retries=0,
        )

    if provider == "groq":
        return create_groq_llm(settings)

    raise ValueError(f"Unsupported LLM provider: {provider}")
