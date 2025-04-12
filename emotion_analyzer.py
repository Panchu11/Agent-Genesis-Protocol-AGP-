"""
Emotion Analyzer for AGP
------------------------
This module provides emotion detection capabilities for AGP agents.
It analyzes text input to detect emotions and sentiment.
"""

import re
import json
import os
from collections import Counter

# Emotion categories and their associated keywords
EMOTION_KEYWORDS = {
    "joy": ["happy", "glad", "delighted", "pleased", "excited", "thrilled", "enjoy", "love", "wonderful",
            "great", "excellent", "fantastic", "amazing", "awesome", "good", "positive", "yay", "smile",
            "laugh", "haha", "lol", "nice", "fun", "celebrate", "congratulations", "congrats", "thank", "thanks"],

    "sadness": ["sad", "unhappy", "disappointed", "upset", "depressed", "miserable", "heartbroken",
                "gloomy", "down", "blue", "sorry", "regret", "miss", "lonely", "alone", "cry", "tears",
                "sigh", "unfortunately", "bad", "terrible", "awful", "worst", "failed", "failure"],

    "anger": ["angry", "mad", "furious", "annoyed", "irritated", "frustrated", "outraged", "hate",
              "dislike", "resent", "despise", "damn", "hell", "stupid", "idiot", "fool", "ridiculous",
              "absurd", "unfair", "wrong", "complaint", "blame", "fault"],

    "fear": ["afraid", "scared", "frightened", "terrified", "anxious", "nervous", "worried", "concerned",
             "panic", "dread", "horror", "terror", "alarmed", "uneasy", "apprehensive", "doubt", "uncertain",
             "unsure", "risk", "danger", "threat", "warning"],

    "surprise": ["surprised", "amazed", "astonished", "shocked", "stunned", "startled", "unexpected",
                "sudden", "wow", "whoa", "oh", "omg", "gosh", "really", "seriously", "unbelievable",
                "incredible", "extraordinary", "remarkable"],

    "confusion": ["confused", "puzzled", "perplexed", "bewildered", "lost", "unsure", "uncertain",
                 "doubt", "question", "wonder", "curious", "strange", "odd", "weird", "complicated",
                 "complex", "difficult", "hard", "challenging", "problem", "issue", "help", "assistance"],

    "neutral": ["okay", "ok", "fine", "alright", "so", "well", "anyway", "however", "therefore",
               "thus", "hence", "consequently", "subsequently", "accordingly", "normal", "usual",
               "typical", "standard", "common", "ordinary", "regular"]
}

# Intensity modifiers and their weights
INTENSITY_MODIFIERS = {
    "very": 1.5,
    "extremely": 2.0,
    "incredibly": 2.0,
    "really": 1.5,
    "so": 1.3,
    "quite": 1.2,
    "somewhat": 0.7,
    "slightly": 0.5,
    "a bit": 0.6,
    "a little": 0.6,
    "not": -0.8,
    "don't": -0.8,
    "doesn't": -0.8,
    "didn't": -0.8,
    "never": -1.0,
    "hardly": -0.7,
    "barely": -0.7
}

class EmotionAnalyzer:
    """Analyzes text to detect emotions and sentiment."""

    def __init__(self):
        """Initialize the emotion analyzer."""
        self.emotion_keywords = EMOTION_KEYWORDS
        self.intensity_modifiers = INTENSITY_MODIFIERS
        self.emotion_history = []
        self.history_file = os.path.join("agents", "emotion_history.json")
        self._load_history()

    def _load_history(self):
        """Load emotion history from file."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    self.emotion_history = json.load(f)
            except:
                self.emotion_history = []

    def _save_history(self):
        """Save emotion history to file."""
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        with open(self.history_file, 'w') as f:
            json.dump(self.emotion_history, f, indent=2)

    def analyze(self, text, user_id="default"):
        """
        Analyze text to detect emotions.

        Args:
            text (str): The text to analyze
            user_id (str): Identifier for the user

        Returns:
            dict: Detected emotions and their scores
        """
        if not text:
            return {"dominant_emotion": "neutral", "emotions": {"neutral": 1.0}, "intensity": 0.5}

        # Normalize text
        text = text.lower()
        words = re.findall(r'\b\w+\b', text)

        # Count emotions
        emotion_scores = {emotion: 0 for emotion in self.emotion_keywords}

        # First pass: find intensity modifiers
        modifiers = {}
        for i, word in enumerate(words):
            if word in self.intensity_modifiers:
                # Look ahead to find what this modifier affects
                for j in range(i+1, min(i+4, len(words))):
                    for emotion, keywords in self.emotion_keywords.items():
                        if words[j] in keywords:
                            modifiers[j] = self.intensity_modifiers[word]
                            break

        # Second pass: count emotion keywords with modifiers
        for i, word in enumerate(words):
            for emotion, keywords in self.emotion_keywords.items():
                if word in keywords:
                    modifier = modifiers.get(i, 1.0)
                    emotion_scores[emotion] += modifier

        # Normalize scores
        total = sum(emotion_scores.values())
        if total > 0:
            emotion_scores = {k: v/total for k, v in emotion_scores.items()}
        else:
            emotion_scores = {"neutral": 1.0}

        # Find dominant emotion
        dominant_emotion = max(emotion_scores, key=emotion_scores.get)

        # Calculate overall intensity (0-1)
        non_neutral_score = sum(v for k, v in emotion_scores.items() if k != "neutral")
        intensity = min(1.0, non_neutral_score * 1.5)  # Scale up a bit, cap at 1.0

        # Create result
        result = {
            "dominant_emotion": dominant_emotion,
            "emotions": emotion_scores,
            "intensity": intensity
        }

        # Add to history
        from datetime import datetime
        self.emotion_history.append({
            "user_id": user_id,
            "text": text,
            "analysis": result,
            "timestamp": str(datetime.now())
        })

        # Keep history at a reasonable size
        if len(self.emotion_history) > 100:
            self.emotion_history = self.emotion_history[-100:]

        self._save_history()
        return result

    def get_emotion_trend(self, user_id="default", limit=10):
        """
        Get the trend of emotions for a user.

        Args:
            user_id (str): Identifier for the user
            limit (int): Number of recent entries to consider

        Returns:
            dict: Emotion trends
        """
        user_history = [entry for entry in self.emotion_history
                        if entry["user_id"] == user_id][-limit:]

        if not user_history:
            return {"trend": "neutral", "stability": 1.0}

        # Count dominant emotions
        emotion_counts = Counter([entry["analysis"]["dominant_emotion"]
                                 for entry in user_history])

        # Find most common emotion
        most_common = emotion_counts.most_common(1)[0][0]

        # Calculate stability (how consistent the emotions are)
        stability = emotion_counts[most_common] / len(user_history)

        return {
            "trend": most_common,
            "stability": stability,
            "counts": dict(emotion_counts)
        }

    def get_response_guidance(self, emotion_data):
        """
        Get guidance for how an agent should respond based on emotion analysis.

        Args:
            emotion_data (dict): The emotion analysis data

        Returns:
            dict: Response guidance
        """
        dominant = emotion_data["dominant_emotion"]
        intensity = emotion_data["intensity"]

        guidance = {
            "tone": "neutral",
            "approach": "balanced",
            "priority": "information"
        }

        # Adjust tone based on dominant emotion
        if dominant == "joy":
            guidance["tone"] = "positive"
            guidance["approach"] = "enthusiastic"
            guidance["priority"] = "engagement"

        elif dominant == "sadness":
            guidance["tone"] = "empathetic"
            guidance["approach"] = "supportive"
            guidance["priority"] = "comfort"

        elif dominant == "anger":
            guidance["tone"] = "calm"
            guidance["approach"] = "respectful"
            guidance["priority"] = "resolution"

        elif dominant == "fear":
            guidance["tone"] = "reassuring"
            guidance["approach"] = "clear"
            guidance["priority"] = "safety"

        elif dominant == "surprise":
            guidance["tone"] = "engaged"
            guidance["approach"] = "explanatory"
            guidance["priority"] = "clarification"

        elif dominant == "confusion":
            guidance["tone"] = "helpful"
            guidance["approach"] = "step-by-step"
            guidance["priority"] = "clarity"

        # Adjust intensity
        if intensity < 0.3:
            guidance["intensity"] = "mild"
        elif intensity < 0.7:
            guidance["intensity"] = "moderate"
        else:
            guidance["intensity"] = "strong"

        return guidance


# For testing
if __name__ == "__main__":
    analyzer = EmotionAnalyzer()

    test_texts = [
        "I'm so happy today! Everything is going great!",
        "This is really frustrating and making me angry.",
        "I'm feeling a bit sad and disappointed.",
        "I'm not sure what to do, I'm confused.",
        "Wow! That's amazing news!",
        "I'm worried about what might happen.",
        "That's fine, I don't have strong feelings about it."
    ]

    for text in test_texts:
        result = analyzer.analyze(text)
        print(f"\nText: {text}")
        print(f"Dominant emotion: {result['dominant_emotion']}")
        print(f"Emotion scores: {result['emotions']}")
        print(f"Intensity: {result['intensity']}")
        print(f"Response guidance: {analyzer.get_response_guidance(result)}")
