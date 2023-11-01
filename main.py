import pypandoc
from dependency_injector.wiring import Provide, inject
from langchain.text_splitter import Language
from langchain.vectorstores import PGVector
from pydantic import AnyUrl

from src.adapters.content.git import GitCodeContentAdapter
from src.adapters.content.web import WebPageContentAdapter
from src.app.discord import DiscordClient
from src.core import containers
from src.domain.port.assistent import AssistentPort


@inject
def run_terminal(
    chat: AssistentPort = Provide[containers.Settings.assistent.conversational],
):
    while True:
        question = input("-> **Q**: ")
        if question.lower() in ["q", "quit", "exit"]:
            break

        answer = chat.prompt(question)
        print(f"**-> Q: {question}\n")
        print(f"**AI**: {answer}\n")


@inject
def run_discord(
    discord: DiscordClient = Provide[containers.Settings.app.discord],
    token: str = Provide[containers.Settings.app.discord_token],
):
    discord.run(token)


@inject
def fetch_documents(
    git: GitCodeContentAdapter = Provide[containers.Settings.content.git],
    web: WebPageContentAdapter = Provide[containers.Settings.content.web],
    storage: PGVector = Provide[containers.Settings.storage.vector_storage],
):
    project = "jabref"
    documents = []

    git_content = git.get(
        project,
        AnyUrl("https://github.com/JabRef/jabref.git"),
        {Language.JAVA: [".java"]},
    )
    documents.extend(git_content)

    web_content = web.get(project, AnyUrl("https://devdocs.jabref.org/"), max_deep=2)
    documents.extend(web_content)

    storage.add_documents(documents)


if __name__ == "__main__":
    pypandoc.ensure_pandoc_installed()

    application = containers.Settings()
    application.config.from_yaml("config.yml")
    application.core.init_resources()
    application.wire(modules=[__name__])

    # fetch_documents()
    # run_terminal()
    run_discord()
