import os
import json
import requests
import random
from typing import Dict, List, Optional, Union, Tuple
from dataclasses import dataclass

@dataclass
class MemeResult:
    """Class to represent a meme search result"""
    title: str
    source: str
    content_type: str  # 'text', 'image', or 'gif'
    content: str  # Text content or URL to image/gif
    tags: List[str]

class MemeSearcher:
    """
    Class to search for and retrieve memes related to conversation topics.
    Supports text memes, static images (jpg/png) and animated gifs.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with optional API key for external meme services"""
        self.api_key = api_key
        self.local_meme_db = self._load_local_memes()
        
        # Example popular meme topics related to Demon Slayer/anime for fallback
        self.popular_topics = [
            "nezuko", "tanjiro", "demon slayer", "anime", "water breathing",
            "zenitsu", "inosuke", "muzan", "hashira", "breathing technique",
            "sword", "crying", "shocked"
        ]
    
    def _load_local_memes(self) -> Dict[str, List[MemeResult]]:
        """Load local meme database from file or create default one if none exists"""
        try:
            if os.path.exists("meme_database.json"):
                with open("meme_database.json", "r") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading local meme database: {e}")
        
        # Create a default database with some common Demon Slayer memes
        default_db = {
            "tanjiro": [
                MemeResult(
                    title="Confused Tanjiro",
                    source="Demon Slayer anime",
                    content_type="image",
                    content="https://i.imgur.com/8jcAyUd.jpg",
                    tags=["tanjiro", "confused", "reaction"]
                ),
                MemeResult(
                    title="Kind Tanjiro",
                    source="Demon Slayer anime",
                    content_type="text",
                    content="When Tanjiro says something really wholesome and the villain starts questioning their life choices",
                    tags=["tanjiro", "kindness", "quote"]
                )
            ],
            "nezuko": [
                MemeResult(
                    title="Nezuko Running",
                    source="Demon Slayer anime",
                    content_type="gif",
                    content="https://c.tenor.com/aNGz6XLt5hEAAAAd/demon-slayer-nezuko.gif",
                    tags=["nezuko", "running", "cute"]
                ),
                MemeResult(
                    title="Smol Nezuko",
                    source="Demon Slayer anime",
                    content_type="image",
                    content="https://i.pinimg.com/originals/6f/da/33/6fda33eccac383df0e9e49bad6a10e6b.jpg",
                    tags=["nezuko", "cute", "small"]
                )
            ],
            "demon slayer": [
                MemeResult(
                    title="Breathing Techniques",
                    source="Demon Slayer anime",
                    content_type="text",
                    content="Me after learning water breathing techniques watching Demon Slayer: *Drinks water aggressively*",
                    tags=["breathing", "water", "funny"]
                ),
                MemeResult(
                    title="Zenitsu Sleeping vs Awake",
                    source="Demon Slayer anime",
                    content_type="image",
                    content="https://pbs.twimg.com/media/EAA4WfPUcAAeN7r.jpg",
                    tags=["zenitsu", "sleeping", "thunder breathing"]
                )
            ],
            "anime": [
                MemeResult(
                    title="Anime Logic",
                    source="Various anime",
                    content_type="text",
                    content="Anime logic: The more tragic your backstory, the more powerful you become",
                    tags=["anime", "logic", "backstory"]
                ),
                MemeResult(
                    title="Anime Protagonist Hair",
                    source="Various anime",
                    content_type="image",
                    content="https://i.pinimg.com/originals/b3/b3/0b/b3b30bce0ecd3f3cbfb2ad43a7ecb55f.jpg",
                    tags=["anime", "hair", "protagonist"]
                )
            ]
        }
        return default_db
    
    def search_memes(self, topic: str, limit: int = 1) -> List[MemeResult]:
        """
        Search for memes related to the given topic
        
        Args:
            topic: Topic to search for
            limit: Maximum number of memes to return
            
        Returns:
            List of MemeResult objects
        """
        # Try to search online first if API key exists (for a real implementation)
        # online_results = self._search_online(topic, limit) if self.api_key else []
        
        # For now, just use our local database
        topic = topic.lower()
        results = []
        
        # Direct match
        if topic in self.local_meme_db:
            results.extend(self.local_meme_db[topic])
        
        # Partial matches
        for key, memes in self.local_meme_db.items():
            if topic in key and key != topic:  # Avoid duplicates from direct match
                results.extend(memes)
            else:
                # Check tags
                for meme in memes:
                    if any(topic in tag for tag in meme.tags):
                        results.append(meme)
        
        # If no results, try with a random popular topic
        if not results and self.popular_topics:
            random_topic = random.choice(self.popular_topics)
            if random_topic in self.local_meme_db:
                results.extend(self.local_meme_db[random_topic])
        
        # Shuffle and limit results
        random.shuffle(results)
        return results[:limit]
    
    def format_meme_for_display(self, meme: MemeResult) -> Tuple[str, Optional[str]]:
        """
        Format a meme for display in the chat interface
        
        Returns:
            Tuple of (text_content, image_url) - either can be None
        """
        if meme.content_type == "text":
            return f"📝 **{meme.title}**: {meme.content}", None
        
        text = f"🖼️ **{meme.title}**"
        image_url = meme.content
        
        return text, image_url
    
    def get_related_meme(self, topic: str) -> Tuple[str, Optional[str]]:
        """
        Get a meme related to the given topic, formatted for display
        
        Returns:
            Tuple of (text_content, image_url) - either can be None
        """
        memes = self.search_memes(topic, limit=1)
        if not memes:
            return f"I couldn't find any memes related to '{topic}'", None
        
        return self.format_meme_for_display(memes[0]) 