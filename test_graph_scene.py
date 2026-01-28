"""
Test script specifically for graph visualization scenes.
Tests graph generation, axis labels, data accuracy, and scene rendering.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import VideoAutomationPipeline

# Test script with EXPLICIT statistics that should generate graphs
# Format: Include clear numerical comparisons
SCRIPT = """
The player count has dropped dramatically. In January 2024, Brawl Stars had 50 million monthly players. 
By June 2024, that number fell to 35 million. And now in January 2025, it's down to just 28 million players.

Looking at win rates, Edgar dominates with a 62 percent win rate. Fang follows at 58 percent. 
Meanwhile Crow sits at 52 percent and Spike struggles at just 48 percent.
"""

# Alternative simpler script if above doesn't work
SIMPLE_SCRIPT = """
Edgar has a 62 percent win rate while Spike only has 48 percent. 
The revenue dropped from 84 million dollars in 2023 to 65 million in 2024.
"""

def test_graph_generation_only():
    """Test just the graph generator directly"""
    print("\n" + "="*70)
    print("TEST 1: Direct Graph Generation")
    print("="*70)
    
    from src.engine.graph_generator import GraphGenerator
    
    generator = GraphGenerator()
    
    # Test 1A: Bar chart with win rates
    print("\n[TEST 1A] Bar Chart - Win Rates")
    bar_data = {
        "labels": ["Edgar", "Fang", "Crow", "Spike"],
        "values": [62, 58, 52, 48],
        "x_label": "Brawler",
        "y_label": "Win Rate (%)"
    }
    
    bar_config = {
        "type": "bar",
        "data": bar_data,
        "x_label": "Brawler",
        "y_label": "Win Rate (%)",
        "title": "Win Rates by Brawler"
    }
    
    bar_path = generator.create_dynamic_scene(bar_config, "Test_WinRates_Bar")
    if bar_path:
        print(f"  [OK] Bar chart generated: {bar_path}")
    else:
        print(f"  [FAIL] Bar chart generation failed!")
    
    # Test 1B: Line chart with player counts
    print("\n[TEST 1B] Line Chart - Player Count Trend")
    line_data = {
        "x": [1, 2, 3],  # Jan 2024, Jun 2024, Jan 2025
        "y": [50, 35, 28],  # Millions
        "x_label": "Time Period",
        "y_label": "Players (Millions)"
    }
    
    line_config = {
        "type": "line",
        "data": line_data,
        "x_label": "Time Period",
        "y_label": "Monthly Players (Millions)",
        "title": "Player Count Decline"
    }
    
    line_path = generator.create_dynamic_scene(line_config, "Test_PlayerCount_Line")
    if line_path:
        print(f"  [OK] Line chart generated: {line_path}")
    else:
        print(f"  [FAIL] Line chart generation failed!")
    
    # Test 1C: Bar chart with revenue (tests $ formatting)
    print("\n[TEST 1C] Bar Chart - Revenue ($M)")
    revenue_data = {
        "labels": ["2022", "2023", "2024"],
        "values": [95, 84, 65],
        "x_label": "Year",
        "y_label": "Revenue ($M)"
    }
    
    revenue_config = {
        "type": "bar",
        "data": revenue_data,
        "x_label": "Year", 
        "y_label": "Revenue ($M)",
        "title": "Annual Revenue"
    }
    
    revenue_path = generator.create_dynamic_scene(revenue_config, "Test_Revenue_Bar")
    if revenue_path:
        print(f"  [OK] Revenue chart generated: {revenue_path}")
    else:
        print(f"  [FAIL] Revenue chart generation failed!")
    
    return [bar_path, line_path, revenue_path]


def test_graph_in_video():
    """Test full pipeline with graph scenes"""
    print("\n" + "="*70)
    print("TEST 2: Full Pipeline with Graph Scenes")
    print("="*70)
    
    pipeline = VideoAutomationPipeline()
    
    result = pipeline.run_full_pipeline(
        script_text=SCRIPT,
        output_name="graph_test",
        youtube_videos=None  # No YouTube videos for this test
    )
    
    if result:
        print(f"\n[OK] Video generated: {result}")
        print("\nCheck the video for:")
        print("  1. Graph scenes appear at correct times")
        print("  2. Correct axis labels (Win Rate %, Players, etc.)")
        print("  3. Data values match the script")
        print("  4. No overlapping text")
        print("  5. Proper animations")
    else:
        print("\n[FAIL] Video generation failed!")


def test_graph_metadata_matching():
    """Test that graphs are matched to correct script segments"""
    print("\n" + "="*70)
    print("TEST 3: Graph Metadata Matching")
    print("="*70)
    
    from src.analysis.script_analyzer import ScriptAnalyzer
    from src.engine.graph_generator import GraphGenerator
    
    analyzer = ScriptAnalyzer()
    generator = GraphGenerator()
    
    # Analyze the script
    analysis = analyzer.analyze_script(SCRIPT)
    
    print(f"\n[ANALYSIS] Found {len(analysis.get('statistics', []))} statistics:")
    for i, stat in enumerate(analysis.get('statistics', [])):
        print(f"  {i+1}. {stat.get('stat_text', 'N/A')[:60]}...")
        print(f"      Type: {stat.get('type', 'unknown')}")
        print(f"      Values: {stat.get('values', [])}")
    
    print(f"\n[ANALYSIS] Found {len(analysis.get('claims', []))} claims:")
    for i, claim in enumerate(analysis.get('claims', [])):
        print(f"  {i+1}. {claim.get('claim_text', 'N/A')[:60]}...")
    
    # Generate graphs for each statistic
    print("\n[GENERATION] Creating graphs for statistics...")
    graphs = []
    for i, stat in enumerate(analysis.get('statistics', [])):
        print(f"\n  Processing stat {i+1}...")
        
        # Extract data
        data = generator.extract_or_fetch_data(stat)
        print(f"    Extracted data: {data}")
        
        if data:
            # Determine chart type
            chart_type = 'bar' if stat.get('type') == 'comparison' else 'line'
            
            graph_path = generator.create_dynamic_scene(
                chart_type, 
                data, 
                f"Test_Stat_{i}"
            )
            
            if graph_path:
                graphs.append({
                    'path': graph_path,
                    'stat_text': stat.get('stat_text', ''),
                    'type': chart_type
                })
                print(f"    [OK] Generated: {os.path.basename(graph_path)}")
            else:
                print(f"    [FAIL] Generation failed")
    
    print(f"\n[RESULT] Generated {len(graphs)} graphs")
    return graphs


def test_graph_scene_rendering():
    """Test the director's graph scene rendering specifically"""
    print("\n" + "="*70)
    print("TEST 4: Graph Scene Rendering")
    print("="*70)
    
    # First generate a test graph
    from src.engine.graph_generator import GraphGenerator
    generator = GraphGenerator()
    
    test_data = {
        "labels": ["A", "B", "C", "D"],
        "values": [80, 60, 45, 30],
        "x_label": "Category",
        "y_label": "Value (%)"
    }
    
    graph_path = generator.create_dynamic_scene({
        "type": "bar",
        "data": test_data,
        "x_label": "Category",
        "y_label": "Value (%)"
    }, "Test_Render_Graph")
    
    if not graph_path:
        print("[FAIL] Could not generate test graph")
        return
    
    print(f"[OK] Test graph generated: {graph_path}")
    
    # Now test rendering it in a scene
    from src.engine.director_v3 import VideoDirector
    from moviepy.editor import concatenate_videoclips
    
    director = VideoDirector()
    
    # Create a mock timeline with just a graph scene
    mock_timeline = {
        'scenes': [{
            'scene_number': 1,
            'type': 'data_graph',
            'start_time': 0.0,
            'end_time': 4.0,
            'elements': [{
                'type': 'graph',
                'index': 0,
                'timestamp': 0.0
            }]
        }]
    }
    
    # Set up graph metadata
    director.graph_metadata = [{
        'path': graph_path,
        'description': 'Test graph'
    }]
    
    print("\n[RENDERING] Creating graph scene...")
    scene_clip = director._create_data_graph_scene(mock_timeline['scenes'][0], 4.0)
    
    if scene_clip:
        print(f"[OK] Scene created, duration: {scene_clip.duration}s")
        
        # Save a test video
        output_path = "data/output/graph_scene_test.mp4"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        scene_clip.write_videofile(
            output_path,
            fps=30,
            codec='h264_nvenc',
            audio=False
        )
        print(f"[OK] Test video saved: {output_path}")
        scene_clip.close()
    else:
        print("[FAIL] Scene creation failed")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test graph scene generation')
    parser.add_argument('--test', type=int, default=0, 
                       help='Run specific test (1-4) or 0 for all')
    args = parser.parse_args()
    
    print("="*70)
    print("GRAPH SCENE TEST SUITE")
    print("="*70)
    print("\nThis will test:")
    print("  1. Direct graph generation (bar/line charts)")
    print("  2. Full pipeline with graph scenes")
    print("  3. Graph metadata matching to script")
    print("  4. Director graph scene rendering")
    
    if args.test == 0 or args.test == 1:
        test_graph_generation_only()
    
    if args.test == 0 or args.test == 3:
        test_graph_metadata_matching()
    
    if args.test == 0 or args.test == 4:
        test_graph_scene_rendering()
    
    if args.test == 0 or args.test == 2:
        test_graph_in_video()
    
    print("\n" + "="*70)
    print("TESTS COMPLETE")
    print("="*70)
    print("\nCheck the generated files in data/output/")
    print("Look for issues like:")
    print("  - Wrong graphs shown for script content")
    print("  - Incorrect axis labels")
    print("  - Overlapping text/elements")
    print("  - Missing animations")
