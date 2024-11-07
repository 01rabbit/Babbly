import json
import queue
import sys
from collections import namedtuple
import sounddevice as sd
from vosk import KaldiRecognizer, Model, SetLogLevel

class MicrophoneStream:
    """マイク音声入力のためのクラス."""
    def __init__(self, rate, chunk):
        self.rate = rate
        self.chunk = chunk
        self.buff = queue.Queue()
        self.input_stream = None

    def open_stream(self):
        self.input_stream = sd.RawInputStream(
            samplerate=self.rate,
            blocksize=self.chunk,
            dtype="int16",
            channels=1,
            callback=self.callback,
        )

    def callback(self, indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        self.buff.put(bytes(indata))

    def generator(self):
        while True:
            chunk = self.buff.get()
            if chunk is None:
                return
            data = [chunk]
            while True:
                try:
                    chunk = self.buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break
            yield b"".join(data)

def get_asr_result(vosk_asr):
    """音声認識APIを実行して最終的な認識結果を得る."""
    mic_stream = vosk_asr.microphone_stream
    mic_stream.open_stream()
    with mic_stream.input_stream:
        audio_generator = mic_stream.generator()
        for content in audio_generator:
            if vosk_asr.recognizer.AcceptWaveform(content):
                recog_result = json.loads(vosk_asr.recognizer.Result())
                recog_text = recog_result["text"].split()
                recog_text = "".join(recog_text)  # 空白記号を除去
                return recog_text
        return None

def initialize_vosk_asr(model_path="babbly/EN/model", chunk_size=8000):
    """Voskの音声認識モジュールを初期化する."""
    SetLogLevel(-1)
    input_device_info = sd.query_devices(kind="input")
    sample_rate = int(input_device_info["default_samplerate"])

    mic_stream = MicrophoneStream(sample_rate, chunk_size)
    recognizer = KaldiRecognizer(Model(model_path), sample_rate)

    VoskStreamingASR = namedtuple("VoskStreamingASR", ["microphone_stream", "recognizer"])
    return VoskStreamingASR(mic_stream, recognizer)
