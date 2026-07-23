# PLAN-038: Fix Automatyka Scraper Advertiser Extraction Fallback

**Status:** IN_PROGRESS  
**Date:** 2026-07-23  

---

## 🎯 Goal
Fix the fallback behavior in `extract_advertiser_info` in `AutomatykaScraper`. When the dedicated "Dane ogłaszającego" or "Dane kontaktowe" block is missing from the HTML (e.g. on guest pages or category/sample aggregation pages), the parser must immediately return an empty string rather than falling back to the entire HTML, which matches layout attributes/CSS tags and generates garbage output.

---

## 🏗️ Implementation Details

### 1. Fix Scraper HTML Parser (`src/scrapers/automatyka.py`)
- Locate function `extract_advertiser_info(html_content: str) -> str`.
- Modify the fallback logic:
  ```python
  if not block_match:
      return ""
  search_scope = block_match.group(1)
  ```
- This prevents regexes from matching inputs, labels, and class attributes of the "new inquiry" templates in the global HTML.

---

## 🛠️ Roles
- **Coordinator**: Create plan, validate handshakes, execute commit.
- **Builder (Subagent)**: Modify `extract_advertiser_info` in `automatyka.py`, check syntax, and generate builder handshake.
- **Auditor (Subagent)**: Audit changes, verify extraction output on sample HTML, and generate auditor handshake.
