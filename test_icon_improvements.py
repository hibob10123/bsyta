"""Test the improved icon search with context-aware queries"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scrapers.asset_gatherer import AssetGatherer

print("="*70)
print("TESTING IMPROVED ICON SEARCH")
print("="*70)
print("\nThis test will show how Claude generates context-aware search queries.\n")

gatherer = AssetGatherer()

# Test cases that were problematic before
test_cases = [
    {
        "keyword": "record",
        "context": "Brawl Stars",
        "sentence": "It hit a record 84 million monthly players, fueled by the massive Toy Story collaboration.",
        "expected": "Simple trophy/achievement icon (NOT music record, NO watermarks)"
    },
    {
        "keyword": "Brawl Stars",
        "context": "Brawl Stars",
        "sentence": "In December 2024, Brawl Stars was on top of the world.",
        "expected": "Brawl Stars game logo (clean, official)"
    },
    {
        "keyword": "Buzz Lightyear",
        "context": "Brawl Stars",
        "sentence": "And the cause of that high—the Buzz Lightyear brawler—was the very thing that started the rot.",
        "expected": "Buzz Lightyear from Brawl Stars (FULL NAME, not just 'Buzz')"
    },
    {
        "keyword": "peak",
        "context": "Brawl Stars",
        "sentence": "But this was a 'hollow peak.'",
        "expected": "Simple mountain peak icon (flat design, no stock photo watermarks)"
    },
    {
        "keyword": "rot",
        "context": "Brawl Stars",
        "sentence": "And the cause of that high—the Buzz Lightyear brawler—was the very thing that started the rot.",
        "expected": "Simple downward arrow icon (NOT complex stock photo with gears)"
    }
]

print("\nSearching for icons with improved context awareness...")
print("NOTE: Using force_redownload=True to bypass old cached icons\n")

for i, test in enumerate(test_cases):
    print(f"--- TEST {i+1}: '{test['keyword']}' ---")
    print(f"Context: {test['context']}")
    print(f"Sentence: {test['sentence'][:80]}...")
    print(f"Expected: {test['expected']}")
    
    # This will trigger the improved _generate_icon_search_query
    # force_redownload=True ensures we get fresh icons with new search queries
    icon_path = gatherer.find_icon(
        test['keyword'],
        context=test['context'],
        sentence_context=test['sentence'],
        force_redownload=True  # Skip cache, download fresh
    )
    
    if icon_path:
        print(f"✓ Icon saved: {icon_path}")
    else:
        print(f"✗ Failed to find icon")
    
    print()

print("="*70)
print("ICON SEARCH TEST COMPLETE")
print("="*70)
print("\nCheck the output above to see the search queries Claude generated.")
print("They should be context-aware and semantically correct!")
print("\nIcons saved to: data/assets/icons/")
print("Manually inspect them to verify they match the expected type.")
