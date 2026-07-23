# PLAN-029: Logintrade Footer Boilerplate Cleaning in DOMSanitizer

**Status:** IN_PROGRESS  
**Date:** 2026-07-23  

---

## 🎯 Goal
Automatically strip Logintrade system footer boilerplate (e.g. `Enquiry is out of date.`, `Time to make an offer is up...`) in `DOMSanitizer.clean` so that systemic platform notice footers never cause false negative LLM rejections during live production scans.

---

## 🏗️ Implementation Details
- Update `DOMSanitizer.clean` in `src/scrapers/base.py`:
  - Add regex stripping for Logintrade system footer boilerplate phrases:
    - `Enquiry is out of date.`
    - `Time to make an offer is up...`
    - `The Purchasing Platform Terms of Use are available...`
    - `Registering in our company suppliers base...`

---

## 🛠️ Roles
- **Coordinator**: Plan creation, handshake validation, smart commit (auto bump to v1.7.7).
- **Builder (Subagent)**: Implement `DOMSanitizer` boilerplate filter, verify syntax, and generate builder handshake.
