import os
import json
import requests
import random
import re
from typing import Dict, List, Optional, Union, Tuple
from dataclasses import dataclass

@dataclass
class Meme:
    """Class to represent a meme search result"""
    title: str
    source: str
    content_type: str  # 'text', 'image', or 'gif'
    url: str  # URL to image/gif or text content
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

# For backward compatibility
MemeResult = Meme

class MemeSearcher:
    """
    Class to search for and retrieve memes related to conversation topics.
    Supports text memes, static images (jpg/png) and animated gifs.
    Uses online APIs with fallback to local database.
    """
    
    def __init__(self, api_key: Optional[str] = None, meme_db_path: str = "meme_database.json"):
        """Initialize with optional API key for external meme services"""
        self.api_key = api_key
        self.meme_db_path = meme_db_path
        self.local_meme_db = self._load_local_memes()
        
        # Example popular meme topics related to Demon Slayer/anime for fallback
        self.popular_topics = [
            "nezuko", "tanjiro", "demon slayer", "anime", "water breathing",
            "zenitsu", "inosuke", "muzan", "hashira", "breathing technique",
            "sword", "crying", "shocked"
        ]
        
        # URLs for online APIs
        self.tenor_api_url = "https://tenor.googleapis.com/v2/search"
        self.imgur_api_url = "https://api.imgur.com/3/gallery/search"
        self.reddit_api_url = "https://www.reddit.com/r/animemes/search.json"
    
    def _load_local_memes(self) -> Dict[str, List[Meme]]:
        """Load local meme database from file or create empty one if none exists"""
        try:
            if os.path.exists(self.meme_db_path):
                with open(self.meme_db_path, "r") as f:
                    data = json.load(f)
                    # Convert the loaded JSON data to Meme objects
                    meme_db = {}
                    for topic, memes in data.items():
                        meme_db[topic] = [
                            Meme(
                                title=meme["title"],
                                source=meme["source"],
                                content_type=meme["content_type"],
                                url=meme["url"],
                                tags=meme["tags"]
                            ) for meme in memes
                        ]
                    print(f"Loaded {sum(len(memes) for memes in meme_db.values())} memes from {self.meme_db_path}")
                    return meme_db
        except Exception as e:
            print(f"Error loading local meme database: {e}")
        
        # Create an empty database file if none exists
        empty_db = {}
        
        # Save the empty database to file
        try:
            with open(self.meme_db_path, "w") as f:
                json.dump(empty_db, f, indent=4)
            print(f"Created empty meme database at {self.meme_db_path}")
        except Exception as e:
            print(f"Error creating empty meme database: {e}")
        
        return empty_db
    
    def add_meme(self, topic: str, meme: Meme) -> bool:
        """
        Add a new meme to the database
        
        Args:
            topic: The topic to add the meme under
            meme: The Meme object to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Add to in-memory database
            if topic.lower() not in self.local_meme_db:
                self.local_meme_db[topic.lower()] = []
            
            self.local_meme_db[topic.lower()].append(meme)
            
            # Save to file
            self._save_meme_db()
            return True
        except Exception as e:
            print(f"Error adding meme: {e}")
            return False
    
    def _save_meme_db(self) -> bool:
        """Save the current meme database to file"""
        try:
            # Convert the Meme objects to dictionaries
            serializable_db = {}
            for topic, memes in self.local_meme_db.items():
                serializable_db[topic] = [
                    {
                        "title": meme.title,
                        "source": meme.source,
                        "content_type": meme.content_type,
                        "url": meme.url,
                        "tags": meme.tags
                    } for meme in memes
                ]
            
            with open(self.meme_db_path, "w") as f:
                json.dump(serializable_db, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving meme database: {e}")
            return False
    
    def _search_tenor(self, query: str, limit: int = 5) -> List[Meme]:
        """Search Tenor API for anime GIFs"""
        results = []
        
        # Set a safe default tenor API key for demo purposes
        tenor_api_key = "AIzaSyBgpyCZVnRDPGAFZPM-UkZYRpZ8MCUgXrA"  # Replace with a real API key in production
        
        # If we have our own API key, use it
        if self.api_key:
            tenor_api_key = self.api_key
            
        # Make sure to include anime-specific terms in the search to get relevant results
        anime_query = f"{query} anime"
        
        try:
            params = {
                "q": anime_query,
                "key": tenor_api_key,
                "client_key": "tanjiro_bot",
                "limit": limit,
                "media_filter": "gif,tinygif",
                "contentfilter": "medium"
            }
            
            print(f"Searching Tenor for: {anime_query}")
            response = requests.get(self.tenor_api_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if "results" in data:
                    for item in data["results"]:
                        # Extract the media URL
                        if "media_formats" in item and "gif" in item["media_formats"]:
                            gif_url = item["media_formats"]["gif"]["url"]
                            title = item.get("title", "Anime GIF")
                            content_tags = [tag.lower() for tag in item.get("tags", [])] if "tags" in item else []
                            
                            results.append(Meme(
                                title=title,
                                source="Tenor",
                                content_type="gif",
                                url=gif_url,
                                tags=content_tags if content_tags else [query]
                            ))
            else:
                print(f"Tenor API error: {response.status_code} - {response.text}")
            
            return results
        except Exception as e:
            print(f"Error searching Tenor: {e}")
            return []
    
    def _search_giphy(self, query: str, limit: int = 5) -> List[Meme]:
        """Search Giphy API for GIFs"""
        results = []
        
        # Use public beta key for demo purposes
        giphy_api_key = "dc6zaTOxFJmzC"  # This is Giphy's public beta key
        giphy_api_url = "https://api.giphy.com/v1/gifs/search"
        
        try:
            params = {
                "api_key": giphy_api_key,
                "q": f"{query} anime",
                "limit": limit,
                "rating": "pg-13"
            }
            
            print(f"Searching Giphy for: {query} anime")
            response = requests.get(giphy_api_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data:
                    for item in data["data"]:
                        if "images" in item and "original" in item["images"]:
                            gif_url = item["images"]["original"]["url"]
                            title = item.get("title", "Anime GIF")
                            
                            results.append(Meme(
                                title=title,
                                source="Giphy",
                                content_type="gif",
                                url=gif_url,
                                tags=[tag.strip() for tag in query.split()]
                            ))
            else:
                print(f"Giphy API error: {response.status_code} - {response.text}")
            
            return results
        except Exception as e:
            print(f"Error searching Giphy: {e}")
            return []
    
    def _search_reddit(self, query: str, limit: int = 5) -> List[Meme]:
        """Search Reddit for anime memes"""
        results = []
        
        # Use multiple subreddits for better results
        subreddits = ["animemes", "anime_irl", "animememes", "goodanimemes", "KimetsuNoYaiba"]
        search_limit = max(10, limit * 3)  # Get more than we need to filter out bad results
        
        try:
            for subreddit in subreddits:
                # If we already have enough results, stop searching additional subreddits
                if len(results) >= limit:
                    break
                
                reddit_url = f"https://www.reddit.com/r/{subreddit}/search.json"
                
                params = {
                    "q": query,
                    "sort": "relevance",
                    "t": "all",
                    "limit": search_limit,
                    "restrict_sr": "on"
                }
                
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                
                print(f"Searching Reddit r/{subreddit} for: {query}")
                try:
                    response = requests.get(reddit_url, params=params, headers=headers, timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if "data" in data and "children" in data["data"]:
                            for post in data["data"]["children"]:
                                if len(results) >= limit:
                                    break
                                
                                post_data = post["data"]
                                
                                # Skip posts without media or that are self-posts
                                if post_data.get("is_self", True):
                                    continue
                                
                                # Get the image URL
                                image_url = None
                                content_type = "unknown"
                                
                                # Check different possible image sources
                                if "url" in post_data:
                                    url = post_data["url"]
                                    if url.endswith(('.jpg', '.jpeg', '.png')):
                                        image_url = url
                                        content_type = "image"
                                    elif url.endswith('.gif'):
                                        image_url = url
                                        content_type = "gif"
                                
                                # Try the preview images if direct URL didn't work
                                if not image_url and "preview" in post_data:
                                    try:
                                        if "images" in post_data["preview"] and len(post_data["preview"]["images"]) > 0:
                                            image_info = post_data["preview"]["images"][0]
                                            
                                            # Check if it's a GIF
                                            if "variants" in image_info and "gif" in image_info["variants"]:
                                                image_url = image_info["variants"]["gif"]["source"]["url"]
                                                content_type = "gif"
                                            # Otherwise use the standard image
                                            else:
                                                image_url = image_info["source"]["url"]
                                                content_type = "image"
                                            
                                            # Reddit URLs are HTML encoded
                                            image_url = image_url.replace("&amp;", "&")
                                    except Exception as e:
                                        print(f"Error processing Reddit preview: {e}")
                                        continue
                                
                                # Skip if we couldn't find an image URL
                                if not image_url:
                                    continue
                                
                                # Create a Meme object and add it to results
                                meme = Meme(
                                    title=post_data.get("title", "Untitled Meme"),
                                    source=f"Reddit r/{subreddit}",
                                    content_type=content_type,
                                    url=image_url,
                                    tags=[]
                                )
                                results.append(meme)
                                
                                # Stop once we have enough results
                                if len(results) >= limit:
                                    break
                    else:
                        print(f"Reddit API error for r/{subreddit}: {response.status_code}")
                except Exception as e:
                    print(f"Error searching r/{subreddit}: {e}")
                    continue
                
            return results[:limit]
        except Exception as e:
            print(f"Error in Reddit search: {e}")
            return []
    
    def _search_online(self, query: str, limit: int = 5) -> List[Meme]:
        """Search for memes online using various APIs and direct scraping"""
        results = []
        
        # Since we're having API key issues with Tenor and Giphy, focus on Reddit which works
        reddit_results = self._search_reddit(query, limit=limit)
        results.extend(reddit_results)
        print(f"Got {len(reddit_results)} results from Reddit")
        
        # If we didn't get enough results, try with alternative keywords
        if len(results) < limit:
            # Try searching with "meme" added to the query
            alt_query = f"{query} meme"
            more_reddit = self._search_reddit(alt_query, limit=limit-len(results))
            
            # Only add new results that aren't duplicates
            for meme in more_reddit:
                if not any(r.url == meme.url for r in results):
                    results.append(meme)
                
            print(f"Got {len(results) - len(reddit_results)} additional results with '{alt_query}'")
        
        # Add anime-specific search as another attempt
        if len(results) < limit:
            anime_query = f"anime {query}"
            more_anime = self._search_reddit(anime_query, limit=limit-len(results))
            
            # Only add new results that aren't duplicates
            for meme in more_anime:
                if not any(r.url == meme.url for r in results):
                    results.append(meme)
                
            print(f"Got {len(results) - len(reddit_results)} total additional results")
        
        print(f"Total meme results: {len(results)}")
        return results
    
    def _extract_hashtags(self, query: str) -> Tuple[str, List[str]]:
        """
        Extract hashtags from a query and return both the cleaned query and hashtags
        
        Args:
            query: The search query possibly containing hashtags
            
        Returns:
            Tuple of (cleaned_query, hashtags)
        """
        # Find all hashtags (word starting with # followed by word characters)
        hashtag_pattern = r'#(\w+)'
        hashtags = re.findall(hashtag_pattern, query)
        
        # Remove hashtags from the query
        cleaned_query = re.sub(hashtag_pattern, '', query).strip()
        
        # If we have no remaining text but have hashtags, use the first hashtag as query
        if not cleaned_query and hashtags:
            cleaned_query = hashtags[0]
        
        return cleaned_query, hashtags

    def search_memes(self, topic: str, limit: int = 5) -> List[Meme]:
        """
        Search for memes related to the given topic using online sources
        Supports hashtag-based searches like "#tanjiro #meme"
        
        Args:
            topic: Topic to search for (can include hashtags)
            limit: Maximum number of memes to return
            
        Returns:
            List of Meme objects
        """
        # Clean up the topic text and make sure we have something to search for
        if not topic or topic.strip() == "":
            return []
        
        # Extract hashtags if present
        main_query, hashtags = self._extract_hashtags(topic.lower().strip())
        
        print(f"Search query: '{main_query}', Hashtags: {hashtags}")
        
        # If we found hashtags, use them to enhance the search
        search_strategies = []
        
        # Start with the main query
        if main_query:
            search_strategies.append(main_query)
        
        # Add combinations with hashtags
        if hashtags:
            # Use individual hashtags
            search_strategies.extend(hashtags)
            
            # Combine main query with each hashtag
            if main_query:
                for tag in hashtags:
                    search_strategies.append(f"{main_query} {tag}")
            
            # Special case: if we have anime or character specific hashtags
            anime_tags = [tag for tag in hashtags if tag in ['anime', 'demonslayer', 'kimetsunoyaiba']]
            character_tags = [tag for tag in hashtags if tag in ['tanjiro', 'nezuko', 'zenitsu', 'inosuke']]
            
            if anime_tags and character_tags:
                for a_tag in anime_tags:
                    for c_tag in character_tags:
                        search_strategies.append(f"{a_tag} {c_tag}")
        
        # If we don't have any search strategies, just use the original topic
        if not search_strategies:
            search_strategies.append(self._clean_search_query(topic))
        
        # Try different search strategies until we get results
        results = []
        for query in search_strategies:
            print(f"Trying search strategy: '{query}'")
            try:
                strategy_results = self._search_online(query, limit=limit)
                if strategy_results:
                    results.extend(strategy_results)
                    # If we got enough results, stop trying more strategies
                    if len(results) >= limit:
                        break
            except Exception as e:
                print(f"Error in search strategy '{query}': {e}")
        
        # Remove duplicates
        unique_results = []
        seen = set()
        for meme in results:
            meme_id = (meme.title, meme.url)
            if meme_id not in seen:
                seen.add(meme_id)
                
                # Add hashtags as tags to the meme for better context
                if hashtags and meme.tags:
                    for tag in hashtags:
                        if tag not in meme.tags:
                            meme.tags.append(tag)
                
                unique_results.append(meme)
        
        # If we still have nothing, try generic searches
        if not unique_results:
            print("No results found with specific strategies, trying generic searches")
            try:
                # Try with "meme" added if not already in queries
                if not any("meme" in s for s in search_strategies):
                    meme_results = self._search_online(f"{main_query} meme", limit=limit)
                    for meme in meme_results:
                        meme_id = (meme.title, meme.url)
                        if meme_id not in seen:
                            seen.add(meme_id)
                            unique_results.append(meme)
                
                # For Demon Slayer specific searches that failed, try with generic terms
                if (not unique_results and 
                    (main_query in ['tanjiro', 'nezuko', 'zenitsu', 'inosuke'] or 
                     any(tag in ['tanjiro', 'nezuko', 'zenitsu', 'inosuke', 'demonslayer'] for tag in hashtags))):
                    demon_slayer_results = self._search_online("demon slayer anime", limit=limit)
                    for meme in demon_slayer_results:
                        meme_id = (meme.title, meme.url)
                        if meme_id not in seen:
                            seen.add(meme_id)
                            unique_results.append(meme)
            except Exception as e:
                print(f"Error in generic search: {e}")
        
        # If we still have nothing, return empty list
        if not unique_results:
            print("No meme results found after all attempts")
            return []
        
        # Randomize order to provide variety
        random.shuffle(unique_results)
        return unique_results[:limit]
    
    def _clean_search_query(self, query: str) -> str:
        """Clean a search query by removing common words and extra characters"""
        # Common words to filter out
        common_words = {"a", "an", "the", "of", "for", "in", "on", "at", "by", "with", "about"}
        
        # Convert to lowercase, remove punctuation
        query = re.sub(r'[^\w\s]', '', query.lower())
        
        # Split into words and filter out common words and very short words
        words = [word for word in query.split() if word not in common_words and len(word) > 2]
        
        # If we have specific keywords like 'anime', 'demon slayer', etc. prioritize them
        priority_keywords = {"anime", "demon", "slayer", "nezuko", "tanjiro", "zenitsu"}
        priority_words = [word for word in words if word in priority_keywords]
        
        # If we have priority words, make sure they're first
        if priority_words:
            for word in priority_words:
                words.remove(word)
            words = priority_words + words
        
        # If we ended up with nothing, return the original query
        if not words:
            return query
            
        # Join back into a string
        return " ".join(words)
        
    def format_meme_for_display(self, meme: Meme) -> Tuple[str, Optional[str]]:
        """
        Format a meme for display in the chat interface
        
        Returns:
            Tuple of (text_content, image_url) - either can be None
        """
        if meme.content_type == "text":
            return f"📝 **{meme.title}**: {meme.url}", None
        
        # For image or gif, return the emoji + title and the content URL
        text = f"🖼️ **{meme.title}**"
        image_url = meme.url
        
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