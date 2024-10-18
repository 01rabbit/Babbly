#!/usr/bin/env python3
import sys
import subprocess
DICT_PATH='/var/lib/mecab/dic/open-jtalk/naist-jdic/'
VOICE_PATH='/usr/share/hts-voice/nitech-jp-atr503-m001/nitech_jp_atr503_m001.htsvoice'

def speak_text_aloud(text_to_speak):
    """引数の文字列を音声に変換して発話するメソッド.

    Args:
       text_to_speak (str): 発話したい文字列
    """

    with open('speech.txt', 'w') as f:
        f.write(text_to_speak)
    subprocess.run(['open_jtalk', '-x', DICT_PATH, '-m', VOICE_PATH, '-ow', 'speech.wav', 'speech.txt'])
    subprocess.run(['aplay', '-q', 'speech.wav'])

def main():
    speak_text_aloud("推奨：速やかなターゲットの入力")
    
if __name__ == "__main__":
    main()