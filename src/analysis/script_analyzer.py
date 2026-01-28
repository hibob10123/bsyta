import os
import sys
import json
import re

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from utils.claude_client import ClaudeClient
from utils.timing_utils import estimate_speech_duration

class ScriptAnalyzer:
    """
    Uses Claude to analyze video scripts and extract structured information
    for automated video production
    """
    
    def __init__(self):
        # Use very high max_tokens for script analysis (long scripts = huge JSON responses)
        # For 800-word scripts, Claude might return 15K+ tokens of structured data
        self.claude = ClaudeClient(max_tokens=16000)
    
    def detect_sections(self, script_text):
        """
        Detect natural section breaks in the script.
        
        Detects patterns like:
        - Roman numerals: "I.", "II.", "III.", etc.
        - Part markers: "Part 1", "Part 2", "Part I", etc.
        - Chapter markers: "Chapter 1", "Chapter 2", etc.
        - Numbered headers: "1.", "2.", "3." at line starts
        - Markdown headers: "# ", "## ", etc.
        - Section dividers: "---", "===", "***"
        
        Args:
            script_text: Full script text
        
        Returns:
            List of section dicts: [
                {"number": 1, "title": "Introduction", "text": "...", "start_line": 0},
                {"number": 2, "title": "Part II", "text": "...", "start_line": 15},
                ...
            ]
        """
        print("[ANALYZER] Detecting script sections...")
        
        # Section header patterns (ordered by priority)
        patterns = [
            # Roman numerals with optional title: "II. Killing the Why" or just "II."
            (r'^(?:^|\n)\s*((?:I{1,3}|IV|V|VI{0,3}|IX|X{0,3})(?:\.|:|\s*[-–—]))\s*(.*)$', 'roman'),
            # Part markers: "Part 1:", "Part II", "PART ONE"
            (r'^(?:^|\n)\s*(?:PART|Part)\s+(\d+|[IVXivx]+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)[\s:.\-–—]*(.*)$', 'part'),
            # Chapter markers: "Chapter 1:", "CHAPTER 2"
            (r'^(?:^|\n)\s*(?:CHAPTER|Chapter)\s+(\d+|[IVXivx]+)[\s:.\-–—]*(.*)$', 'chapter'),
            # Numbered headers at line start: "1. Introduction"
            (r'^(?:^|\n)\s*(\d+)[\.\)]\s+([A-Z][^\n]{0,60})$', 'numbered'),
            # Markdown headers: "# Title" or "## Title"
            (r'^(?:^|\n)\s*(#{1,3})\s+(.+)$', 'markdown'),
        ]
        
        # Divider patterns (these split sections but don't have titles)
        divider_patterns = [
            r'^(?:^|\n)\s*[-]{3,}\s*$',   # ---
            r'^(?:^|\n)\s*[=]{3,}\s*$',   # ===
            r'^(?:^|\n)\s*[*]{3,}\s*$',   # ***
            r'^(?:^|\n)\s*[_]{3,}\s*$',   # ___
        ]
        
        sections = []
        lines = script_text.split('\n')
        
        # Find all section markers
        section_markers = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Check for dividers
            for div_pattern in divider_patterns:
                if re.match(div_pattern, '\n' + line, re.MULTILINE):
                    section_markers.append({
                        'line': i,
                        'title': f'Section {len(section_markers) + 1}',
                        'type': 'divider'
                    })
                    break
            else:
                # Check for section headers
                for pattern, ptype in patterns:
                    match = re.match(pattern, '\n' + line, re.MULTILINE | re.IGNORECASE)
                    if match:
                        # Extract title
                        if ptype == 'roman':
                            marker = match.group(1).strip()
                            title = match.group(2).strip() if match.group(2) else marker
                            title = f"{marker} {title}".strip() if title != marker else marker
                        elif ptype in ['part', 'chapter']:
                            num = match.group(1)
                            title = match.group(2).strip() if match.group(2) else f"{ptype.title()} {num}"
                        elif ptype == 'numbered':
                            num = match.group(1)
                            title = match.group(2).strip() if match.group(2) else f"Section {num}"
                        elif ptype == 'markdown':
                            title = match.group(2).strip()
                        else:
                            title = f"Section {len(section_markers) + 1}"
                        
                        section_markers.append({
                            'line': i,
                            'title': title,
                            'type': ptype
                        })
                        break
        
        # If no sections found, return the whole script as one section
        if not section_markers:
            print("[ANALYZER] No section markers detected - treating as single section")
            return [{
                'number': 1,
                'title': 'Full Script',
                'text': script_text.strip(),
                'start_line': 0,
                'word_count': len(script_text.split())
            }]
        
        # Build sections from markers
        for i, marker in enumerate(section_markers):
            start_line = marker['line']
            
            # End at next marker or end of script
            if i + 1 < len(section_markers):
                end_line = section_markers[i + 1]['line']
            else:
                end_line = len(lines)
            
            # Extract section text (skip the header line for dividers/headers)
            if marker['type'] in ['divider']:
                section_lines = lines[start_line + 1:end_line]
            else:
                # Include header line but also get content after it
                section_lines = lines[start_line:end_line]
            
            section_text = '\n'.join(section_lines).strip()
            
            # Skip empty sections
            if not section_text or len(section_text.split()) < 10:
                continue
            
            sections.append({
                'number': len(sections) + 1,
                'title': marker['title'],
                'text': section_text,
                'start_line': start_line,
                'word_count': len(section_text.split())
            })
        
        # Handle content before first marker (if any)
        if section_markers and section_markers[0]['line'] > 0:
            intro_text = '\n'.join(lines[:section_markers[0]['line']]).strip()
            if intro_text and len(intro_text.split()) >= 10:
                # Insert at beginning
                sections.insert(0, {
                    'number': 0,  # Will be renumbered
                    'title': 'Introduction',
                    'text': intro_text,
                    'start_line': 0,
                    'word_count': len(intro_text.split())
                })
        
        # Renumber sections
        for i, section in enumerate(sections):
            section['number'] = i + 1
        
        print(f"[ANALYZER] Detected {len(sections)} section(s):")
        for section in sections:
            print(f"[ANALYZER]   Section {section['number']}: '{section['title']}' ({section['word_count']} words)")
        
        return sections

    def strip_section_markers(self, script_text):
        """
        Remove section header/divider lines from the script so they won't be spoken.
        This lets you denote parts without the voiceover reading them.
        """
        # Section header patterns (ordered by priority)
        patterns = [
            (r'^\s*((?:I{1,3}|IV|V|VI{0,3}|IX|X{0,3})(?:\.|:|\s*[-–—]))\s*(.*)$', 'roman'),
            (r'^\s*(?:PART|Part)\s+(\d+|[IVXivx]+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)[\s:.\-–—]*(.*)$', 'part'),
            (r'^\s*(?:CHAPTER|Chapter)\s+(\d+|[IVXivx]+)[\s:.\-–—]*(.*)$', 'chapter'),
            (r'^\s*(\d+)[\.\)]\s+([A-Z][^\n]{0,60})$', 'numbered'),
            (r'^\s*(#{1,3})\s+(.+)$', 'markdown'),
        ]

        divider_patterns = [
            r'^\s*[-]{3,}\s*$',
            r'^\s*[=]{3,}\s*$',
            r'^\s*[*]{3,}\s*$',
            r'^\s*[_]{3,}\s*$',
        ]

        cleaned_lines = []
        for line in script_text.split('\n'):
            line_stripped = line.strip()
            if not line_stripped:
                cleaned_lines.append(line)
                continue

            # Skip divider lines
            if any(re.match(pat, line_stripped) for pat in divider_patterns):
                continue

            # Skip section header lines
            is_header = False
            for pattern, _ptype in patterns:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    is_header = True
                    break

            if not is_header:
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines).strip()
    
    def analyze_script(self, script_text):
        """
        Main analysis function that extracts all necessary information
        
        Args:
            script_text: The video script to analyze
        
        Returns:
            Dictionary with keys: keywords, claims, statistics, segments
        """
        print("[ANALYZER] Starting script analysis...")
        
        # Calculate dynamic thresholds based on script length
        word_count = len(script_text.split())
        
        # Scale keywords moderately: roughly 1 keyword per 8-10 words for balanced visual coverage
        # Reduced density to avoid icon spam (35% reduction from aggressive settings)
        min_keywords = max(15, word_count // 9)  # Reduced from word_count // 6
        max_keywords = max(25, word_count // 5)  # Reduced from word_count // 3
        
        # Scale segments: roughly 1 segment per 50-100 words
        min_segments = max(2, word_count // 100)
        max_segments = max(3, word_count // 40)
        
        print(f"[ANALYZER] Script length: {word_count} words")
        print(f"[ANALYZER] Target keywords: {min_keywords}-{max_keywords}")
        print(f"[ANALYZER] Target segments: {min_segments}-{max_segments}")
        
        # Create comprehensive prompt for Claude
        system_prompt = """You are an expert video production assistant. Analyze scripts for YouTube documentary-style videos about games.
Your job is to extract structured information that will be used to automatically create visuals, find supporting evidence, and generate graphs."""
        
        user_prompt = f"""Analyze this video script and extract the following information in JSON format:

SCRIPT:
{script_text}

Please provide a JSON object with this exact structure:
{{
    "keywords": [
        {{"word": "December 2024", "timestamp_hint": "early", "importance": 7, "display_type": "text", "sentence": "In December 2024, Brawl Stars was on top of the world."}},
        {{"word": "Brawl Stars", "timestamp_hint": "early", "importance": 10, "display_type": "icon", "sentence": "In December 2024, Brawl Stars was on top of the world."}},
        {{"word": "84 million", "timestamp_hint": "early", "importance": 8, "display_type": "text", "sentence": "It hit a record 84 million monthly players, fueled by the massive Toy Story collaboration."}},
        {{"word": "Toy Story", "timestamp_hint": "early", "importance": 9, "display_type": "icon", "sentence": "It hit a record 84 million monthly players, fueled by the massive Toy Story collaboration."}},
        {{"word": "Buzz Lightyear", "timestamp_hint": "late", "importance": 9, "display_type": "icon", "sentence": "And the cause of that high—the Buzz Lightyear brawler—was the very thing that started the rot."}}
    ],
    "claims": [
        {{"claim": "statement that needs evidence", "confidence": "high/medium/low", "reddit_search_terms": ["term1", "term2"]}},
        {{"claim": "another statement", "confidence": "high/medium/low", "reddit_search_terms": ["term1"]}}
    ],
    "statistics": [
        {{"stat_text": "60% win rate", "value": 60, "metric": "win rate", "visualization_type": "bar/line/pie", "context": "Edgar"}},
        {{"stat_text": "another stat", "value": 123, "metric": "metric name", "visualization_type": "bar/line/pie", "context": "comparison label"}}
    ],
    "segments": [
        {{"segment_number": 1, "text": "opening hook text", "type": "hook", "duration_estimate": 5}},
        {{"segment_number": 2, "text": "main content", "type": "data", "duration_estimate": 10}},
        {{"segment_number": 3, "text": "supporting evidence", "type": "evidence", "duration_estimate": 8}}
    ],
    "overall_mood": "energetic/calm/serious/humorous",
    "main_subject": "name of the main topic/character/game"
}}

GUIDELINES:
- Keywords: Extract {min_keywords}-{max_keywords} visual concepts **that ACTUALLY APPEAR in the script** (we want good icon coverage!)
  - **CRITICAL RULE #1 - KEEP FULL NAMES/TERMS TOGETHER**: 
    * Multi-word names MUST be kept as ONE keyword, not split
    * "Buzz Lightyear" → CORRECT: "Buzz Lightyear", WRONG: "Buzz" 
    * "Toy Story" → CORRECT: "Toy Story", WRONG: "Toy"
    * "Clash Royale" → CORRECT: "Clash Royale", WRONG: "Clash" or "Royale"
    * "Clash of Clans" → CORRECT: "Clash of Clans", WRONG: "Clash" or "Clans"
    * "Brawl Stars" → CORRECT: "Brawl Stars", WRONG: "Brawl" or "Stars"
    * "Elite Wild Cards" → CORRECT: "Elite Wild Cards", WRONG: "Elite" or "Cards" or "Wild"
    * "Pass Royale" → CORRECT: "Pass Royale", WRONG: "Pass"
    * Streamer names: "Jynxzi", "KairosTime", "xQc" - keep exact usernames
    * This is EXTREMELY important - splitting names/terms ruins icon search
  - **CRITICAL RULE #2**: Only extract words/phrases that are EXPLICITLY mentioned in the script text
  - **CRITICAL RULE #3 - Display Type (icon vs text)**:
    * **ALWAYS use "text"** for:
      - **Dates & Times**: "December 2024", "2024", "5 years ago", "three months"
      - **Numbers & Quantities**: "84 million", "$77 million", "1.2 billion"
      - **Percentages & Stats**: "60%", "45% win rate", "2x growth"
      - **Ordinal numbers**: "first", "second", "#1 ranked"
      - **Time periods**: "5 years", "3 months", "two weeks"
      - **Any number/date combination**: "December 2024", "Q4 2023"
    * **Use "icon"** for everything else:
      - **Game/Brand names**: "Brawl Stars", "Clash Royale", "Toy Story"
      - **Character names**: "Buzz Lightyear", "Edgar", "Mortis"
      - **Concepts**: "record", "peak", "decline", "rot", "resurrection"
      - **Actions**: "dominate", "explode", "collapse"
      - **Objects**: "trophy", "collaboration", "update"
      - **Emotions**: "furious", "excited", "frustrated"
    * **Rule of thumb**: If it's a number, date, or stat → TEXT. Everything else → ICON.
  - **CRITICAL RULE #4 - QUESTIONS NEED ICONS TOO**:
    * When the script asks a question (sentences ending with "?" or rhetorical questions), extract an icon!
    * For direct questions: Extract a "question" icon AND the subject of the question
    * Examples:
      - "Is Edgar broken?" → Extract {{"word": "question", "display_type": "icon", "importance": 8}} AND {{"word": "Edgar", "display_type": "icon"}}
      - "Why is this happening?" → Extract {{"word": "why", "display_type": "icon", "importance": 7}}
      - "What went wrong?" → Extract {{"word": "problem", "display_type": "icon", "importance": 7}}
      - "How did they mess this up?" → Extract {{"word": "confusion", "display_type": "icon", "importance": 7}}
      - "Will Edgar get nerfed?" → Extract {{"word": "nerf", "display_type": "icon", "importance": 8}}
    * Question words that should become icons: "question", "why", "mystery", "problem", "confusion", "doubt"
    * This ensures visual interest during rhetorical moments in the script!
  - **INCLUDE THE FULL SENTENCE**: For each keyword, include the complete sentence where it appears (this helps generate better visuals)
  - Focus on ACTION words (trickshotting, dominating, resurrect) or IMPACT words (decline, buff, nerf, crisis)
  - Include key CHARACTER/GAME names when they're important to the story (Clash Royale, Brawl Stars, Edgar)
    * Keep multi-word names together: "Buzz Lightyear" (not just "Buzz"), "Toy Story" (not just "Toy"), "Clash Royale" (not just "Clash")
  - Include EMOTION/MOOD words (furious, bleeding, flourish, loyal)
  - Include ABSTRACT CONCEPTS that can be visualized (paradox, monetization, confidence, death, record, peak)
  - Include TEMPORAL markers if emphasized (December, 2024, 5 years)
  - AVOID: filler words, articles, generic verbs (is, has, being), words not in the script, splitting multi-word names
  - Example: "In December 2024" -> {{"word": "December 2024", "display_type": "text", "sentence": "In December 2024, Brawl Stars was on top.", "importance": 7}}
  - Example: "hit 84 million players" -> {{"word": "84 million", "display_type": "text", "sentence": "It hit a record 84 million monthly players.", "importance": 8}}
  - Example: "60% win rate" -> {{"word": "60%", "display_type": "text", "sentence": "Edgar has a 60% win rate.", "importance": 8}}
  - Example: "Brawl Stars was on top" -> {{"word": "Brawl Stars", "display_type": "icon", "sentence": "Brawl Stars was on top of the world.", "importance": 10}}
  - Example: "hit a record" -> {{"word": "record", "display_type": "icon", "sentence": "It hit a record 84 million players.", "importance": 8}}
  - Example: "Buzz Lightyear brawler" -> {{"word": "Buzz Lightyear", "display_type": "icon", "sentence": "The Buzz Lightyear brawler caused problems.", "importance": 9}}
  - Example: "Is Edgar broken?" -> {{"word": "question", "display_type": "icon", "sentence": "Is Edgar completely broken right now?", "importance": 8}}
  - Example: "Why did this happen?" -> {{"word": "why", "display_type": "icon", "sentence": "Why did this happen?", "importance": 7}}
  - **timestamp_hint**: Indicate where in the script this word appears (early=first 1/3, middle=middle 1/3, late=last 1/3)
  - **sentence**: The COMPLETE sentence (or two sentences if context is needed) containing this keyword
- For gaming content: include game names, characters, mechanics, abilities, emotions
- **BE EXTREMELY GENEROUS with keywords!** Icons are what make the video engaging!
- **EXTRACT {min_keywords}-{max_keywords} KEYWORDS** - This is NOT optional. Extract the FULL range!
- If you're unsure about a word, INCLUDE IT. More keywords = better video!
- Extract EVERY significant noun, proper noun, action word, and concept
- Extract ALL game names, character names, feature names (even if mentioned multiple times)
- Extract ALL emotion/mood words (catastrophic, nightmare, disillusioned, frustrated, etc.)
- Extract ALL temporal markers and events (December 2024, February 2025, etc.)
- Extract ALL abstract concepts (peak, decline, rot, crash, domino, death, chore, etc.)
- Extract ALL important numbers and stats (84 million, 73 million, 3000 coins, 450 points, etc.)
- Claims are statements that would benefit from Reddit posts or other evidence
- **Statistics - STRICT RULES** (graphs need multiple data points):
  - **ONLY extract if script contains 2+ comparable numbers for the SAME metric**
  - **DO NOT extract standalone/isolated numbers** - they can't be graphed meaningfully
  
  **EXTRACT these (multiple data points):**
  ✅ **Comparisons**: "Edgar has 60% win rate, Mortis has 45%, Fang has 52%"
  ✅ **Trends over time**: "In 2020 it was 50M players, 2022 had 65M, 2024 hit 84M"
     * Also: "grew from 50M in 2020 to 84M in 2024" (extract all mentioned points)
     * Also: "84M in 2024—up from 65M in 2022 and 50M in 2020" (extract 2020: 50M, 2022: 65M, 2024: 84M)
  ✅ **Rankings**: "Clash Royale made $77M, Brawl Stars made $35M, CoC made $30M"
  ✅ **Before/After**: "went from 50M to 84M", "increased from 45% to 60%"
  
  **DO NOT EXTRACT these (single data points):**
  ❌ "It hit a record 84 million players" (just one number, no comparison)
  ❌ "The game costs $4.99" (no comparison)
  ❌ "He has 60% win rate" (if no other characters mentioned)
  
  **Examples of VALID extraction:**
  - "84 million in 2024—up from 65 million in 2022 and 50 million in 2020" →
    Extract: [
      {{"stat_text": "Players in 2020", "value": 50, "metric": "monthly_players_millions", "context": "2020"}},
      {{"stat_text": "Players in 2022", "value": 65, "metric": "monthly_players_millions", "context": "2022"}},
      {{"stat_text": "Players in 2024", "value": 84, "metric": "monthly_players_millions", "context": "2024"}}
    ]
  - "Clash Royale made $77M, more than Brawl Stars and CoC combined" →
    Extract: [
      {{"stat_text": "Clash Royale revenue", "value": 77, "metric": "revenue_millions", "context": "Clash Royale"}},
      {{"stat_text": "Brawl Stars revenue (estimated)", "value": 35, "metric": "revenue_millions", "context": "Brawl Stars"}},
      {{"stat_text": "CoC revenue (estimated)", "value": 30, "metric": "revenue_millions", "context": "Clash of Clans"}}
    ]
  - "Edgar has 60% win rate, Mortis has 45%" →
    Extract: [
      {{"stat_text": "Edgar win rate", "value": 60, "metric": "win_rate_percent", "context": "Edgar"}},
      {{"stat_text": "Mortis win rate", "value": 45, "metric": "win_rate_percent", "context": "Mortis"}}
    ]
  
  - **KEY RULE**: If you can't make a bar chart or line graph with 2+ bars/points, DON'T EXTRACT
  - Use reasonable estimates for comparative values if exact numbers aren't given but comparison is implied
- Segments should break the script into logical parts (aim for {min_segments}-{max_segments} segments based on script length)
- Segment types: "hook" (opening), "data" (statistics), "evidence" (claims/reddit), "gameplay" (general narration)
- Duration estimates should be in seconds based on how long it would take to speak that text

Return ONLY the JSON object, no additional text."""

        # Get analysis from Claude
        print(f"[ANALYZER] Sending {len(script_text)} characters to Claude for analysis...")
        print(f"[ANALYZER] This may take 30-60 seconds for long scripts...")
        analysis = self.claude.ask_json(user_prompt, system_prompt)
        
        if not analysis:
            print("[WARNING] Claude analysis failed, returning empty structure")
            print("[WARNING] Check the error above for details")
            return self._empty_analysis()
        
        # Validate and enrich the analysis
        analysis = self._validate_analysis(analysis, script_text)
        
        print(f"[ANALYZER] Found {len(analysis.get('keywords', []))} keywords")
        print(f"[ANALYZER] Found {len(analysis.get('claims', []))} claims")
        print(f"[ANALYZER] Found {len(analysis.get('statistics', []))} statistics")
        print(f"[ANALYZER] Created {len(analysis.get('segments', []))} segments")
        
        return analysis
    
    def _validate_analysis(self, analysis, script_text):
        """Validate and fill in missing fields"""
        
        # Ensure all required keys exist
        if 'keywords' not in analysis:
            analysis['keywords'] = []
        if 'claims' not in analysis:
            analysis['claims'] = []
        if 'statistics' not in analysis:
            analysis['statistics'] = []
        if 'segments' not in analysis:
            # Fallback: create basic segments
            analysis['segments'] = self._create_basic_segments(script_text)
        if 'overall_mood' not in analysis:
            analysis['overall_mood'] = 'energetic'
        if 'main_subject' not in analysis:
            analysis['main_subject'] = 'Unknown'
        
        # Sort keywords by importance (but DON'T limit them - we want lots of visual elements!)
        if analysis['keywords']:
            analysis['keywords'] = sorted(
                analysis['keywords'],
                key=lambda x: x.get('importance', 0),
                reverse=True
            )
            # Note: No hard limit - let Claude extract as many as needed for good visual coverage
        
        return analysis
    
    def _create_basic_segments(self, script_text):
        """Create basic segments if Claude didn't provide them"""
        from utils.timing_utils import split_script_into_segments, estimate_speech_duration
        
        segments_text = split_script_into_segments(script_text, 3)
        segments = []
        
        for i, text in enumerate(segments_text):
            duration = estimate_speech_duration(text)
            segment_type = 'hook' if i == 0 else ('evidence' if i == len(segments_text) - 1 else 'data')
            
            segments.append({
                'segment_number': i + 1,
                'text': text,
                'type': segment_type,
                'duration_estimate': int(duration)
            })
        
        return segments
    
    def _empty_analysis(self):
        """Return empty but valid analysis structure"""
        return {
            'keywords': [],
            'claims': [],
            'statistics': [],
            'segments': [],
            'overall_mood': 'energetic',
            'main_subject': 'Unknown'
        }
    
    def extract_keywords(self, script_text):
        """Quick extraction of just keywords"""
        analysis = self.analyze_script(script_text)
        return analysis.get('keywords', [])
    
    def detect_claims(self, script_text):
        """Quick extraction of just claims"""
        analysis = self.analyze_script(script_text)
        return analysis.get('claims', [])
    
    def find_statistics(self, script_text):
        """Quick extraction of just statistics"""
        analysis = self.analyze_script(script_text)
        return analysis.get('statistics', [])
    
    def segment_scenes(self, script_text):
        """Quick extraction of just segments"""
        analysis = self.analyze_script(script_text)
        return analysis.get('segments', [])
    
    def save_analysis(self, analysis, filename):
        """Save analysis to file for later use"""
        output_path = f"data/scripts/{filename}_analysis.json"
        os.makedirs("data/scripts", exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        print(f"[ANALYZER] Saved analysis to {output_path}")
        return output_path


if __name__ == "__main__":
    # Test the analyzer
    test_script = """
    Is Edgar completely broken right now? This character has dominated the meta for weeks.
    He has a win rate of over 60 percent in Showdown and it is ruining the game for everyone.
    Players are frustrated because Edgar requires zero skill to use effectively.
    Reddit users are constantly sharing clips of him jumping on enemies with his super.
    The community has been begging for a nerf, but Supercell hasn't responded yet.
    Compare this to characters like Spike who sit at 49% win rate - perfectly balanced.
    Will Edgar finally get the nerf he deserves? Only time will tell.
    """
    
    print("=" * 60)
    print("Testing Script Analyzer")
    print("=" * 60)
    
    analyzer = ScriptAnalyzer()
    analysis = analyzer.analyze_script(test_script)
    
    print("\n" + "=" * 60)
    print("ANALYSIS RESULTS:")
    print("=" * 60)
    print(json.dumps(analysis, indent=2))
    
    # Save for inspection
    analyzer.save_analysis(analysis, "test_script")
