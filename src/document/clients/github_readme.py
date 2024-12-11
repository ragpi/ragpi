import base64
import logging
from typing import AsyncGenerator
from src.document.clients.github import GitHubClient
from src.document.exceptions import GitHubClientException
from src.document.schemas import MarkdownPage


class GitHubReadmeClient(GitHubClient):
    def __init__(self) -> None:
        super().__init__(concurrent_requests=1)

    async def fetch_readmes(
        self,
        repo_owner: str,
        repo_name: str,
        include_root: bool = True,
        sub_dirs: list[str] | None = None,
        ref: str | None = None,
    ) -> AsyncGenerator[MarkdownPage, None]:
        base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/readme"

        targets: list[str] = []

        if include_root:
            targets.append("")

        if sub_dirs:
            targets.extend(sub_dirs)

        if not targets:
            raise GitHubClientException("No targets to fetch READMEs")

        for dir in targets:
            url = base_url + (f"/{dir}" if dir else "")
            params = {}
            if ref:
                params["ref"] = ref

            data, _ = await self.request("GET", url, params=params)
            if not data:
                logging.error(f"No README found at {url}")
                continue

            content_b64 = data["content"]
            encoding = data["encoding"]

            if encoding == "base64":
                try:
                    decoded_bytes = base64.b64decode(content_b64)
                    decoded_str = decoded_bytes.decode("utf-8", errors="replace")
                except Exception as e:
                    raise GitHubClientException(
                        f"Failed to decode README content at {url}: {e}"
                    )
            else:
                raise GitHubClientException(
                    f"Unexpected encoding '{encoding}' for README content at {url}"
                )

            page = MarkdownPage(
                title=data["path"],
                url=data["html_url"],
                content=decoded_str,
            )

            yield page
