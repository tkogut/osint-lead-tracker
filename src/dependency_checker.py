"""
dependency_checker.py — Uniwersalny skaner spójności i stanu zależności pakietów Python.
Sprawdza pakiety wymagane i opcjonalne, zwraca ustrukturyzowany raport oraz loguje ostrzeżenia.
"""

import importlib
import importlib.metadata
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger("dependency_checker")

# Pakiety wymagane dla prawidłowego działania systemu
REQUIRED_PACKAGES = [
    "fastapi",
    "uvicorn",
    "pydantic_settings",
    "apscheduler",
    "aiosqlite",
    "google.genai",
    "sqlalchemy",
    "curl_cffi",
    "trafilatura",
]

# Pakiety opcjonalne (skrappery rezerwowe / opcjonalne feature'y)
OPTIONAL_PACKAGES = [
    "bs4",
    "playwright",
]

# Mapowanie nazwy modułu na nazwę pakietu w PyPI (dla importlib.metadata)
DISTRIBUTION_NAMES = {
    "pydantic_settings": "pydantic-settings",
    "google.genai": "google-genai",
    "bs4": "beautifulsoup4",
    "curl_cffi": "curl-cffi",
}


def _get_module_version(mod_name: str, mod_obj: Any) -> str:
    """Pobiera wersję modułu z __version__ lub importlib.metadata."""
    if hasattr(mod_obj, "__version__") and mod_obj.__version__:
        return str(mod_obj.__version__)
    dist_name = DISTRIBUTION_NAMES.get(mod_name, mod_name)
    try:
        return importlib.metadata.version(dist_name)
    except Exception:
        return "unknown"


def audit_dependencies() -> Dict[str, Any]:
    """
    Wykonuje pełny audyt wymaganych i opcjonalnych zależności.
    Zwraca słownik z podsumowaniem statusu ("OK" | "WARNING" | "CRITICAL"),
    szczegółami modułów, listą polskich ostrzeżeń oraz znacznikiem czasu ISO UTC.
    """
    modules_info: List[Dict[str, Any]] = []
    warnings: List[str] = []
    overall_status = "OK"

    all_packages = [(pkg, True) for pkg in REQUIRED_PACKAGES] + [
        (pkg, False) for pkg in OPTIONAL_PACKAGES
    ]

    for pkg_name, required in all_packages:
        mod_data: Dict[str, Any] = {
            "name": pkg_name,
            "required": required,
            "installed": False,
            "version": None,
            "status": "OK",
            "error": None,
        }

        try:
            mod = importlib.import_module(pkg_name)
            version = _get_module_version(pkg_name, mod)
            mod_data["installed"] = True
            mod_data["version"] = version
            mod_data["status"] = "OK"
        except Exception as e:
            err_msg = str(e)
            mod_data["status"] = "CRITICAL" if required else "WARNING"
            mod_data["error"] = err_msg

            if required:
                overall_status = "CRITICAL"
                warn_str = f"WYMAGANY pakiet '{pkg_name}' nie mógł zostać załadowany: {err_msg}"
                warnings.append(warn_str)
                logger.error("SYSTEM DEPENDENCY ERROR: %s", warn_str)
            else:
                if overall_status != "CRITICAL":
                    overall_status = "WARNING"
                warn_str = (
                    f"OPCJONALNY pakiet '{pkg_name}' nie jest dostępny: {err_msg}"
                )
                warnings.append(warn_str)
                logger.warning("SYSTEM DEPENDENCY WARNING: %s", warn_str)

        modules_info.append(mod_data)

    report = {
        "status": overall_status,
        "modules": modules_info,
        "warnings": warnings,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return report


def log_dependency_banner(report: Dict[str, Any]) -> None:
    """Loguje czytelny banner informacyjny o stanie zależności przy starcie systemu."""
    status = report.get("status", "UNKNOWN")
    modules = report.get("modules", [])
    ok_count = sum(1 for m in modules if m.get("status") == "OK")
    total_count = len(modules)
    warnings = report.get("warnings", [])

    logger.info("================================================================================")
    logger.info(" SYSTEM DEPENDENCY INTEGRITY REPORT — Status: %s", status)
    logger.info(" Total Scanned: %d | OK: %d | Warnings/Errors: %d", total_count, ok_count, len(warnings))
    logger.info("================================================================================")

    if warnings:
        for warn in warnings:
            if "WYMAGANY" in warn:
                logger.error(" [!] %s", warn)
            else:
                logger.warning(" [!] %s", warn)
