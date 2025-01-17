from enum import Enum


class ExtractorType(str, Enum):
    SITEMAP = "sitemap"
    GITHUB_ISSUES = "github_issues"
    GITHUB_README = "github_readme"
