import os
import sys
import json
import subprocess
from manim import *

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.claude_client import ClaudeClient

# Configuration
OUTPUT_DIR = os.path.join("data", "temp", "manim_renders")
config.media_dir = OUTPUT_DIR
config.video_dir = os.path.join(OUTPUT_DIR, "videos")
config.quality = "high_quality"
config.preview = False

class GraphGenerator:
    """
    Create Manim visualizations from script data
    Supports multiple chart types and data sources
    """
    
    def __init__(self):
        self.claude = ClaudeClient()
        self.output_dir = OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
    
    def extract_or_fetch_data(self, stat_info):
        """
        Get data for visualization from various sources
        
        Args:
            stat_info: Dictionary with stat information from script analyzer
        
        Returns:
            Dictionary with data ready for visualization
        """
        # Check if we have explicit data
        if 'data' in stat_info:
            return stat_info['data']
        
        # Try to parse from stat_text using Claude
        if 'stat_text' in stat_info:
            return self._extract_data_with_claude(stat_info['stat_text'])
        
        # Fallback: create sample data
        return self._create_sample_data(stat_info)
    
    def _extract_data_with_claude(self, stat_text):
        """Use Claude to extract structured data from text"""
        prompt = f"""Extract numerical data from this text: "{stat_text}"

Return a JSON object with the data structure needed for visualization.
For example:
- If it mentions "Edgar has 60% win rate, Spike has 49%": {{"Edgar": 60, "Spike": 49}}
- If it's a single number: {{"value": <number>, "label": "<context>"}}

Return ONLY the JSON object."""

        result = self.claude.ask_json(prompt)
        return result if result else {}
    
    def _create_sample_data(self, stat_info):
        """Create sample data for demonstration"""
        if 'value' in stat_info and 'metric' in stat_info:
            return {
                stat_info.get('metric', 'Value'): stat_info['value']
            }
        return {"Sample": 50}
    
    def create_dynamic_scene(self, viz_type_or_config, data=None, scene_name=None):
        """
        Create a visualization scene
        
        Args:
            viz_type_or_config: Either a string ('line', 'bar') or a full config dict
            data: Dictionary with data to visualize (if viz_type_or_config is a string)
            scene_name: Name for the scene (auto-generated if None)
        
        Returns:
            Path to rendered video file
        """
        # Support both old format: create_dynamic_scene('line', {...}, 'name')
        # and new format: create_dynamic_scene({type: 'line', data: {...}, x_label: ..., y_label: ...}, 'name')
        if isinstance(viz_type_or_config, dict) and 'type' in viz_type_or_config:
            # New format with full config dict
            config = viz_type_or_config
            viz_type = config.get('type', 'line')
            actual_data = config.get('data', {})
            x_label = config.get('x_label')
            y_label = config.get('y_label')
            title = config.get('title')
            # scene_name is passed as second argument (data parameter) if it's a string
            if isinstance(data, str):
                scene_name = data
            data = actual_data
        else:
            # Old format: viz_type is a string like 'line', data is the data dict
            viz_type = viz_type_or_config
            # data is already set correctly
            x_label = None
            y_label = None
            title = None
        
        if scene_name is None:
            import time
            scene_name = f"Graph_{int(time.time())}"
        
        print(f"[GRAPH] Creating {config if isinstance(viz_type_or_config, dict) else viz_type} chart: {scene_name}")
        
        # Create the Python code for the scene
        if viz_type in ['bar', 'bar_chart']:
            scene_code = self._generate_bar_chart_code(data, scene_name, x_label, y_label, title)
        elif viz_type in ['line', 'line_graph']:
            scene_code = self._generate_line_graph_code(data, scene_name, x_label, y_label, title)
        elif viz_type == 'comparison':
            scene_code = self._generate_comparison_code(data, scene_name)
        else:
            # Default to bar chart
            scene_code = self._generate_bar_chart_code(data, scene_name, x_label, y_label, title)
        
        # Write scene to temporary file
        scene_file = os.path.join(self.output_dir, f"{scene_name}.py")
        with open(scene_file, 'w') as f:
            f.write(scene_code)
        
        # Render with Manim
        video_path = self._render_scene(scene_file, scene_name)
        
        return video_path
    
    def generate_bar_chart(self, data_dict, title="Chart"):
        """
        Generate a bar chart visualization
        
        Args:
            data_dict: Dictionary mapping labels to values {label: value}
            title: Chart title
        
        Returns:
            Path to rendered video
        """
        return self.create_dynamic_scene('bar', data_dict, title.replace(' ', '_'))
    
    def generate_line_graph(self, timeseries_data, title="Trend"):
        """
        Generate a line graph
        
        Args:
            timeseries_data: List of (x, y) tuples or dict with x and y lists
            title: Chart title
        
        Returns:
            Path to rendered video
        """
        return self.create_dynamic_scene('line', timeseries_data, title.replace(' ', '_'))
    
    def generate_comparison(self, before_after_data, title="Comparison"):
        """
        Generate before/after comparison visualization
        
        Args:
            before_after_data: Dict with 'before' and 'after' keys
            title: Chart title
        
        Returns:
            Path to rendered video
        """
        return self.create_dynamic_scene('comparison', before_after_data, title.replace(' ', '_'))
    
    def _generate_bar_chart_code(self, data, scene_name, x_label=None, y_label=None, title=None):
        """Generate Python code for a bar chart scene"""
        # Handle both old dict format and new labeled format
        if 'labels' in data and 'values' in data:
            names = data['labels']
            values = data['values']
            if not x_label:
                x_label = data.get('x_label', 'Category')
            if not y_label:
                y_label = data.get('y_label', 'Value')
        elif isinstance(data, dict):
            # Old format: dict of name: value
            names = list(data.keys())
            values = list(data.values())
            if not x_label:
                x_label = 'Category'
            if not y_label:
                y_label = 'Value'
        else:
            # Fallback
            names = ["Value"]
            values = [50]
            if not x_label:
                x_label = 'Category'
            if not y_label:
                y_label = 'Value'
        
        # Limit to 6 items for visual clarity
        if len(names) > 6:
            names = names[:6]
            values = values[:6]
        
        # Convert values to floats (in case they're strings)
        try:
            values = [float(v) for v in values]
        except (ValueError, TypeError):
            # If conversion fails, use dummy data
            values = [50] * len(names)
        
        # Normalize values to 0-1 range for display
        max_val = max(values) if values else 100
        normalized = [v / max_val for v in values]
        
        # Generate colors - gradient from blue to cyan
        colors = ['#0078D4', '#00A8E8', '#00D9FF', '#00E5FF', '#00F0FF', '#00FFFF'][:len(names)]
        
        code = f'''from manim import *
import os

OUTPUT_DIR = os.path.join("data", "temp", "manim_renders")
config.media_dir = OUTPUT_DIR
config.video_dir = os.path.join(OUTPUT_DIR, "videos")
config.quality = "high_quality"
config.preview = False

class {scene_name}(Scene):
    def construct(self):
        # Elegant dark theme
        self.camera.background_color = "#0a0a0a"
        
        # Data
        names = {names}
        values = {values}
        max_val = {max_val}
        num_bars = len(names)
        
        # Smart value formatting function
        def format_value(val, label):
            label_lower = label.lower()
            if 'revenue' in label_lower or 'million' in label_lower or '$m' in label_lower:
                return f"${{int(val)}}M"
            elif '%' in label_lower or 'rate' in label_lower or 'percent' in label_lower:
                if val >= 1:
                    return f"{{int(val)}}%"
                else:
                    return f"{{val:.1f}}%"
            elif val >= 1000:
                return f"{{int(val/1000)}}K"
            else:
                return f"{{int(val)}}"
        
        # Dynamic sizing based on number of bars
        if num_bars <= 3:
            bar_width = 1.4
            bar_spacing = 2.2
            font_size = 28
        elif num_bars <= 5:
            bar_width = 1.1
            bar_spacing = 1.8
            font_size = 24
        else:
            bar_width = 0.9
            bar_spacing = 1.5
            font_size = 20
        
        # Elegant axis labels - positioned to avoid overlap
        y_label = Text("{y_label}", font_size=28, color="#888888")
        y_label.rotate(90 * DEGREES)
        y_label.to_edge(LEFT, buff=0.4)
        
        x_label = Text("{x_label}", font_size=28, color="#888888")
        x_label.to_edge(DOWN, buff=0.6)
        
        # Create bars
        bars = VGroup()
        bar_labels = VGroup()
        value_labels = VGroup()
        
        total_width = num_bars * bar_spacing
        start_x = -total_width / 2 + bar_spacing / 2
        
        colors = {colors}
        
        for i, (name, value) in enumerate(zip(names, values)):
            # Calculate bar height (max 4.0 units to leave room)
            bar_height = max(0.3, (value / max_val) * 4.0)
            
            # Create elegant bar with rounded corners effect
            bar = RoundedRectangle(
                width=bar_width,
                height=bar_height,
                corner_radius=0.1,
                fill_color=colors[i % len(colors)],
                fill_opacity=0.9,
                stroke_color="#FFFFFF",
                stroke_width=1.5
            )
            
            x_pos = start_x + i * bar_spacing
            bar.move_to([x_pos, bar_height / 2 - 1.2, 0])
            
            # Name label below bar - truncate if too long
            name_str = str(name)[:10]
            name_label = Text(name_str, font_size=font_size, color="#CCCCCC")
            name_label.next_to(bar, DOWN, buff=0.25)
            
            # Value label above bar
            val_text = format_value(value, "{y_label}")
            value_label = Text(val_text, font_size=font_size - 2, color="#FFFFFF")
            value_label.next_to(bar, UP, buff=0.15)
            
            bars.add(bar)
            bar_labels.add(name_label)
            value_labels.add(value_label)
        
        # Animate
        self.play(Write(y_label), Write(x_label), run_time=0.5)
        self.play(Write(bar_labels), run_time=0.4)
        
        # Animate bars growing together for smoother effect
        self.play(
            *[GrowFromEdge(bar, DOWN) for bar in bars],
            *[FadeIn(val_label) for val_label in value_labels],
            run_time=1.2
        )
        
        self.wait(2)
'''
        return code
    
    def _generate_line_graph_code(self, data, scene_name, x_label=None, y_label=None, title=None):
        """Generate Python code for a line graph scene"""
        # Convert data to points
        if isinstance(data, dict):
            if 'x' in data and 'y' in data:
                x_vals = data['x']
                y_vals = data['y']
                if not x_label:
                    x_label = data.get('x_label', 'X-Axis')
                if not y_label:
                    y_label = data.get('y_label', 'Y-Axis')
            else:
                # Data is like {'Before Nerf': 60, 'After Nerf': 48}
                # For line graphs, we need numeric x values
                labels = list(data.keys())
                y_vals = list(data.values())
                x_vals = list(range(len(labels)))  # 0, 1, 2, ...
                
                if not x_label:
                    x_label = 'Category'
                if not y_label:
                    y_label = 'Value'
        elif isinstance(data, list):
            x_vals = [p[0] for p in data]
            y_vals = [p[1] for p in data]
            if not x_label:
                x_label = 'X-Axis'
            if not y_label:
                y_label = 'Y-Axis'
        else:
            x_vals = [0, 1, 2, 3]
            y_vals = [10, 20, 15, 25]
            if not x_label:
                x_label = 'X-Axis'
            if not y_label:
                y_label = 'Y-Axis'
        
        # Store labels for x-axis ticks if we have string labels
        x_tick_labels = None
        if isinstance(data, dict) and 'x' not in data:
            x_tick_labels = list(data.keys())
        
        # Convert all values to numbers (in case they're strings from Claude)
        try:
            x_vals = [float(x) for x in x_vals]
            y_vals = [float(y) for y in y_vals]
        except (ValueError, TypeError) as e:
            print(f"[WARNING] Failed to convert graph values to floats: {e}")
            # Use safe defaults
            x_vals = [0, 1, 2, 3]
            y_vals = [10, 20, 15, 25]
        
        # CRITICAL: Sort data by x-values to ensure proper left-to-right progression
        # This prevents the line from looping back on itself
        if len(x_vals) > 1:
            sorted_pairs = sorted(zip(x_vals, y_vals), key=lambda p: p[0])
            x_vals = [p[0] for p in sorted_pairs]
            y_vals = [p[1] for p in sorted_pairs]
            # Also sort x_tick_labels if they exist
            if x_tick_labels:
                # Re-sort labels to match new order
                original_pairs = list(zip(list(range(len(x_tick_labels))), x_tick_labels))
                # This is tricky - we need to map the sorted indices
                # For now, just regenerate sequential labels
                pass
        
        print(f"[GRAPH] Line graph data - X: {x_vals}, Y: {y_vals}")
        
        # Format y-axis values (e.g., 500000 -> "500K")
        max_y = max(y_vals)
        if max_y >= 1000000:
            y_format = "M"
            y_divisor = 1000000
        elif max_y >= 1000:
            y_format = "K"
            y_divisor = 1000
        else:
            y_format = ""
            y_divisor = 1
        
        code = f'''from manim import *
import os

OUTPUT_DIR = os.path.join("data", "temp", "manim_renders")
config.media_dir = OUTPUT_DIR
config.video_dir = os.path.join(OUTPUT_DIR, "videos")
config.quality = "high_quality"
config.preview = False

class {scene_name}(Scene):
    def construct(self):
        # Elegant dark theme
        self.camera.background_color = "#0a0a0a"
        
        # Data (already converted to floats in Python)
        x_vals = {x_vals}
        y_vals = {y_vals}
        
        # IMPORTANT: Sort data points by x-value to ensure proper time progression
        sorted_indices = sorted(range(len(x_vals)), key=lambda i: x_vals[i])
        x_vals = [x_vals[i] for i in sorted_indices]
        y_vals = [y_vals[i] for i in sorted_indices]
        
        # Calculate proper ranges with MORE padding on left for first data point
        x_min_data, x_max_data = min(x_vals), max(x_vals)
        y_min_data, y_max_data = 0, max(y_vals)
        
        # Add MORE padding to prevent edge clipping - especially on left
        x_range_span = max(1, x_max_data - x_min_data)
        x_padding_left = max(0.8, x_range_span * 0.25)  # More padding on left
        x_padding_right = max(0.5, x_range_span * 0.15)
        y_padding = y_max_data * 0.2
        
        # Create sleek axes with proper sizing to avoid overlap
        axes = Axes(
            x_range=[x_min_data - x_padding_left, x_max_data + x_padding_right, max(1, x_range_span / 4)],
            y_range=[0, y_max_data + y_padding, max(1, y_max_data / 4)],
            x_length=8,  # Slightly smaller to leave room for labels
            y_length=5,
            axis_config={{
                "color": "#333333",
                "stroke_width": 2,
                "include_tip": False,
                "include_numbers": False  # We add custom labels
            }}
        )
        
        # Center the axes slightly right to make room for y-label
        axes.shift(RIGHT * 0.5)
        
        # Sleek, modern axis labels - positioned to avoid overlap
        x_label_text = Text("{x_label}", font_size=28, color="#888888")
        x_label_text.next_to(axes.x_axis, DOWN, buff=0.6)
        
        y_label_text = Text("{y_label}", font_size=28, color="#888888")
        y_label_text.rotate(90 * DEGREES)
        y_label_text.next_to(axes.y_axis, LEFT, buff=0.8)
        
        # Format y-axis numbers (e.g., 500K instead of 500000)
        y_divisor = {y_divisor}
        y_suffix = "{y_format}"
        
        def format_y(val):
            if y_divisor > 1:
                return f"{{int(val/y_divisor)}}{{y_suffix}}"
            return f"{{int(val)}}"
        
        # Add y-axis value labels at proper intervals
        y_labels = VGroup()
        y_step = max(1, y_max_data / 4)
        for i in range(1, 5):
            y_val = y_step * i
            if y_val <= y_max_data + y_padding:
                label = Text(format_y(y_val), font_size=20, color="#666666")
                label.next_to(axes.c2p(x_min_data - x_padding_left, y_val), LEFT, buff=0.2)
                y_labels.add(label)
        
        # Add x-axis labels (custom text or numeric)
        x_tick_labels = {x_tick_labels}
        x_labels = VGroup()
        for i, x_val in enumerate(x_vals):
            if x_tick_labels and i < len(x_tick_labels):
                label_text = str(x_tick_labels[i])[:12]  # Truncate long labels
            else:
                label_text = str(int(x_val))
            label = Text(label_text, font_size=22, color="#666666")
            label.next_to(axes.c2p(x_val, 0), DOWN, buff=0.25)
            x_labels.add(label)
        
        # Create line graph - use straight line segments (no smooth curves that can loop)
        points = [axes.c2p(x, y) for x, y in zip(x_vals, y_vals)]
        
        # Use Line objects connected together for clean, non-looping lines
        graph_lines = VGroup()
        for i in range(len(points) - 1):
            line_segment = Line(points[i], points[i+1], stroke_width=4)
            # Gradient from cyan to blue
            progress = i / max(1, len(points) - 2)
            color = interpolate_color(ManimColor("#00D9FF"), ManimColor("#0078D4"), progress)
            line_segment.set_color(color)
            graph_lines.add(line_segment)
        
        # Add glowing dots at data points with value labels
        dots = VGroup()
        value_labels = VGroup()
        for x, y in zip(x_vals, y_vals):
            dot_outer = Dot(axes.c2p(x, y), radius=0.12, color="#00D9FF", fill_opacity=0.3)
            dot_inner = Dot(axes.c2p(x, y), radius=0.06, color="#FFFFFF")
            dots.add(dot_outer, dot_inner)
            
            # Add value label above dot
            val_label = Text(format_y(y), font_size=18, color="#FFFFFF")
            val_label.next_to(axes.c2p(x, y), UP, buff=0.15)
            value_labels.add(val_label)
        
        # Smooth animations
        self.play(
            Create(axes),
            Write(x_label_text),
            Write(y_label_text),
            run_time=0.8
        )
        self.play(
            Write(y_labels),
            Write(x_labels),
            run_time=0.6
        )
        # Animate line segments appearing one by one
        for line_seg in graph_lines:
            self.play(Create(line_seg), run_time=0.4)
        self.play(
            FadeIn(dots),
            FadeIn(value_labels),
            run_time=0.4
        )
        self.wait(2)
'''
        return code
    
    def _generate_comparison_code(self, data, scene_name):
        """Generate code for before/after comparison"""
        before_val = data.get('before', 50)
        after_val = data.get('after', 75)
        
        code = f'''from manim import *
import os

OUTPUT_DIR = os.path.join("data", "temp", "manim_renders")
config.media_dir = OUTPUT_DIR
config.video_dir = os.path.join(OUTPUT_DIR, "videos")
config.quality = "high_quality"
config.preview = False

class {scene_name}(Scene):
    def construct(self):
        # Before/After values
        before_val = {before_val}
        after_val = {after_val}
        
        # Create bars
        before_bar = Rectangle(width=1.5, height=before_val/20, color=RED, fill_opacity=0.8)
        after_bar = Rectangle(width=1.5, height=after_val/20, color=GREEN, fill_opacity=0.8)
        
        # Position bars
        before_bar.shift(LEFT * 2.5)
        after_bar.shift(RIGHT * 2.5)
        
        # Labels
        before_lbl = Text("Before", font_size=24).next_to(before_bar, DOWN)
        after_lbl = Text("After", font_size=24).next_to(after_bar, DOWN)
        before_val_lbl = Text(str(before_val), font_size=30).next_to(before_bar, UP)
        after_val_lbl = Text(str(after_val), font_size=30).next_to(after_bar, UP)
        
        # Animate
        self.play(GrowFromEdge(before_bar, DOWN), FadeIn(before_lbl), FadeIn(before_val_lbl))
        self.wait(0.5)
        self.play(GrowFromEdge(after_bar, DOWN), FadeIn(after_lbl), FadeIn(after_val_lbl))
        self.wait(2)
'''
        return code
    
    def _render_scene(self, scene_file, scene_name):
        """Render a Manim scene and return path to video"""
        try:
            print(f"[GRAPH] Rendering scene with Manim...")
            
            # Run manim command with full output
            cmd = f"manim -qm {scene_file} {scene_name}"  # Changed to medium quality for speed
            print(f"[GRAPH] Running: {cmd}")
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"[ERROR] Manim rendering failed!")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                return None
            
            print(f"[GRAPH] Manim output: {result.stdout[:200]}")
            
            # Find the rendered video
            video_path = self._find_rendered_video(scene_name)
            
            if video_path:
                print(f"[GRAPH] Rendered successfully: {video_path}")
                return video_path
            else:
                print(f"[ERROR] Could not find rendered video for {scene_name}")
                print(f"[DEBUG] Searching in: {os.path.join(self.output_dir, 'videos')}")
                return None
                
        except Exception as e:
            print(f"[ERROR] Rendering failed: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _find_rendered_video(self, scene_name):
        """Find where Manim saved the video"""
        search_dir = os.path.join(self.output_dir, "videos")
        
        for root, dirs, files in os.walk(search_dir):
            for file in files:
                if file == f"{scene_name}.mp4":
                    return os.path.join(root, file)
        
        return None


if __name__ == "__main__":
    # Test the graph generator
    print("=" * 60)
    print("Testing Graph Generator")
    print("=" * 60)
    
    generator = GraphGenerator()
    
    # Test bar chart
    test_data = {
        "Edgar": 60,
        "Fang": 58,
        "Crow": 52,
        "Spike": 49
    }
    
    print("\nGenerating bar chart...")
    video_path = generator.generate_bar_chart(test_data, "TestWinRates")
    
    if video_path:
        print(f"Success! Video at: {video_path}")
    else:
        print("Failed to generate chart")
