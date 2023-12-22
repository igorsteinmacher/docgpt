from pathlib import Path

import pypandoc
from dependency_injector.wiring import Provide, inject
from langchain.globals import set_debug, set_verbose
from langchain.vectorstores import VectorStore

from src.app.discord import BOT
from src.core import containers
from src.domain.content import Content
from src.domain.port.assistent import AssistentPort
from src.domain.port.content import ContentPort


@inject
def run_terminal(
    chat: AssistentPort = Provide[containers.Settings.assistant.chat],
):
    while True:
        question = input("-> **Q**: ")
        if question.lower() in ["q", "quit", "exit"]:
            break

        answer = chat.prompt(question, session_id="cli")
        print(f"**-> Q: {question}\n")
        print(f"**AI**: {answer}\n")


@inject
def run_discord(
    *,
    token: str = Provide[containers.Settings.app.discord_token],
):
    BOT.run(token)


@inject
def add_documents(
    documents: list[Content],
    *,
    storage: VectorStore = Provide[containers.Settings.storage.vector_storage],
) -> None:
    fails_count = 0

    for doc in documents:
        try:
            storage.add_documents([doc])
        except (Exception,) as e:
            fails_count += 1
            print(f"Fail to add document: {e}")

    if fails_count:
        print(f"{fails_count} documents failed to add")


@inject
def fetch_documents(
    code: ContentPort = Provide[containers.Settings.content.git_code],
    wiki: ContentPort = Provide[containers.Settings.content.git_wiki],
    assets_path: Path = Provide[containers.Settings.core.assets_path],
):
    project = "pdf.js"

    code_url = f"ssh://git@github.com/mozilla/{project}.git"
    code_path = assets_path.joinpath(project)

    wiki_url = f"ssh://git@github.com/mozilla/{project}.wiki.git"
    wiki_path = assets_path.joinpath(project + ".wiki")

    if code_path.exists():
        code_docs = code.get_by_path(project, code_path, branch="master")
    else:
        code_docs = code.get_by_url(project, code_url, branch="master")

    if wiki_path.exists():
        wiki_docs = wiki.get_by_path(project, wiki_path)
    else:
        wiki_docs = wiki.get_by_url(project, wiki_url)

    add_documents(wiki_docs)  # type: ignore
    add_documents(code_docs)  # type: ignore


if __name__ == "__main__":
    pypandoc.ensure_pandoc_installed()

    application = containers.Settings()
    application.config.from_yaml("config.yml")
    application.core.init_resources()
    application.wire(modules=[__name__, "src.app.discord"])
    set_debug(True)
    set_verbose(True)

    # fetch_documents()
    # run_terminal()
    run_discord()
