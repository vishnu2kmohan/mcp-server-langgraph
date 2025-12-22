---
name: web-research
version: 1.0.0
description: Research topics using web search and summarization
category: research
author: Emergence AI
dependencies:
  - beautifulsoup4>=4.12.0
  - httpx>=0.25.0
  - readability-lxml>=0.8.0
sandbox_config:
  network: allowlist
  allowed_domains:
    - "*.google.com"
    - "*.wikipedia.org"
    - "*.arxiv.org"
    - "*.github.com"
    - "*.stackoverflow.com"
required_secrets: []
optional_secrets:
  - SERPAPI_KEY
  - GOOGLE_SEARCH_API_KEY
---

# Web Research Skill

A comprehensive web research skill for gathering information, synthesizing findings, and producing research summaries.

## Capabilities

- **Web Search**: Execute targeted web searches using search APIs
- **Page Extraction**: Extract main content from web pages
- **Source Synthesis**: Combine information from multiple sources
- **Citation Management**: Track and cite sources properly

## Usage Examples

- "Research recent advances in quantum computing"
- "Find the top 5 open-source LLM frameworks in 2025"
- "Summarize the key points from this article: [URL]"
- "Compare cloud providers for ML workloads"

## Guidelines

1. **Start Broad, Then Narrow**: Begin with general searches before diving into specifics
2. **Verify Sources**: Cross-reference information from multiple authoritative sources
3. **Cite Everything**: Always include source URLs in the output
4. **Respect Rate Limits**: Space out requests to avoid overwhelming sources
5. **Focus on Recency**: Prefer recent sources for technical topics

## Workflow

1. Parse the research query to identify key topics
2. Execute initial broad search
3. Analyze search results for relevance
4. Extract content from top results
5. Synthesize findings into coherent summary
6. Include citations and source links

## Output Format

Research results are structured as:

```markdown
# Research: [Topic]

## Summary
[Brief overview of findings]

## Key Findings
- Finding 1 (Source: [URL])
- Finding 2 (Source: [URL])

## Detailed Analysis
[In-depth exploration of each finding]

## Sources
1. [Source Title](URL) - Accessed [Date]
2. [Source Title](URL) - Accessed [Date]
```

## Limitations

- Respects robots.txt and terms of service
- Cannot access paywalled content
- Rate limited to prevent abuse
- Results may not include real-time data
