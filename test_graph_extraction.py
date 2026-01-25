"""Test that the time-series data is properly extracted for graph generation"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from analysis.script_analyzer import ScriptAnalyzer

print("="*70)
print("TESTING: Time-Series Data Extraction for Graph")
print("="*70)

script = """
In December 2024, Brawl Stars exploded to 84 million players—up from 
65 million in 2022 and 50 million back in 2020. This massive growth 
was fueled by the Toy Story collaboration.
"""

print("\nScript:")
print(script)
print("\n" + "-"*70)

analyzer = ScriptAnalyzer()
analysis = analyzer.analyze_script(script)

stats = analysis.get('statistics', [])

print(f"\nExtracted {len(stats)} statistic(s):")
print("-"*70)

if len(stats) == 0:
    print("❌ NO STATISTICS EXTRACTED!")
    print("\nExpected to find:")
    print("  - 2020: 50 million players")
    print("  - 2022: 65 million players")
    print("  - 2024: 84 million players")
    print("\nThis should generate a LINE CHART showing growth over time.")
else:
    for i, stat in enumerate(stats):
        print(f"\n{i+1}. {stat.get('stat_text', 'Unknown')}")
        print(f"   Value: {stat.get('value', 0)}")
        print(f"   Metric: {stat.get('metric', 'unknown')}")
        print(f"   Context: {stat.get('context', 'none')}")
        print(f"   Viz Type: {stat.get('visualization_type', 'bar')}")

print("\n" + "="*70)
print("VALIDATION:")
print("="*70)

if len(stats) >= 3:
    print(f"✅ SUCCESS! Extracted {len(stats)} data points")
    print("   This will generate a LINE CHART showing player growth over time")
    
    # Check if they have the right metric
    same_metric = len(set(s.get('metric') for s in stats)) == 1
    if same_metric:
        print(f"✅ All statistics share the same metric: {stats[0].get('metric')}")
    else:
        print("⚠️  Statistics have different metrics - might create separate graphs")
    
    # Check for years in context
    has_years = any(c and any(year in str(c) for year in ['2020', '2022', '2024']) 
                    for s in stats for c in [s.get('context')])
    if has_years:
        print("✅ Year information found in context - will create time-series line chart")
    else:
        print("⚠️  No year information in context - might default to bar chart")
        
elif len(stats) == 2:
    print(f"⚠️  Only {len(stats)} data points extracted")
    print("   Expected 3 points (2020, 2022, 2024)")
    print("   Will still create a graph, but missing a data point")
elif len(stats) == 1:
    print(f"❌ Only {len(stats)} data point extracted")
    print("   Cannot create a graph with single data point")
    print("   Need at least 2 points for comparison/trend")
else:
    print("❌ No statistics extracted - no graph will be generated")

print("\n💡 TIP: Run 'python test_full_paragraph.py' to see the full pipeline with graph")
