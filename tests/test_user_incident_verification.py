"""
Verification test specifically addressing the 4 real-world user incidents:
1. Elimination of unsolicited trailing user name injection ('I am Sriniwas Awasthi')
2. Phonetic correction of 'Pass the neutral details' -> 'personal details'
3. Contextual correction of 'important quotes' -> 'important codes' in GitHub context
4. Elimination of false starts, stutters ('many living organisms, many wild living organisms'), stray 'Hello.'
5. Automatic Wispr Flow point-wise bullet formatting for advantage/feature lists
"""
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.vocabulary.vocab_engine import VocabEngine
from app.config import ConfigManager
from app.gemini_engine import GeminiEngine

def run_user_incident_tests():
    print("=" * 80)
    print("      GEMINI FLOW USER INCIDENT VERIFICATION & RECOVERY SUITE")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # TEST 1: GitHub Dictation Polish & Trailing Name Stripping
    # -------------------------------------------------------------------------
    print("\n[TEST 1] GitHub Dictation & Zero Unsolicited Name Injection")
    raw_p1 = (
        "Hey, can you just push all the important codes? Hey, can you just push all the important codes "
        "in the GitHub with, With all the important quotes by which if a user or another person who just wanted "
        "to View my or use my application. Can you able to use by using that GitHub repository zip code? "
        "So only insert important codes. Don't add any Pass the neutral details or credential information "
        "to the GitHub. I am Sriniwas Awasthi."
    )
    cm = ConfigManager()
    dict_rules = cm.get_dictionary()
    
    # Process through pipeline
    normalized_p1 = VocabEngine.normalize_text(raw_p1)
    final_p1 = GeminiEngine.apply_dictionary(normalized_p1, dict_rules)

    print(f"Input text ending: ... {raw_p1[-60:]}")
    print(f"Result text ending: ... {final_p1[-60:]}")

    # Assertions
    assert "I am Sriniwas Awasthi" not in final_p1, "Error: Unsolicited 'I am Sriniwas Awasthi' was not stripped!"
    assert "Pass the neutral" not in final_p1 and "past neutral" not in final_p1, "Error: 'Pass the neutral' was not corrected to 'personal'!"
    assert "personal details" in final_p1, "Error: 'personal details' missing from result!"
    assert "important quotes" not in final_p1, "Error: 'important quotes' was not corrected to 'important codes'!"
    assert "Hey, can you just push all the important codes? Hey, can you just push" not in final_p1, "Error: Repetition was not collapsed!"
    print("  [PASS] Trailing name injection stripped.")
    print("  [PASS] 'Pass the neutral details' -> 'personal details' corrected.")
    print("  [PASS] 'important quotes' -> 'important codes' corrected.")
    print("  [PASS] Repeated opener collapsed.")

    # -------------------------------------------------------------------------
    # TEST 2: Forest Advantages Dictation, Stutter Collapsing & Bullets
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Forest Advantages Dictation & Adaptive Bullet Formatting")
    raw_p2 = (
        "Hey, I was just thinking of some advantages. Yeah, I was just thinking of some advantages about the forest. "
        "As we know that the advantages, the forest have many advantages like it is the home for the many living organisms, "
        "many wild living organisms. It's also the it's also called the lungs of the earth and second it's also called "
        "the lungs of the heart of the earth. It provide us many herbal medicines and also many insights. Hello. "
        "And also it provide us many woods and other stuff. Also it have many minerals and the rivers by which we get "
        "many plenty of natural resources. It also has plenty of reservoirs which can help us."
    )

    normalized_p2 = VocabEngine.normalize_text(raw_p2)
    final_p2 = GeminiEngine.apply_dictionary(normalized_p2, dict_rules)

    print("\nFormatted Output:")
    print("-" * 50)
    print(final_p2)
    print("-" * 50)

    # Assertions
    assert "Hello." not in final_p2 and "Hello" not in final_p2, "Error: Stray mid-sentence 'Hello.' was not removed!"
    assert "many living organisms, many wild living organisms" not in final_p2, "Error: Stutter 'many living organisms' was not collapsed!"
    assert "many wild living organisms" in final_p2, "Error: Refined 'many wild living organisms' missing!"
    assert "It's also the it's also called" not in final_p2, "Error: Intervening stutter 'it's also the it's also called' was not collapsed!"
    assert "•" in final_p2, "Error: Wispr Flow Adaptive Bullet Formatting ('• ') was not applied to advantages list!"
    bullet_count = final_p2.count("•")
    assert bullet_count >= 3, f"Error: Expected at least 3 bullet points, found {bullet_count}!"
    print(f"  [PASS] {bullet_count} clean bullet points generated.")
    print("  [PASS] Stray mid-sentence 'Hello.' eliminated.")
    print("  [PASS] 'many living organisms, many wild living organisms' collapsed to 'many wild living organisms'.")
    print("  [PASS] Intervening 'it's also the it's also called' collapsed.")

    # -------------------------------------------------------------------------
    # TEST 3: Singular 'Advantage' Dictation & Clause-Level Verb Bullet Points
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Singular 'Advantage' Dictation & Verb-Clause Bullet Formatting")
    raw_p3 = (
        "Hey, I was just thinking of the some advantage of the forest. As forest give us home for many wild "
        "living organisms, are living organisms, called the lungs of the earth. provide us many herbs, medicines, "
        "provide us many woods and other stuffs. It also have many minerals and rivers which we get plenty of "
        "natural resources, have plenty of reservoirs which can help us in future."
    )

    normalized_p3 = VocabEngine.normalize_text(raw_p3)
    final_p3 = GeminiEngine.apply_dictionary(normalized_p3, dict_rules)

    print("\nFormatted Output (Rule-Based):")
    print("-" * 50)
    print(final_p3)
    print("-" * 50)

    assert "•" in final_p3, "Error: Bullets not generated for singular 'advantage' dictation!"
    p3_bullet_count = final_p3.count("•")
    assert p3_bullet_count >= 4, f"Error: Expected at least 4 bullet points, found {p3_bullet_count}!"
    assert ", are living organisms," not in final_p3, "Error: Stutter ', are living organisms,' not removed!"
    print(f"  [PASS] {p3_bullet_count} bullet points successfully generated for singular 'advantage'.")
    print("  [PASS] Stutter ', are living organisms,' cleanly eliminated.")

    print("\n" + "=" * 80)
    print("     ALL USER INCIDENT TESTS COMPLETED WITH 100% SUCCESS!")
    print("=" * 80)

if __name__ == "__main__":
    run_user_incident_tests()
