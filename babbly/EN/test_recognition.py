import time
from english_speech_recognition import initialize_vosk_asr, get_asr_result

def test_english_recognition():
    # 英語モデルのパス（適宜変更してください）
    model_path = "babbly/EN/model"
    vosk_asr = initialize_vosk_asr(model_path)

    print("Start speaking...")

    try:
        while True:
            # 音声認識結果を取得
            result_text = get_asr_result(vosk_asr)
            if result_text:
                print("Recognized Text:", result_text)
            else:
                print("No speech detected, or incomplete phrase.")

            # 一度テストを行いたい場合、以下の `time.sleep` で適宜録音時間を調整
            time.sleep(1)
    except KeyboardInterrupt:
        print("Test terminated.")

# テストを実行
if __name__ == "__main__":
    test_english_recognition()
