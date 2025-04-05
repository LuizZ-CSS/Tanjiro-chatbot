import os
import json
import openai
from typing import List, Dict, Any
from collections import deque
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MemoryAgent:
    """
    Memory Agent responsible for:
    1. Recording conversation history
    2. Analyzing user interests 
    3. Providing context to the Tanjiro bot
    """
    
    def __init__(self, api_key: str = None, max_entries: int = 10, 
                 cache_file: str = "conversation_cache.json"):
        """Initialize the Memory Agent with API key and cache settings"""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = openai.OpenAI(api_key=self.api_key)
        self.max_entries = max_entries
        self.cache_file = cache_file
        self.cache = deque(maxlen=max_entries)
        self.load_cache()
        self.last_analysis = None
    
    def load_cache(self):
        """Load the cache from disk if it exists"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    # Convert the loaded list to a deque with max length
                    self.cache = deque(cache_data, maxlen=self.max_entries)
        except Exception as e:
            print(f"Error loading cache: {e}")
            self.cache = deque(maxlen=self.max_entries)
    
    def save_cache(self):
        """Save the cache to disk"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(list(self.cache), f)
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def record_interaction(self, user_input: str, tanjiro_response: str):
        """Record a new interaction between the user and Tanjiro"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "response": tanjiro_response
        }
        self.cache.append(entry)
        self.save_cache()
    
    def get_recent_entries(self, count=None):
        """Get the most recent entries from the cache"""
        if count is None or count > len(self.cache):
            return list(self.cache)
        return list(self.cache)[-count:]
    
    def clear_cache(self):
        """Clear the cache"""
        self.cache.clear()
        self.save_cache()
    
    def analyze_user_interests(self) -> Dict[str, Dict]:
        """
        Use OpenAI to analyze the user's interests based on conversation history
        Returns structured information about Demon Slayer topics and general topics
        """
        # Early return if cache is empty
        if not self.cache:
            return {"demon_slayer_topics": {}, "general_topics": {}}
            
        try:
            # Collect user inputs from the cache
            user_inputs = [entry["user_input"] for entry in self.cache]
            
            # Create prompt for OpenAI
            prompt = """Analyze the following user messages from a conversation with Tanjiro (from Demon Slayer anime).
            Identify key topics of interest, both related to Demon Slayer and general topics.
            
            For Demon Slayer topics, consider: characters (Nezuko, Zenitsu, etc), abilities (breathing techniques, etc), 
            plot elements (Muzan, demons, etc), relationships, and other anime-specific content.
            
            For general topics, identify themes, personal interests, and conversation patterns.
            
            User messages:
            """
            
            for i, msg in enumerate(user_inputs, 1):
                prompt += f"\n{i}. {msg}"
            
            prompt += """\n\nPlease analyze and return a JSON object with the following structure:
            {
                "demon_slayer_topics": {"topic1": weight, "topic2": weight, ...},
                "general_topics": {"topic1": weight, "topic2": weight, ...},
                "summary": "Brief summary of user's apparent interests"
            }
            
            Where weights are integers 1-5 indicating the importance/frequency of the topic in the conversation.
            Identify synonyms and related concepts (e.g. "sister" and "Nezuko" might be related).
            Include only topics that are actually discussed.
            """
            
            # Make API call
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                temperature=0.2,
                messages=[
                    {"role": "system", "content": "You are an analysis assistant that identifies topics and patterns in conversation data."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            analysis = json.loads(response.choices[0].message.content)
            
            # Store the full analysis for later use
            self.last_analysis = analysis
                
            return analysis
            
        except Exception as e:
            print(f"Error in OpenAI analysis: {e}")
            # Fall back to the simpler keyword-based analysis
            return self.fallback_interest_analysis()
    
    def fallback_interest_analysis(self) -> Dict[str, Dict]:
        """Fallback method for topic analysis if OpenAI analysis fails"""
        # Keywords to look for in conversations - Demon Slayer themed
        demon_slayer_topics = {
            "nezuko": 0, "family": 0, "demons": 0, "breathing technique": 0, 
            "muzan": 0, "hashira": 0, "sword": 0, "water breathing": 0,
            "mission": 0, "sister": 0, "training": 0, "final selection": 0,
            "urokodaki": 0, "hinokami": 0, "dance": 0, "slayer": 0,
            "corps": 0, "inosuke": 0, "zenitsu": 0, "fight": 0
        }
        
        # General conversation topics
        general_topics = {
            "help": 0, "friend": 0, "strong": 0, "kind": 0, 
            "power": 0, "protect": 0, "love": 0, "hope": 0,
            "mission": 0, "goal": 0, "dream": 0, "future": 0
        }
        
        # Count occurrences of topics in user inputs
        for entry in self.cache:
            user_input = entry["user_input"].lower()
            
            # Check Demon Slayer topics
            for topic in demon_slayer_topics:
                if topic in user_input:
                    demon_slayer_topics[topic] += 1
            
            # Check general topics
            for topic in general_topics:
                if topic in user_input:
                    general_topics[topic] += 1
        
        # Filter out topics with zero occurrences
        filtered_ds_topics = {k: v for k, v in demon_slayer_topics.items() if v > 0}
        filtered_gen_topics = {k: v for k, v in general_topics.items() if v > 0}
        
        return {
            "demon_slayer_topics": filtered_ds_topics,
            "general_topics": filtered_gen_topics,
            "summary": "Analysis based on keyword matching only."
        }
    
    def generate_context_for_tanjiro(self) -> str:
        """
        Generate context information from conversation history for Tanjiro
        This gets added to Tanjiro's system prompt to help him respond appropriately
        """
        if not self.cache:
            return ""
        
        context_parts = []
        
        # Get fresh analysis or use cached analysis
        try:
            analysis = self.analyze_user_interests()
            
            # Extract topics
            demon_slayer_topics = analysis.get("demon_slayer_topics", {})
            general_topics = analysis.get("general_topics", {})
            
            # Combine and sort topics
            all_topics = {**demon_slayer_topics, **general_topics}
            
            if all_topics:
                # Sort topics by frequency/weight
                sorted_topics = sorted(all_topics.items(), key=lambda x: x[1], reverse=True)
                top_interests = sorted_topics[:3]  # Get top 3 interests
                
                if top_interests:
                    topics_str = ", ".join([f"{topic}" for topic, count in top_interests])
                    context_parts.append(f"The user has shown interest in these topics: {topics_str}.")
            
            # Include the full summary if available
            if "summary" in analysis:
                context_parts.append(f"User context: {analysis['summary']}")
                
        except Exception as e:
            print(f"Error generating context: {e}")
            # No fallback here - if we can't generate context, we'll just return empty string
        
        # Combine all context
        if context_parts:
            return "\n".join(context_parts)
        
        return ""
    
    def display_history(self):
        """Display the conversation history from the cache"""
        entries = self.get_recent_entries()
        if not entries:
            print("\nNo conversation history available.")
            return
        
        print("\n" + "=" * 50)
        print("Recent Conversation History:")
        print("=" * 50)
        
        for i, entry in enumerate(entries, 1):
            timestamp = datetime.fromisoformat(entry["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{i}] {timestamp}")
            print(f"You: {entry['user_input']}")
            print(f"Tanjiro: {entry['response']}")
            print("-" * 30)
    
    def display_interests(self):
        """Display the user's interests based on conversation history"""
        try:
            # Analyze user interests
            analysis = self.analyze_user_interests()
            ds_topics = analysis.get("demon_slayer_topics", {})
            gen_topics = analysis.get("general_topics", {})
            
            print("\n" + "=" * 50)
            print("Tanjiro's Understanding of Your Interests:")
            print("=" * 50)
            
            if not ds_topics and not gen_topics:
                print("\nTanjiro hasn't identified any specific topics of interest yet.")
            else:
                # Display Demon Slayer topics if available
                if ds_topics:
                    print("\nDemon Slayer Topics:")
                    for topic, weight in sorted(ds_topics.items(), key=lambda x: x[1], reverse=True):
                        stars = "★" * int(weight)
                        print(f"- {topic.capitalize()}: {stars} ({weight})")
                        
                # Display general topics if available
                if gen_topics:
                    print("\nGeneral Topics:")
                    for topic, weight in sorted(gen_topics.items(), key=lambda x: x[1], reverse=True):
                        stars = "★" * int(weight)
                        print(f"- {topic.capitalize()}: {stars} ({weight})")
                
                # Display analysis summary if available
                if "summary" in analysis:
                    print("\nSummary:")
                    print(analysis["summary"])
            
            print("-" * 50)
        
        except Exception as e:
            print(f"\nError displaying interests: {e}")
            print("Unable to analyze user interests at this time.") 