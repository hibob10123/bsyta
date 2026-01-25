import os
import yaml

class Config:
    """Configuration loader and manager"""
    
    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    print(f"[CONFIG] Loaded configuration from {self.config_path}")
                    return config if config else self._default_config()
            except Exception as e:
                print(f"[WARNING] Could not load config: {e}")
                return self._default_config()
        else:
            print(f"[WARNING] Config file not found, using defaults")
            return self._default_config()
    
    def _default_config(self):
        """Return default configuration"""
        return {
            'video': {
                'resolution': [1920, 1080],
                'fps': 30,
                'output_dir': 'data/output'
            },
            'scenes': {
                'gameplay_opacity': 0.4,
                'icon_max_per_scene': 5,
                'reddit_slide_duration': 0.7,
                'graph_hold_time': 3.0
            },
            'sound_effects': {
                'whoosh': 'data/sfx/whoosh.mp3',
                'pop': 'data/sfx/pop.mp3',
                'transition': 'data/sfx/transition.mp3'
            },
            'llm': {
                'model': 'claude-3-5-sonnet-20241022',
                'max_tokens': 4000,
                'temperature': 0.7
            },
            'pipeline': {
                'do_research_assist': False,
                'do_reddit_search': True,
                'do_graph_generation': True,
                'do_asset_gathering': True,
                'reddit_max_posts': 5,
                'reddit_subreddit': 'BrawlStars',
                'words_per_minute': 150
            },
            'paths': {
                'gameplay': 'data/assets/gameplay.mp4',
                'icons_dir': 'data/assets/icons',
                'output_dir': 'data/output',
                'temp_dir': 'data/temp',
                'scripts_dir': 'data/scripts',
                'sfx_dir': 'data/sfx'
            }
        }
    
    def get(self, key_path, default=None):
        """
        Get config value by dot-separated key path
        Example: config.get('video.fps') -> 30
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def ensure_directories(self):
        """Create necessary directories"""
        dirs_to_create = [
            self.get('paths.output_dir', 'data/output'),
            self.get('paths.temp_dir', 'data/temp'),
            self.get('paths.scripts_dir', 'data/scripts'),
            self.get('paths.sfx_dir', 'data/sfx'),
            self.get('paths.icons_dir', 'data/assets/icons')
        ]
        
        for dir_path in dirs_to_create:
            try:
                os.makedirs(dir_path, exist_ok=True)
            except Exception:
                pass  # Directory likely already exists
        
        print("[CONFIG] Ensured all directories exist")


# Global config instance
_config = None

def load_config(config_path="config.yaml"):
    """Load or reload configuration"""
    global _config
    _config = Config(config_path)
    return _config

def get_config():
    """Get current configuration"""
    global _config
    if _config is None:
        _config = Config()
    return _config


if __name__ == "__main__":
    # Test config loader
    print("=" * 60)
    print("Testing Config Loader")
    print("=" * 60)
    
    config = load_config()
    
    print("\nSample config values:")
    print(f"  Video FPS: {config.get('video.fps')}")
    print(f"  LLM Model: {config.get('llm.model')}")
    print(f"  Output Dir: {config.get('paths.output_dir')}")
    print(f"  Reddit Search: {config.get('pipeline.do_reddit_search')}")
    
    print("\nEnsuring directories...")
    config.ensure_directories()
    
    print("\nConfig loaded successfully!")
