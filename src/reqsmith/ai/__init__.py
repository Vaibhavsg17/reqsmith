"""
AI module for Gemini-powered features.
"""

from .gemini_client import (
    GeminiClient,
    ValidationResult,
    SecureKeyManager,
    check_gemini_availability
)
from .assistant import (
    AIAssistant,
    AIFeatureManager
)
from .validators import (
    AIValidator,
    SmartSuggestionEngine
)

__all__ = [
    # Gemini client
    'GeminiClient',
    'ValidationResult',
    'SecureKeyManager',
    'check_gemini_availability',
    
    # AI assistant
    'AIAssistant',
    'AIFeatureManager',
    
    # Validators and suggestions
    'AIValidator',
    'SmartSuggestionEngine'
]