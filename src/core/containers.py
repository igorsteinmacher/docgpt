import logging.config

from dependency_injector import containers, providers
from dependency_injector.providers import Factory, Singleton
from langchain.chat_models import ChatOpenAI
from langchain.chat_models.base import BaseChatModel
from langchain.embeddings import OpenAIEmbeddings
from langchain.memory import ConversationBufferMemory, MongoDBChatMessageHistory
from langchain.memory.chat_memory import BaseChatMemory
from langchain.schema import BaseChatMessageHistory
from langchain.schema.embeddings import Embeddings
from langchain.text_splitter import TextSplitter
from langchain.vectorstores import PGVector, VectorStore

from src.adapters.assistent import ConversationalAssistentAdapter
from src.adapters.content import (
    GitCodeContentAdapter,
    LangSplitterByMetadata,
    PandocConverterAdapter,
    WebPageContentAdapter,
)
from src.domain.port.assistent import AssistentPort
from src.domain.port.content import ContentConverterPort, ContentPort


class Core(containers.DeclarativeContainer):
    config = providers.Configuration()

    logging = providers.Resource(
        logging.config.dictConfig,
        config=config.logging,
    )


class AI(containers.DeclarativeContainer):
    config = providers.Configuration()

    llm: Singleton[BaseChatModel] = Singleton(
        ChatOpenAI,
        model_name=config.openai.model_name,
        openai_api_key=config.openai.api_key,
        verbose=True,
    )

    embeddings: Singleton[Embeddings] = Singleton(
        OpenAIEmbeddings,
        openai_api_key=config.openai.api_key,
        openai_api_version=config.openai.api_version,
        openai_api_base=config.openai.api_base,
        disallowed_special=[],
        show_progress_bar=True,
    )


class StorageAdapters(containers.DeclarativeContainer):
    config = providers.Configuration()
    ai = providers.DependenciesContainer()

    vector_storage: Singleton[VectorStore] = Singleton(
        PGVector,
        connection_string=config.vector.url,
        embedding_function=ai.embeddings,
        pre_delete_collection=config.vector.pre_delete_collection,
    )

    memory_factory: providers.Factory[BaseChatMessageHistory] = providers.Factory(
        MongoDBChatMessageHistory,
        connection_string=config.memory.url,
    )


class ContentAdapters(containers.DeclarativeContainer):
    config = providers.Configuration()

    converter: Singleton[ContentConverterPort] = Singleton(PandocConverterAdapter)
    splitter_factory: Factory[LangSplitterByMetadata] = Factory(LangSplitterByMetadata)

    git_splitter: Singleton[TextSplitter] = Singleton(splitter_factory, "file_name")
    git: Singleton[ContentPort] = Singleton(
        GitCodeContentAdapter, splitter=git_splitter
    )
    web: Singleton[ContentPort] = Singleton(WebPageContentAdapter, converter)


class AssistantAdapters(containers.DeclarativeContainer):
    config = providers.Configuration()
    ai = providers.DependenciesContainer()
    storage = providers.DependenciesContainer()

    memory: providers.Factory[BaseChatMemory] = providers.Factory(
        ConversationBufferMemory,
        chat_memory=storage.memory_factory,
        memory_key="chat_history",
    )

    chat: Singleton[AssistentPort] = Singleton(
        ConversationalAssistentAdapter,
        llm=ai.llm,
        storage=storage.vector_storage,
        memory_factory=memory.provider,
        k=config.k,
        tokens_limit=config.tokens_limit.as_int(),
        score_threshold=config.score_threshold,
        distance_threshold=config.distance_threshold,
    )


class Apps(containers.DeclarativeContainer):
    config = providers.Configuration()
    assistent = providers.DependenciesContainer()

    discord_token = config.discord.token


class Settings(containers.DeclarativeContainer):
    config = providers.Configuration()

    core = providers.Container(Core, config=config.core)
    ai = providers.Container(AI, config=config.ai)
    storage = providers.Container(StorageAdapters, config=config.storage, ai=ai)
    content = providers.Container(ContentAdapters, config=config.content)
    assistant = providers.Container(
        AssistantAdapters,
        config=config.assistent,
        ai=ai,
        storage=storage,
    )
    app = providers.Container(Apps, config=config.app, assistent=assistant)
