import base64
from typing import AsyncGenerator

from src.sources.common.exceptions import DocumentExtractorException
from src.sources.common.github_client import GitHubClient
from src.sources.common.schemas import MarkdownPage


class GitHubReadmeFetcher:
    def __init__(
        self,
        *,
        github_client: GitHubClient,
    ):
        self.client = github_client

    async def fetch_readmes(
        self,
        repo_owner: str,
        repo_name: str,
        include_root: bool = True,
        sub_dirs: list[str] | None = None,
        ref: str | None = None,
    ) -> AsyncGenerator[MarkdownPage, None]:
        base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/readme"

        dirs: list[str] = []

        if include_root:
            dirs.append("")

        if sub_dirs:
            dirs.extend(sub_dirs)

        if not dirs:
            raise DocumentExtractorException(
                "No directories specified to fetch READMEs"
            )

        for dir in dirs:
            url = base_url + (f"/{dir}" if dir else "")
            params: dict[str, str] = {}
            if ref:
                params["ref"] = ref

            data, _ = await self.client.request("GET", url, params=params)
            if not data:
                raise DocumentExtractorException(
                    f"Failed to fetch README content at {url}"
                )

            content_b64 = data["content"]
            encoding = data["encoding"]

            if encoding == "base64":
                try:
                    decoded_bytes = base64.b64decode(content_b64)
                    decoded_str = decoded_bytes.decode("utf-8", errors="replace")
                except Exception as e:
                    raise DocumentExtractorException(
                        f"Failed to decode README content at {url}: {e}"
                    )
            else:
                raise DocumentExtractorException(
                    f"Unexpected encoding '{encoding}' for README content at {url}"
                )

            page = MarkdownPage(
                title=data["path"],
                url=data["html_url"],
                content=decoded_str,
            )

            yield page
