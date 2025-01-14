from typing import AsyncGenerator
from src.common.schemas import Document
from src.sources.common.chunker import chunk_markdown_page
from src.sources.common.github_client import GitHubClient
from src.sources.github_readme.config import GithubReadmeConfig
from src.sources.github_readme.fetcher import GitHubReadmeFetcher


async def extract_documents_from_github_readme(
    *,
    source_config: GithubReadmeConfig,
    user_agent: str,
    github_api_version: str,
    github_token: str | None,
    document_uuid_namespace: str,
) -> AsyncGenerator[Document, None]:
    github_client = GitHubClient(
        concurrent_requests=1,
        user_agent=user_agent,
        github_api_version=github_api_version,
        github_token=github_token,
    )

    readme_fetcher = GitHubReadmeFetcher(github_client=github_client)

    async for page in readme_fetcher.fetch_readmes(
        repo_owner=source_config.repo_owner,
        repo_name=source_config.repo_name,
        include_root=source_config.include_root,
        sub_dirs=source_config.sub_dirs,
    ):
        chunks = chunk_markdown_page(
            page_data=page,
            chunk_size=source_config.chunk_size,
            chunk_overlap=source_config.chunk_overlap,
            uuid_namespace=document_uuid_namespace,
        )
        for chunk in chunks:
            yield chunk
