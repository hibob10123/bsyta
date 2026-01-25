import os
import sys

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.claude_client import ClaudeClient

class ResearchAssistant:
    """
    Optional research assistant to help with script writing
    Uses Claude to research topics and suggest script structure
    """
    
    def __init__(self):
        self.claude = ClaudeClient()
    
    def research_topic(self, topic, depth="medium"):
        """
        Research a topic and provide key points
        
        Args:
            topic: What to research (game, character, controversy, etc.)
            depth: "light", "medium", or "deep"
        
        Returns:
            Dictionary with research findings
        """
        print(f"[RESEARCH] Researching topic: {topic}")
        
        depth_instructions = {
            "light": "Provide 3-5 key points",
            "medium": "Provide 5-8 key points with context",
            "deep": "Provide detailed analysis with 10+ points, statistics, and context"
        }
        
        system_prompt = """You are a gaming research assistant specializing in documentary-style video content.
Research topics thoroughly and provide structured information suitable for video scripts."""

        user_prompt = f"""Research this topic for a YouTube video: {topic}

Depth level: {depth} - {depth_instructions.get(depth, '')}

Provide a JSON response with:
{{
    "topic": "{topic}",
    "key_points": [
        {{"point": "Main point 1", "details": "Supporting details", "source_hint": "Where this info comes from"}},
        {{"point": "Main point 2", "details": "Supporting details", "source_hint": "Where this info comes from"}}
    ],
    "statistics": [
        {{"stat": "60% win rate", "context": "In which mode/timeframe"}},
    ],
    "controversies": ["List any controversies or community debates"],
    "suggested_angle": "How to approach this topic for a video"
}}

Return ONLY the JSON."""

        research = self.claude.ask_json(user_prompt, system_prompt)
        
        if research:
            print(f"[RESEARCH] Found {len(research.get('key_points', []))} key points")
            return research
        else:
            print("[WARNING] Research failed")
            return {'topic': topic, 'key_points': [], 'statistics': [], 'controversies': []}
    
    def suggest_script_structure(self, topic=None, research_data=None):
        """
        Suggest a script structure/outline
        
        Args:
            topic: Video topic
            research_data: Optional research findings from research_topic()
        
        Returns:
            Script outline/structure
        """
        print("[RESEARCH] Suggesting script structure...")
        
        if research_data:
            context = f"Research findings:\n{self._format_research(research_data)}"
        else:
            context = f"Topic: {topic}"
        
        system_prompt = """You are an expert YouTube scriptwriter specializing in gaming documentary content.
Create engaging script structures that hook viewers and maintain interest."""

        user_prompt = f"""{context}

Create a script structure for a 3-5 minute video. Include:

1. Hook (first 5-10 seconds to grab attention)
2. Main content sections (2-3 sections)
3. Evidence/examples for each section
4. Conclusion

Provide the structure as a JSON with:
{{
    "hook": "Opening line that grabs attention",
    "sections": [
        {{
            "title": "Section name",
            "key_points": ["Point 1", "Point 2"],
            "suggested_visuals": ["What to show"]
        }}
    ],
    "conclusion": "Closing thoughts"
}}

Return ONLY the JSON."""

        structure = self.claude.ask_json(user_prompt, system_prompt)
        
        if structure:
            print("[RESEARCH] Script structure created")
            return structure
        else:
            return None
    
    def enhance_script(self, draft_script):
        """
        Review and suggest improvements to a script draft
        
        Args:
            draft_script: User's draft script
        
        Returns:
            Dictionary with feedback and suggestions
        """
        print("[RESEARCH] Reviewing script draft...")
        
        system_prompt = """You are a YouTube script editor specializing in gaming content.
Provide constructive feedback to improve engagement, pacing, and clarity."""

        user_prompt = f"""Review this video script draft:

{draft_script}

Provide feedback as JSON:
{{
    "overall_score": 1-10,
    "strengths": ["What works well"],
    "improvements": ["What could be better"],
    "pacing_notes": "Is it too slow/fast?",
    "hook_quality": 1-10,
    "suggested_edits": [
        {{"original": "weak line", "improved": "stronger version", "reason": "why"}}
    ]
}}

Return ONLY the JSON."""

        feedback = self.claude.ask_json(user_prompt, system_prompt, temperature=0.5)
        
        if feedback:
            score = feedback.get('overall_score', 5)
            print(f"[RESEARCH] Script score: {score}/10")
            return feedback
        else:
            return None
    
    def _format_research(self, research_data):
        """Format research data for prompts"""
        lines = []
        
        if 'key_points' in research_data:
            lines.append("Key Points:")
            for point in research_data['key_points'][:5]:
                lines.append(f"  - {point.get('point', '')}")
        
        if 'statistics' in research_data:
            lines.append("\nStatistics:")
            for stat in research_data['statistics']:
                lines.append(f"  - {stat.get('stat', '')}")
        
        return '\n'.join(lines)


if __name__ == "__main__":
    # Test the research assistant
    print("=" * 60)
    print("Testing Research Assistant")
    print("=" * 60)
    
    assistant = ResearchAssistant()
    
    # Test research
    print("\n1. Researching topic...")
    research = assistant.research_topic("Edgar character in Brawl Stars", depth="medium")
    
    if research:
        print(f"\nResearch results:")
        print(f"  Key points: {len(research.get('key_points', []))}")
        print(f"  Statistics: {len(research.get('statistics', []))}")
    
    # Test script structure
    print("\n2. Creating script structure...")
    structure = assistant.suggest_script_structure(
        topic="Edgar in Brawl Stars",
        research_data=research
    )
    
    if structure:
        print("\nScript structure created successfully")
