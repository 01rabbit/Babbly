#!/usr/bin/env python3
import subprocess

def speak_text_aloud(text_to_speak):
    """Convert the given string to speech and play it aloud using espeak.

    Args:
       text_to_speak (str): The string to be spoken aloud
    """
    subprocess.run(['espeak', '-s', '140', text_to_speak])

def main():
    speak_text_aloud("Recommended: Enter the target promptly.")
    
if __name__ == "__main__":
    main()
