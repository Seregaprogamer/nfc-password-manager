"""
Service for Android Intent handling
Simplified version for GitHub Actions
"""

from kivy.utils import platform

def setup_intent_handler(callback):
    print(f"Intent handler setup called with callback: {callback}")
    # In GitHub Actions this won't execute
    # Real implementation will be on device
    pass

if platform == 'android':
    print("Running on Android")
else:
    print(f"Running on {platform}, using stub implementation")
