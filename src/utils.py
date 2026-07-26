import re
from typing import List

def match_polish_keywords(text: str, keywords: List[str]) -> bool:
    if not keywords:
        return True
    valid_keywords = [k.lower().strip() for k in keywords if k and isinstance(k, str) and k.strip()]
    if not valid_keywords:
        return True
    text_lower = text.lower()
    for kw_clean in valid_keywords:
        if kw_clean in text_lower:
            return True
    for kw_clean in valid_keywords:
        words = [w for w in re.findall(r'\b\w+\b', kw_clean) if len(w) > 3]
        if not words:
            continue
        stems = []
        for w in words:
            stem = w[:-1] if w[-1] in 'aeiouyęąó' else w
            if len(stem) > 3:
                if stem.endswith('ód'):
                    stem = stem[:-2] + 'od'
                elif stem[-1] in 't':
                    stem = stem[:-1]
            stems.append(stem)
        if not stems:
            continue
        found_all = True
        for stem in stems:
            if stem not in text_lower:
                found_all = False
                break
        if found_all:
            for match in re.finditer(re.escape(stems[0]), text_lower):
                start_pos = max(0, match.start() - 60)
                end_pos = min(len(text_lower), match.end() + 120)
                window = text_lower[start_pos:end_pos]
                if all(stem in window for stem in stems):
                    return True
    return False
