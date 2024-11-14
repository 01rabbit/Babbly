# pico_tts.py

import subprocess
import os
import tempfile
from typing import Optional

class PicoTTS:
    """
    Pico TTS wrapper class for text-to-speech conversion.
    
    Attributes:
        last_error (str): Contains the last error message if any operation fails
    """
    
    def __init__(self) -> None:
        """Initialize the PicoTTS instance."""
        self.last_error: str = ""
        self._check_dependencies()
    
    def _check_dependencies(self) -> bool:
        """
        Check if required dependencies are installed.
        
        Returns:
            bool: True if all dependencies are available, False otherwise
        """
        try:
            subprocess.run(['which', 'pico2wave'], 
                         check=True, 
                         capture_output=True)
            subprocess.run(['which', 'aplay'], 
                         check=True, 
                         capture_output=True)
            return True
        except subprocess.CalledProcessError:
            self.last_error = ("Required dependencies not found. "
                             "Please install libttspico-utils and alsa-utils: "
                             "sudo apt-get install libttspico-utils alsa-utils")
            return False

    def say(self, text: str, language: str = "en-US") -> bool:
        """
        Convert text to speech and play it.
        
        Args:
            text (str): Text to be converted to speech
            language (str, optional): Language code. Defaults to "en-US"
        
        Returns:
            bool: True if successful, False if an error occurred
        """
        if not text:
            self.last_error = "Empty text provided"
            return False
            
        try:
            # Create temporary wave file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Generate speech
            result = subprocess.run([
                'pico2wave',
                '-w', temp_path,
                '-l', language,
                text
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                self.last_error = f"pico2wave error: {result.stderr}"
                return False
            
            # Play the audio
            result = subprocess.run([
                'aplay',
                '-q',  # Quiet mode
                temp_path
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                self.last_error = f"aplay error: {result.stderr}"
                return False
                
            return True
            
        except Exception as e:
            self.last_error = str(e)
            return False
            
        finally:
            # Clean up temporary file
            if 'temp_path' in locals():
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    self.last_error = f"Failed to remove temporary file: {e}"
    
    def get_last_error(self) -> str:
        """
        Get the last error message.
        
        Returns:
            str: The last error message
        """
        return self.last_error