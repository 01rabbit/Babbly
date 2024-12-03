import pyopenjtalk
import numpy as np
from scipy.io import wavfile
import os
from typing import Optional, Dict, Tuple, Union
import subprocess
from dataclasses import dataclass

@dataclass
class VoiceResult:
    """音声生成結果を保持するデータクラス"""
    filepath: str
    duration: float  # 音声の長さ（秒）
    settings: Dict[str, float]  # 使用された設定値

class Japanese_TTS:
    """
    OpenJTalkを使用した音声合成のクラス
    設定の管理と音声生成、再生を担当
    """
    
    def __init__(self, 
                 default_speed_rate: float = 1.0,
                 default_alpha: float = 0.55,
                 default_master_volume: float = 1.0,
                 auto_play: bool = True):
        """
        初期化メソッド
        
        Args:
            default_speed_rate (float): デフォルトの話速
            default_alpha (float): デフォルトの声質パラメータ
            default_master_volume (float): デフォルトの音量
            auto_play (bool): 音声生成後に自動再生するかどうか
        """
        self.default_settings = {
            'speed_rate': default_speed_rate,
            'alpha': default_alpha,
            'master_volume': default_master_volume
        }
        self.auto_play = auto_play
        
        # プリセット設定
        self.presets = {
            'standard': {
                'speed_rate': 0.9,
                'alpha': 0.45,
                'master_volume': 1.0
            },
            'presentation': {
                'speed_rate': 0.8,
                'alpha': 0.5,
                'master_volume': 1.2
            },
            'fast': {
                'speed_rate': 1.2,
                'alpha': 0.45,
                'master_volume': 1.0
            }
        }
    
    def _process_text(self, text: str) -> str:
        """テキストの前処理"""
        text = text.replace('、', '、 ')
        text = text.replace('。', '。 ')
        return text
    
    def _adjust_wave(self, 
                    wave: np.ndarray, 
                    speed_rate: float,
                    master_volume: float) -> np.ndarray:
        """波形データの調整"""
        if speed_rate != 1.0:
            original_len = len(wave)
            new_len = int(original_len / speed_rate)
            indices = np.linspace(0, original_len - 1, new_len)
            wave = np.interp(indices, np.arange(original_len), wave)
        
        wave = wave * master_volume
        wave = wave / np.max(np.abs(wave))
        
        return wave
    
    def play_voice(self, filepath: str) -> None:
        """音声ファイルを再生"""
        try:
            subprocess.run(['aplay', '-q', filepath], check=True)
        except subprocess.CalledProcessError as e:
            print(f"音声再生中にエラーが発生しました: {e}")
        except FileNotFoundError:
            print("aplayコマンドが見つかりません。システムに適切な音声再生プログラムがインストールされているか確認してください。")
    
    def say(self, 
                    text: str,
                    output_filename: Optional[str] = None,
                    preset: Optional[str] = None,
                    play: Optional[bool] = None,
                    **kwargs) -> VoiceResult:
        """
        音声の生成と再生
        
        Args:
            text (str): 読み上げるテキスト
            output_filename (Optional[str]): 出力ファイル名
            preset (Optional[str]): 使用するプリセット名
            play (Optional[bool]): 生成後に再生するかどうか（Noneの場合はインスタンスのデフォルト設定を使用）
            **kwargs: 個別の設定値（speed_rate, alpha, master_volume）
            
        Returns:
            VoiceResult: 生成された音声の情報
        """
        # 設定の取得
        settings = self.default_settings.copy()
        if preset and preset in self.presets:
            settings.update(self.presets[preset])
        settings.update({k: v for k, v in kwargs.items() if k in settings})
        
        # 出力ファイル名の設定
        if output_filename is None:
            output_filename = "speech.wav"
        output_path = os.path.join(output_filename)
        
        # テキストの前処理
        processed_text = self._process_text(text)
        
        # 音声合成
        wave, sr = pyopenjtalk.tts(processed_text)
        
        # 波形の調整
        wave = self._adjust_wave(
            wave,
            settings['speed_rate'],
            settings['master_volume']
        )
        
        # ファイルの保存
        wavfile.write(output_path, sr, (wave * 32767).astype(np.int16))
        
        # 音声の長さを計算（秒）
        duration = len(wave) / sr
        
        # 結果オブジェクトの作成
        result = VoiceResult(
            filepath=output_path,
            duration=duration,
            settings=settings
        )
        
        # 音声の再生
        should_play = play if play is not None else self.auto_play
        if should_play:
            self.play_voice(output_path)
        
        return result
    
    def add_preset(self, 
                  name: str,
                  settings: Dict[str, float]) -> None:
        """新しいプリセットの追加"""
        self.presets[name] = settings
    
    def get_preset_settings(self, preset: str) -> Optional[Dict[str, float]]:
        """プリセット設定の取得"""
        return self.presets.get(preset)

def example_usage():
    synthesizer = Japanese_TTS()
    synthesizer.say("人工無能システム、バブリー、起動します")

if __name__ == "__main__":
    example_usage()