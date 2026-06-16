"""
Compliance Coverage Analysis

Computes which regulatory framework articles are referenced (directly or
implicitly) within the combined text output of a workflow run.

Design:
  - Pure function: no I/O, no LLM calls
  - Keyword matching against article.keywords tuples
  - Coverage ratio is per-framework to surface regulatory gaps
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .frameworks import ALL_ARTICLES, FrameworkArticle


@dataclass
class ArticleCoverage:
    code: str
    framework: str
    article: str
    title: str
    obligation_type: str
    esg_categories: tuple[str, ...]
    covered: bool


@dataclass
class FrameworkCoverage:
    framework: str
    total_articles: int
    covered_count: int
    coverage_ratio: float
    articles: list[ArticleCoverage] = field(default_factory=list)


@dataclass
class ComplianceCoverageReport:
    covered_article_codes: list[str]
    framework_coverage: list[FrameworkCoverage]
    overall_coverage_ratio: float
    mandatory_coverage_ratio: float


def compute_coverage(texts: list[str]) -> ComplianceCoverageReport:
    """
    Scan `texts` (agent step outputs) for keyword matches against the article
    catalog and return a ComplianceCoverageReport.

    `texts` is typically all non-empty step outputs from a WorkflowRun.
    """
    combined = "\n".join(t for t in texts if t).lower()

    covered_codes: set[str] = set()
    article_hits: dict[str, bool] = {}

    for article in ALL_ARTICLES:
        matched = any(kw.lower() in combined for kw in article.keywords)
        article_hits[article.code] = matched
        if matched:
            covered_codes.add(article.code)

    framework_reports: list[FrameworkCoverage] = []
    frameworks: dict[str, list[FrameworkArticle]] = {}
    for a in ALL_ARTICLES:
        frameworks.setdefault(a.framework, []).append(a)

    for fw_name, articles in frameworks.items():
        fw_articles = [
            ArticleCoverage(
                code=a.code,
                framework=a.framework,
                article=a.article,
                title=a.title,
                obligation_type=a.obligation_type,
                esg_categories=a.esg_categories,
                covered=article_hits[a.code],
            )
            for a in articles
        ]
        covered = sum(1 for ac in fw_articles if ac.covered)
        total = len(fw_articles)
        framework_reports.append(
            FrameworkCoverage(
                framework=fw_name,
                total_articles=total,
                covered_count=covered,
                coverage_ratio=covered / total if total else 0.0,
                articles=fw_articles,
            )
        )

    total_all = len(ALL_ARTICLES)
    mandatory = [a for a in ALL_ARTICLES if a.obligation_type == "mandatory"]
    mandatory_covered = sum(1 for a in mandatory if article_hits[a.code])

    overall = len(covered_codes) / total_all if total_all else 0.0
    mandatory_ratio = mandatory_covered / len(mandatory) if mandatory else 0.0

    return ComplianceCoverageReport(
        covered_article_codes=sorted(covered_codes),
        framework_coverage=framework_reports,
        overall_coverage_ratio=overall,
        mandatory_coverage_ratio=mandatory_ratio,
    )
