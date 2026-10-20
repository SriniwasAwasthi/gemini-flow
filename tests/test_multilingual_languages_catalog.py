"""
Automated Test Suite for Multilingual Languages Catalog & Intelligence:
- Validates 210+ comprehensive world languages across 7 geographical regions.
- Tests fuzzy search, alias resolution, and typographical tolerance.
- Verifies target prompt formatting for English Only, Single/Multi Language, and Universal modes.
- Validates zero-romanization and script enforcement directives.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from app.languages import (
    LANGUAGES_DB,
    REGIONS,
    REGION_ALL,
    REGION_INDIAN,
    REGION_EUROPEAN,
    REGION_ASIAN,
    REGION_MIDDLE_EAST,
    REGION_AFRICAN,
    REGION_AMERICAS,
    search_languages,
    fuzzy_search_languages,
    get_all_languages,
    get_language_by_name,
    get_language_by_code,
    format_language_prompt_instruction
)


def test_catalog_integrity():
    print("--- 1. Testing Catalog Integrity ---")
    assert len(LANGUAGES_DB) >= 210, f"Expected 210+ languages, found {len(LANGUAGES_DB)}"
    print(f"[PASS] Total languages cataloged: {len(LANGUAGES_DB)}")

    # Check required fields and unique codes
    codes = set()
    for lang in LANGUAGES_DB:
        assert lang.code, "Language code must not be empty"
        assert lang.name, "Language name must not be empty"
        assert lang.native_name, "Language native name must not be empty"
        assert lang.region in REGIONS, f"Invalid region: {lang.region}"
        assert lang.script, "Language script must not be empty"
        assert lang.code not in codes, f"Duplicate language code: {lang.code}"
        codes.add(lang.code)
    print(f"[PASS] All {len(codes)} language entries have valid schemas and unique codes.")


def test_regions_coverage():
    print("\n--- 2. Testing Regional Coverage ---")
    for reg in REGIONS:
        if reg == REGION_ALL:
            continue
        langs = [l for l in LANGUAGES_DB if l.region == reg]
        assert len(langs) > 0, f"Region '{reg}' has no languages!"
        print(f"[PASS] Region '{reg:30}': {len(langs):3} languages.")


def test_fuzzy_search_and_aliases():
    print("\n--- 3. Testing Fuzzy Search & Aliases ---")
    test_queries = [
        # (Query, Expected top match name)
        ("marathi", "Marathi"),
        ("marath", "Marathi"),
        ("mrathi", "Marathi"),
        ("latn", "Latin"),
        ("latin", "Latin"),
        ("romance", "Romansh"),
        ("idish", "Yiddish"),
        ("yiddish", "Yiddish"),
        ("deutsch", "German"),
        ("germany", "German"),
        ("francais", "French"),
        ("france", "French"),
        ("espanol", "Spanish"),
        ("spain", "Spanish"),
        ("bhojpur", "Bhojpuri"),
        ("bihar", "Bhojpuri"),
        ("sanskrit", "Sanskrit"),
        ("gujarati", "Gujarati"),
        ("russian", "Russian"),
        ("russia", "Russian"),
        ("japanese", "Japanese"),
        ("japan", "Japanese"),
    ]

    for q, expected in test_queries:
        res, suggestions = fuzzy_search_languages(q)
        assert len(res) > 0, f"No results for query '{q}'"
        top_name = res[0].name
        assert top_name.lower() == expected.lower() or any(r.name.lower() == expected.lower() for r in res[:3]), (
            f"Query '{q}' failed: expected '{expected}', got '{top_name}'"
        )
        print(f"[PASS] Search query '{q:12}' -> Top match: '{res[0].name}' ({res[0].native_name})")


def test_prompt_conditioning_modes():
    print("\n--- 4. Testing Prompt Conditioning Modes ---")

    # Mode 1: English Only (Default)
    en_prompt = format_language_prompt_instruction(["English"])
    assert "English Only" in en_prompt or "Primary Spoken Language: English" in en_prompt
    assert "ABSOLUTE PROHIBITION ON ROMANIZED TRANSLITERATION" in en_prompt
    assert "NEVER write 'majama'" in en_prompt
    print("[PASS] English Only mode formats correct translation & anti-romanization directives.")

    # Mode 2: Gujarati & Hindi Selected
    gh_prompt = format_language_prompt_instruction(["Gujarati", "Hindi"])
    assert "STRICT AUTHORIZED OUTPUT" in gh_prompt
    assert "Gujarati" in gh_prompt
    assert "Hindi" in gh_prompt
    assert "AUTHENTIC NATIVE SCRIPT" in gh_prompt
    print("[PASS] Multi-Language selected mode enforces native script and authorized output.")

    # Mode 3: Universal Mode (All 210+ Languages)
    all_names = [l.name for l in LANGUAGES_DB]
    univ_prompt = format_language_prompt_instruction(all_names)
    assert "Universal Multilingual Mode" in univ_prompt
    assert "200+" in univ_prompt
    print("[PASS] Universal Multilingual mode formats global catalog fidelity directives.")


if __name__ == "__main__":
    print("=" * 70)
    print("MULTILINGUAL LANGUAGES CATALOG & INTELLIGENCE VERIFICATION")
    print("=" * 70)
    test_catalog_integrity()
    test_regions_coverage()
    test_fuzzy_search_and_aliases()
    test_prompt_conditioning_modes()
    print("\n" + "=" * 70)
    print("ALL MULTILINGUAL CATALOG TESTS PASSED 100%!")
    print("=" * 70)
