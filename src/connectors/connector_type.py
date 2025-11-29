from enum import Enum


class ConnectorType(str, Enum):
    SITEMAP = "sitemap"
    GITHUB_ISSUES = "github_issues"
    GITHUB_README = "github_readme"
    GITHUB_PDF = "github_pdf"
    REST_API = "rest_api"
