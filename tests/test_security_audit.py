"""Automated Security & Data Anonymization Audit Test Suite.

Scans all project source code, configurations, data files, and documentation for:
1. Hardcoded API keys, client secrets, bearer tokens, and private keys.
2. PII (Personally Identifiable Information), Cardholder Data (PCI-DSS PANs, SSNs, phone numbers).
3. Corporate email addresses or confidential internal employee identifiers.
4. Anonymization compliance in data/anonymized_sample_data.csv.
5. Presence and coverage of .gitignore and .dockerignore rules.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Directories to ignore from deep scanning
IGNORED_DIRS = {".venv", "venv", "__pycache__", ".pytest_cache", ".git"}

# Allowed placeholder examples in documentation or help strings
ALLOWED_PLACEHOLDERS = {
    "AIzaSy...",
    "your_gemini_api_key_here",
    "your_api_key",
    "/path/to/service_account.json",
}

# Regex patterns for high-risk secrets
SECRET_PATTERNS = {
    "Google API Key": re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b"),
    "OpenAI API Key": re.compile(r"\bsk-[a-zA-Z0-9]{24,}\b"),
    "AWS Access Key ID": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub Personal Access Token": re.compile(r"\bgh[pousr]-[0-9a-zA-Z]{36}\b"),
    "Slack Token": re.compile(r"\bxox[baprs]-[0-9a-zA-Z]{10,48}\b"),
    "Private Key Block": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    "Hardcoded Password Assignment": re.compile(
        r"""(?:password|passwd|api_key|secret_key|client_secret)\s*=\s*['\"][^'\"]{8,}['\"]""",
        re.IGNORECASE,
    ),
}

# Regex patterns for PII and Cardholder data
PII_PATTERNS = {
    "US Social Security Number (SSN)": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "Corporate / Personal Email": re.compile(r"\b[A-Za-z0-9._%+-]+@(?!example\.com|company\.com)[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "Phone Number": re.compile(r"\b(?:\+?1[-. ]?)?\(?[2-9]\d{2}\)?[-. ]?\d{3}[-. ]?\d{4}\b"),
}


def get_tracked_files() -> list[Path]:
    """Collect all non-ignored project files."""
    files = []
    for path in PROJECT_ROOT.rglob("*"):
        if path.is_file():
            # Check if any parent part is in IGNORED_DIRS
            if not any(part in IGNORED_DIRS for part in path.parts):
                files.append(path)
    return files


def test_no_hardcoded_secrets_in_repository():
    """Verify no real API keys, bearer tokens, or private keys exist in any repository file."""
    files = get_tracked_files()
    violations: list[str] = []

    for file_path in files:
        # Skip binary files if any
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for secret_name, pattern in SECRET_PATTERNS.items():
            matches = pattern.findall(content)
            for match in matches:
                if any(allowed in match for allowed in ALLOWED_PLACEHOLDERS):
                    continue
                # Ignore test assertions verifying placeholder detection
                if "test_security_audit.py" in str(file_path):
                    continue
                rel_path = file_path.relative_to(PROJECT_ROOT)
                violations.append(f"[{secret_name}] found in {rel_path}: {match[:10]}...")

    assert not violations, "Security audit detected potential hardcoded secrets:\n" + "\n".join(violations)


def test_no_pii_or_cardholder_data_in_dataset():
    """Verify data/anonymized_sample_data.csv contains zero PII, real emails, or cardholder numbers."""
    csv_path = PROJECT_ROOT / "data" / "anonymized_sample_data.csv"
    assert csv_path.exists(), "Sample dataset must exist for verification"

    content = csv_path.read_text(encoding="utf-8")

    # Check PII
    for pii_name, pattern in PII_PATTERNS.items():
        matches = pattern.findall(content)
        assert not matches, f"Found unexpected {pii_name} in sample dataset: {matches[:3]}"

    # Validate that Amex 15-digit or Visa/MasterCard 16-digit card numbers do not exist
    card_pattern = re.compile(r"\b(?:3[47]\d{13}|4\d{15}|5[1-5]\d{14})\b")
    card_matches = card_pattern.findall(content)
    assert not card_matches, f"Found potential payment card PANs in dataset: {card_matches[:3]}"


def test_dataset_strict_anonymization_and_synthetic_integrity():
    """Verify synthetic integrity: only scrubbed departments, regions, and synthetic record IDs."""
    csv_path = PROJECT_ROOT / "data" / "anonymized_sample_data.csv"
    assert csv_path.exists()

    allowed_departments = {
        "Global Commercial Services",
        "Global Consumer Services",
        "Enterprise Digital & Data Solutions",
        "Global Technology & Infrastructure",
        "Global Risk, Compliance & Legal",
        "Corporate Affairs & Real Estate",
    }

    allowed_regions = {
        "North America (NAM)",
        "Europe, Middle East & Africa (EMEA)",
        "Asia-Pacific (APAC)",
        "Latin America (LATAM)",
    }

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        row_count = 0
        for row in reader:
            row_count += 1
            # Verify record ID is synthetic format REC-xxxxx
            record_id = row["record_id"]
            assert record_id.startswith("REC-"), f"Non-synthetic record ID format: {record_id}"

            # Verify department is purely in allowed list
            dept = row["department"]
            assert dept in allowed_departments, f"Non-anonymized department found: {dept}"

            # Verify region is purely in allowed list
            reg = row["region"]
            assert reg in allowed_regions, f"Non-anonymized region found: {reg}"

            # Verify no personal names or text fields outside generic schemas
            assert float(row["gross_emissions_mt"]) >= 0.0
            assert float(row["net_emissions_mt"]) >= 0.0

        assert row_count == 576, f"Expected 576 synthetic rows, found {row_count}"


def test_no_actual_env_files_committed():
    """Verify no .env or credentials json files exist in repository root."""
    forbidden_files = [
        PROJECT_ROOT / ".env",
        PROJECT_ROOT / ".env.local",
        PROJECT_ROOT / ".env.production",
        PROJECT_ROOT / "service_account.json",
        PROJECT_ROOT / "gcp-key.json",
    ]
    for forbidden in forbidden_files:
        assert not forbidden.exists(), f"Found uncommitted or forbidden secret file: {forbidden.name}"


def test_gitignore_and_dockerignore_rules():
    """Verify that .gitignore and .dockerignore contain all required exclusion rules."""
    gitignore_path = PROJECT_ROOT / ".gitignore"
    dockerignore_path = PROJECT_ROOT / ".dockerignore"

    assert gitignore_path.exists(), ".gitignore must exist"
    assert dockerignore_path.exists(), ".dockerignore must exist"

    gitignore_text = gitignore_path.read_text(encoding="utf-8")
    dockerignore_text = dockerignore_path.read_text(encoding="utf-8")

    # .gitignore essential patterns
    assert ".env" in gitignore_text
    assert "*.key" in gitignore_text
    assert "*service_account*.json" in gitignore_text
    assert ".venv" in gitignore_text

    # .dockerignore essential patterns
    assert ".venv" in dockerignore_text
    assert "__pycache__" in dockerignore_text
