---
name: document-analysis
description: Analyze and summarize documents with key insights extraction. Use when processing PDFs, DOCX, or other document formats for structured data extraction.
allowed-tools:
- Read
- Glob
- Grep
compatibility: Requires pypdf>=4.0.0, python-docx>=1.0.0. No network access needed.
metadata:
  version: 1.0.0
  category: research
  author: Emergence AI
  dependencies:
  - pypdf>=4.0.0
  - python-docx>=1.0.0
  sandbox_config:
    network: none
    filesystem: readonly
---
# Document Analysis Skill

Extract key insights, summaries, and structured data from various document formats.

## Capabilities

- **Document Parsing**: Extract text from PDF, DOCX, TXT
- **Summarization**: Generate concise summaries
- **Key Point Extraction**: Identify main arguments and findings
- **Table Extraction**: Extract structured data from tables
- **Citation Analysis**: Identify and parse references

## Usage Examples

- "Summarize this research paper"
- "Extract key findings from this report"
- "Analyze the structure of this document"
- "List all citations in this paper"

## Guidelines

1. Preserve document structure in analysis
2. Highlight quantitative findings
3. Note any limitations or caveats mentioned
4. Extract actionable insights

## Output Format

```markdown
# Document Analysis: [Title]

## Summary
[Executive summary - 2-3 paragraphs]

## Key Findings
1. [Finding 1]
2. [Finding 2]

## Detailed Sections
[Section-by-section breakdown]

## Data Tables
[Extracted tables if present]

## References
[List of citations]
```
