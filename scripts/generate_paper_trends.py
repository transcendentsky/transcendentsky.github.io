#!/usr/bin/env python3
"""Generate a daily paper trend report for the tech-news section.

The script intentionally uses only the Python standard library so it can run in
GitHub Actions without dependency installation. It fetches recent arXiv papers,
adds best-effort metadata from Semantic Scholar and GitHub repository search,
then writes a Jekyll post under _posts/.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

ARXIV_API = "https://export.arxiv.org/api/query"
SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper/arXiv:{}"
GITHUB_SEARCH_API = "https://api.github.com/search/repositories"
OPENALEX_API = "https://api.openalex.org/works"

ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"

QUERY_SPECS = [
    ("多模态 / Vision-Language", 'cat:cs.CV AND (abs:"multimodal" OR abs:"vision-language" OR abs:"vision language" OR abs:"VLM")'),
    ("大模型 / LLM", 'cat:cs.CL AND (abs:"large language model" OR abs:"LLM" OR abs:"foundation model")'),
    ("智能体 / Agent", '(cat:cs.AI OR cat:cs.CL) AND (abs:"agent" OR abs:"multi-agent" OR abs:"tool use" OR abs:"planning")'),
    ("机器人与具身智能", '(cat:cs.RO OR cat:cs.AI) AND (abs:"embodied" OR abs:"robot" OR abs:"world model")'),
    ("推理、训练与对齐", '(cat:cs.LG OR cat:cs.CL) AND (abs:"reasoning" OR abs:"alignment" OR abs:"reinforcement learning" OR abs:"preference")'),
]

INNOVATION_POSITIVE = {
    "first": 8,
    "novel": 6,
    "new paradigm": 9,
    "paradigm": 5,
    "foundation": 4,
    "agent": 4,
    "multi-agent": 6,
    "world model": 7,
    "benchmark": 5,
    "dataset": 5,
    "framework": 4,
    "system": 3,
    "open-source": 4,
    "open source": 4,
    "state-of-the-art": 3,
    "sota": 3,
    "scalable": 3,
    "generalist": 5,
    "multimodal": 4,
    "vision-language": 4,
    "tool use": 5,
    "planning": 4,
    "reasoning": 4,
    "long-context": 4,
    "long context": 4,
    "unified": 4,
    "architecture": 5,
    "pretraining": 3,
    "post-training": 3,
    "reinforcement learning": 4,
    "preference": 3,
}

INCREMENTAL_SIGNALS = {
    "improve": -2,
    "improves": -2,
    "efficient": -2,
    "efficiency": -2,
    "lightweight": -2,
    "fine-tuning": -2,
    "fine tuning": -2,
    "adapter": -2,
    "compression": -2,
    "survey": -8,
    "review": -8,
    "revisit": -4,
    "revisiting": -4,
    "empirical study": -4,
}

IMPORTANT_TERMS = [
    "multimodal",
    "vision-language",
    "large language model",
    "llm",
    "agent",
    "multi-agent",
    "tool use",
    "world model",
    "embodied",
    "robot",
    "reasoning",
    "alignment",
    "reinforcement learning",
    "preference",
    "foundation model",
]

URL_RE = re.compile(r"https?://[^\s)\]}>,]+")
GITHUB_RE = re.compile(r"https?://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", re.I)


@dataclass
class Paper:
    arxiv_id: str
    title: str
    summary: str
    authors: List[str]
    published: str
    updated: str
    categories: List[str]
    query_bucket: str
    abs_url: str
    pdf_url: str
    comment: str = ""
    affiliations: List[str] = field(default_factory=list)
    source_url: str = ""
    source_open: bool = False
    innovation_score: int = 0
    classification: str = ""
    reasons: List[str] = field(default_factory=list)


def request_text(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "paper-trends-bot/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def request_json(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> Optional[dict]:
    try:
        return json.loads(request_text(url, headers=headers, timeout=timeout))
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None


def normalize_arxiv_id(raw_id: str) -> str:
    value = raw_id.rstrip("/").split("/")[-1]
    return value.replace("v1", "").replace("v2", "").replace("v3", "").replace("v4", "").replace("v5", "")


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def fetch_arxiv(query: str, bucket: str, max_results: int) -> List[Paper]:
    params = {
        "search_query": query,
        "start": "0",
        "max_results": str(max_results),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"
    xml_text = request_text(url)
    root = ET.fromstring(xml_text)
    papers: List[Paper] = []
    for entry in root.findall(f"{ATOM_NS}entry"):
        raw_id = entry.findtext(f"{ATOM_NS}id", "")
        arxiv_id = normalize_arxiv_id(raw_id)
        title = clean_text(entry.findtext(f"{ATOM_NS}title", ""))
        summary = clean_text(entry.findtext(f"{ATOM_NS}summary", ""))
        published = entry.findtext(f"{ATOM_NS}published", "")[:10]
        updated = entry.findtext(f"{ATOM_NS}updated", "")[:10]
        authors = [clean_text(a.findtext(f"{ATOM_NS}name", "")) for a in entry.findall(f"{ATOM_NS}author")]
        categories = [c.attrib.get("term", "") for c in entry.findall(f"{ATOM_NS}category") if c.attrib.get("term")]
        comment = clean_text(entry.findtext(f"{ARXIV_NS}comment", ""))
        links = entry.findall(f"{ATOM_NS}link")
        abs_url = raw_id
        pdf_url = ""
        for link in links:
            if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                pdf_url = link.attrib.get("href", "")
        papers.append(
            Paper(
                arxiv_id=arxiv_id,
                title=title,
                summary=summary,
                authors=authors,
                published=published,
                updated=updated,
                categories=categories,
                query_bucket=bucket,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )
    return papers


def enrich_semantic_scholar(paper: Paper) -> None:
    fields = "title,authors,externalIds,url,abstract,openAccessPdf,publicationDate,year"
    url = SEMANTIC_SCHOLAR_API.format(urllib.parse.quote(paper.arxiv_id)) + "?" + urllib.parse.urlencode({"fields": fields})
    data = request_json(url, timeout=10)
    if not data:
        return
    affiliations = []
    for author in data.get("authors", []) or []:
        for aff in author.get("affiliations", []) or []:
            if aff and aff not in affiliations:
                affiliations.append(aff)
    paper.affiliations = affiliations[:6]
    if data.get("openAccessPdf", {}).get("url") and not paper.pdf_url:
        paper.pdf_url = data["openAccessPdf"]["url"]


def enrich_openalex(paper: Paper) -> None:
    if paper.affiliations:
        return
    params = {
        "search": paper.title,
        "per-page": "1",
        "select": "title,authorships",
    }
    data = request_json(OPENALEX_API + "?" + urllib.parse.urlencode(params), timeout=10)
    if not data or not data.get("results"):
        return
    result = data["results"][0]
    match_ratio = difflib.SequenceMatcher(None, paper.title.lower(), (result.get("title") or "").lower()).ratio()
    if match_ratio < 0.72:
        return
    institutions: List[str] = []
    for authorship in result.get("authorships", []) or []:
        for institution in authorship.get("institutions", []) or []:
            name = institution.get("display_name")
            if name and name not in institutions:
                institutions.append(name)
    paper.affiliations = institutions[:8]


def find_open_source_from_text(paper: Paper) -> Optional[str]:
    text = "\n".join([paper.title, paper.summary, paper.comment])
    match = GITHUB_RE.search(text)
    if match:
        return match.group(0).rstrip(".")
    urls = URL_RE.findall(text)
    for url in urls:
        if any(host in url.lower() for host in ["huggingface.co", "gitlab.com", "bitbucket.org"]):
            return url.rstrip(".")
    return None


def title_tokens(title: str) -> List[str]:
    stop = {"with", "from", "towards", "toward", "using", "large", "language", "model", "models", "benchmark", "benchmarking", "framework", "unified", "learning", "reasoning", "agent", "agents", "multimodal"}
    tokens = re.findall(r"[a-z0-9]{5,}", title.lower())
    return [t for t in tokens if t not in stop]


def looks_like_generic_paper_list(repo: dict) -> bool:
    full_name = (repo.get("full_name") or "").lower()
    description = (repo.get("description") or "").lower()
    generic = ["paper-daily", "daily-paper", "daily-papers", "dailyarxiv", "daily-arxiv", "awesome", "reading-list", "newsletter"]
    return any(term in full_name or term in description for term in generic)


def github_search_title(title: str, token: Optional[str]) -> Optional[str]:
    # GitHub search is noisy: many daily paper-list repos mention paper titles.
    # Accept a match only when the repository name itself resembles the paper title
    # and does not look like a generic paper aggregator.
    query = f'"{title}" in:readme,description'
    url = GITHUB_SEARCH_API + "?" + urllib.parse.urlencode({"q": query, "sort": "stars", "order": "desc", "per_page": "5"})
    headers = {"User-Agent": "paper-trends-bot/1.0", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = request_json(url, headers=headers, timeout=12)
    if not data or not data.get("items"):
        return None
    tokens = title_tokens(title)[:8]
    for item in data["items"]:
        if looks_like_generic_paper_list(item):
            continue
        repo_name = (item.get("name") or "").lower()
        full_name = (item.get("full_name") or "").lower()
        overlap = [token for token in tokens if token in repo_name or token in full_name]
        if overlap or item.get("stargazers_count", 0) >= 30:
            return item.get("html_url")
    return None


def score_paper(paper: Paper) -> None:
    text = f"{paper.title}\n{paper.summary}\n{paper.comment}".lower()
    score = 45
    reasons: List[str] = []

    for term in IMPORTANT_TERMS:
        if term in text:
            score += 2
    for term, weight in INNOVATION_POSITIVE.items():
        if term in text:
            score += weight
            if weight >= 5:
                reasons.append(term)
    for term, weight in INCREMENTAL_SIGNALS.items():
        if term in text:
            score += weight
            if weight <= -4:
                reasons.append(f"偏增量信号：{term}")

    if len(paper.categories) >= 3:
        score += 3
        reasons.append("跨多个 arXiv 方向")
    if paper.source_open:
        score += 4
        reasons.append("已发现开源实现")
    if len(paper.summary) > 1000:
        score += 2
    if "survey" in paper.title.lower() or "review" in paper.title.lower():
        score -= 12

    score = max(0, min(100, score))
    paper.innovation_score = score
    if score >= 75:
        paper.classification = "高创新"
    elif score >= 60:
        paper.classification = "中等创新"
    else:
        paper.classification = "偏增量"
    paper.reasons = reasons[:5] or ["按摘要关键词、跨领域程度和开源线索综合判断"]


def dedupe_papers(papers: Iterable[Paper]) -> List[Paper]:
    seen = set()
    result = []
    for paper in papers:
        key = paper.arxiv_id or paper.title.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(paper)
    return result


def md_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def short_authors(authors: Sequence[str], limit: int = 5) -> str:
    if not authors:
        return "未知"
    if len(authors) <= limit:
        return ", ".join(authors)
    return ", ".join(authors[:limit]) + f" 等 {len(authors)} 人"


def affiliation_text(paper: Paper) -> str:
    if paper.affiliations:
        return "; ".join(paper.affiliations[:4])
    return "未识别（arXiv 元数据通常不提供机构，需人工核验）"


def source_text(paper: Paper) -> str:
    if paper.source_open and paper.source_url:
        return f"是：{paper.source_url}"
    return "未发现明确开源地址"


def key_innovation_text(paper: Paper) -> str:
    text = f"{paper.title}. {paper.summary}"
    sentences = re.split(r"(?<=[.!?])\s+", text)
    priority_terms = [
        "introduce", "introduces", "propose", "proposes", "present", "presents",
        "benchmark", "dataset", "framework", "paradigm", "world model", "agent",
        "multi-agent", "tool", "reasoning", "multimodal", "vision-language", "unified",
    ]
    ranked: List[Tuple[int, str]] = []
    for sentence in sentences:
        s = clean_text(sentence)
        if len(s) < 40:
            continue
        lower = s.lower()
        score = sum(1 for term in priority_terms if term in lower)
        if score > 0:
            ranked.append((score, s))
    if ranked:
        ranked.sort(key=lambda item: item[0], reverse=True)
        chosen = ranked[0][1]
    else:
        chosen = paper.summary[:360]
    if len(chosen) > 360:
        chosen = chosen[:357].rstrip() + "..."
    return chosen


def render_report(papers: List[Paper], report_date: dt.date, lookback_days: int, max_results: int, top_k: int) -> str:
    top_k = max(5, min(10, top_k))
    ranked_papers = sorted(papers, key=lambda p: p.innovation_score, reverse=True)
    selected = ranked_papers[:top_k]

    title = f"每日论文趋势报告：多模态、智能体与大模型（{report_date.isoformat()}）"
    lines = [
        "---",
        f"title: {title}",
        "categories:",
        "  - technews",
        "tags:",
        "  - 科技日报",
        "  - 论文趋势",
        "  - 多模态",
        "  - 智能体",
        "  - 大模型",
        "  - AI",
        "---",
        "",
        f"# {title}",
        "",
        f"> 自动生成报告：采集 arXiv 最近 {lookback_days} 天内与多模态、智能体、大模型、具身智能、推理和对齐相关的论文，只筛选最值得优先精读的 Top {len(selected)}。机构和开源信息为最佳努力识别，重要论文建议人工复核。",
        "",
        "<!--more-->",
        "",
        "## 今日概览",
        "",
        f"- 采集论文数：{len(papers)} 篇。",
        f"- 最终精选：{len(selected)} 篇。",
        f"- 每个主题最多抓取：{max_results} 篇，按 arXiv submittedDate 排序。",
        "- 筛选标准：优先选择新任务/新范式/新系统架构/新基准数据集/智能体或多模态能力边界推进明显的论文。",
        "",
        "## 今日最值得关注的论文",
        "",
    ]

    if selected:
        lines.extend([
            "| 论文名 | 学校/公司 | 创新性打分 | 是否开源 | 关键创新或理念 |",
            "| --- | --- | ---: | --- | --- |",
        ])
        for paper in selected:
            lines.append(
                "| "
                + f"[{md_escape(paper.title)}]({paper.abs_url}) | {md_escape(affiliation_text(paper))} | {paper.innovation_score} | {md_escape(source_text(paper))} | {md_escape(key_innovation_text(paper))} |"
            )
    else:
        lines.append("今日未筛出足够值得优先精读的候选。")

    lines.extend([
        "",
        "## 精选简析",
        "",
    ])
    for index, paper in enumerate(selected, start=1):
        lines.extend([
            f"### {index}. {paper.title}",
            "",
            f"- 机构：{affiliation_text(paper)}",
            f"- 作者：{short_authors(paper.authors)}",
            f"- 创新性打分：{paper.innovation_score} / 100",
            f"- 是否开源：{source_text(paper)}",
            f"- 关键创新/理念：{key_innovation_text(paper)}",
            f"- 筛选依据：{'; '.join(paper.reasons)}",
            f"- 论文：[{paper.arxiv_id}]({paper.abs_url})",
            "",
        ])

    lines.extend([
        "## 方法说明",
        "",
        "本报告是每日论文筛选器，不是最终论文评审。脚本会综合标题、摘要、arXiv 分类、跨领域程度、是否出现 benchmark/dataset/framework/agent/world model 等信号，以及是否发现开源实现，给出 0-100 的创新性打分。",
        "",
        "只保留 Top 5-10 篇，避免把中等创新和偏增量论文加入正文。开源地址优先读取 arXiv 摘要和 comment 中的 GitHub/Hugging Face 链接；对高分论文再用 GitHub Search 做标题匹配，并过滤论文日报、awesome list 等聚合仓库。",
    ])
    return "\n".join(lines) + "\n"

def parse_date(value: str) -> Optional[dt.date]:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(value[:10])
    except ValueError:
        return None


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate daily paper trend report")
    parser.add_argument("--date", default=dt.date.today().isoformat(), help="Report date, YYYY-MM-DD")
    parser.add_argument("--lookback-days", type=int, default=7)
    parser.add_argument("--per-query", type=int, default=40)
    parser.add_argument("--max-total", type=int, default=160)
    parser.add_argument("--top-k", type=int, default=8, help="Number of best papers to include, clamped to 5-10")
    parser.add_argument("--output-dir", default="_posts")
    parser.add_argument("--github-search", action="store_true", help="Use GitHub repo search for high-score candidates")
    args = parser.parse_args(argv)

    report_date = dt.date.fromisoformat(args.date)
    cutoff = report_date - dt.timedelta(days=args.lookback_days)

    fetched: List[Paper] = []
    for bucket, query in QUERY_SPECS:
        try:
            fetched.extend(fetch_arxiv(query, bucket, args.per_query))
            time.sleep(3.1)  # arXiv asks clients not to hammer the API.
        except Exception as exc:  # keep the daily job alive if one query fails
            print(f"warning: arXiv query failed for {bucket}: {exc}", file=sys.stderr)

    papers = []
    for paper in dedupe_papers(fetched):
        published = parse_date(paper.published) or parse_date(paper.updated)
        if published and published < cutoff:
            continue
        papers.append(paper)
    papers = papers[: args.max_total]

    for i, paper in enumerate(papers):
        if i < 80:
            enrich_semantic_scholar(paper)
            if not paper.affiliations:
                enrich_openalex(paper)
            time.sleep(0.25)
        source_url = find_open_source_from_text(paper)
        if source_url:
            paper.source_url = source_url
            paper.source_open = True
        score_paper(paper)

    if args.github_search:
        token = os.environ.get("GITHUB_TOKEN")
        candidates = sorted([p for p in papers if p.innovation_score >= 72 and not p.source_open], key=lambda p: p.innovation_score, reverse=True)[:20]
        for paper in candidates:
            repo = github_search_title(paper.title, token)
            if repo:
                paper.source_url = repo
                paper.source_open = True
                score_paper(paper)
            time.sleep(2)

    os.makedirs(args.output_dir, exist_ok=True)
    slug = "paper-trends-multimodal-agent-llm"
    out_path = os.path.join(args.output_dir, f"{report_date.isoformat()}-{slug}.md")
    content = render_report(papers, report_date, args.lookback_days, args.per_query, args.top_k)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
