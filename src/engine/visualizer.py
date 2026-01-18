from manim import *
import os

# --- CONFIGURATION ---
OUTPUT_DIR = os.path.join("data", "temp", "manim_renders")
config.media_dir = OUTPUT_DIR
config.video_dir = os.path.join(OUTPUT_DIR, "videos")
config.quality = "high_quality" # Forces 1080p (1920x1080)
config.preview = False

class BrawlerWinRateChart(Scene):
    def construct(self):
        # 1. THE DATA
        data = {"Fang": 0.58, "Crow": 0.52, "Spike": 0.49, "Edgar": 0.45}
        names = list(data.keys())
        values = list(data.values())
        colors = [RED, BLUE, PURPLE, ORANGE]

        # 2. DRAW EVERYTHING
        # We create a Group so we can center the whole thing later
        chart_group = VGroup()

        # Axes
        # 7 units wide, 5 units tall
        x_axis = Line(start=ORIGIN, end=RIGHT * 7)
        y_axis = Line(start=ORIGIN, end=UP * 5)
        y_label = Text("Win Rate", font_size=24).next_to(y_axis, UP)
        
        axes = VGroup(x_axis, y_axis, y_label)
        chart_group.add(axes)

        # Bars
        bar_spacing = 7.0 / len(names)
        
        for i, (name, value) in enumerate(zip(names, values)):
            bar_height = value * 5.0
            
            bar = Rectangle(
                width=0.8, 
                height=bar_height, 
                color=colors[i], 
                fill_opacity=0.8
            )
            
            # Position relative to the axes we just made
            x_pos = RIGHT * (i * bar_spacing + 0.8)
            bar.move_to(x_pos, aligned_edge=DOWN)
            
            name_lbl = Text(name, font_size=24).next_to(bar, DOWN)
            val_lbl = Text(f"{int(value*100)}%", font_size=24).next_to(bar, UP)
            
            # Add to group
            chart_group.add(bar, name_lbl, val_lbl)
            
            # Animation
            self.play(GrowFromEdge(bar, DOWN), FadeIn(name_lbl), FadeIn(val_lbl), run_time=0.5)

        # 3. THE FIX: CENTER EVERYTHING
        # Now that it's drawn, we grab the whole group and shove it to the center of the screen
        self.play(chart_group.animate.move_to(ORIGIN))
        
        self.wait(2)

if __name__ == "__main__":
    # -qh = High Quality (1080p)
    os.system(f"manim -qh src/engine/visualizer.py BrawlerWinRateChart")