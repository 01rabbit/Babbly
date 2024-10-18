#!/usr/bin/python3
import sys
import os
import subprocess
import time
import threading
from janome.analyzer import Analyzer
from janome.tokenfilter import CompoundNounFilter
from vosk_asr_module import initialize_vosk_asr, get_asr_result
from speech import speak_text_aloud
from ipaddress_manager import IPAddressManager


WAKEUP_PHRASE = "プログラム"  # ウェイクアップフレーズ
EXIT_PHRASE = "終了"          # 終了フレーズ
COMMANDS_PATH = 'commands.txt'

def analyze_text(message):
    """受け取った文字列を形態素解析する

    Args:
       message : 解析する文字列
    """
    messages = []
    # janomeで形態素解析した結果を複合名詞化してリスト化
    a = Analyzer(token_filters=[CompoundNounFilter()])

    # `analyze`メソッドで解析を実行し、各トークンを処理する
    for token in a.analyze(message):
        # トークンの基本形 (base_form) をリストに追加
        messages.append(token.base_form)

    return messages

def load_commands(file_path):
    """コマンドマッピングの読み込みをする

    Args:
       file_path : コマンドファイルのパス
    """
    command_map = {}
    with open(file_path, 'r') as file:
        for line in file:
            key, command = line.strip().split(',')
            command_map[key] = command
    return command_map

def listen_for_wakeup_phrase(vosk_asr):
    """ウェイクアップフレーズが認識されるまで待機する.

    Args:
       vosk_asr (VoskStreamingASR): 音声認識モジュール
    """
    while True:
        recog_text = get_asr_result(vosk_asr)
        if recog_text:
            print(f"認識テキスト: {recog_text}")
            userOrder=[]
            userOrder = analyze_text(recog_text)
            if WAKEUP_PHRASE in userOrder:
                print("ウェイクアップフレーズ認識！次の入力を待機します。")
                speak_text_aloud("起動コードを認識")
                listen_for_command(vosk_asr)  # ウェイクアップ後にコマンドを待機

#------test-------
def find_target_ip(comparison_list, target_dict):
    # target_dictから名前のリストを作成
    target_names = [value['name'] for value in target_dict.values()]
    
    # comparison_listの各要素をチェック
    for item in comparison_list:
        if item in target_names:
            # 一致する名前が見つかった場合、そのIPアドレスを返す
            for value in target_dict.values():
                if value['name'] == item:
                    return item, value['ip']
    
    return None, None  # 一致するターゲットが見つからない場合

def listen_for_command(vosk_asr):
    """ウェイクアップ後のコマンド入力を待機する.

    Args:
       vosk_asr (VoskStreamingASR): 音声認識モジュール
    """
    command_map = load_commands(COMMANDS_PATH)
    last_modified = os.path.getmtime(COMMANDS_PATH)

    #-----test--------
    manager = IPAddressManager("target.csv")
    target_dict = manager.load_targets()




    print("コマンドを入力してください（終了するには 'exit' を言ってください）")
    speak_text_aloud("何か指示をしてください")
    while True:
        # ファイル変更の監視
        if os.path.getmtime(COMMANDS_PATH) != last_modified:
            command_map = load_commands(COMMANDS_PATH)
            last_modified = os.path.getmtime(COMMANDS_PATH)

        # 音声認識結果を取得
        recog_text = get_asr_result(vosk_asr)
        if recog_text:
            print(f"認識テキスト: {recog_text}")
            userOrder=[]
            userOrder = analyze_text(recog_text)
            if EXIT_PHRASE in userOrder:
                print("終了フレーズ認識！処理を終了します。")
                speak_text_aloud("終了フレーズ認識！終了します。")
                sys.exit(0)  # 終了フレーズが認識されたらプログラムを終了
            else:
                print(f"コマンド実行: {recog_text}")
                matching_item = set(userOrder) & set(command_map)

                #------test--------
                target_name, target_ip = find_target_ip(userOrder, target_dict)


                if matching_item:
                    # セットから要素を1つ取り出す（複数マッチした場合は1つ目のみ使用）
                    matched_key = next(iter(matching_item))
                    speak_text_aloud(f"{matched_key}を実行します")

                    # perform_action を別スレッドで実行
                    action_thread = threading.Thread(target=perform_action, args=(command_map[matched_key],))
                    action_thread.start()
                print("再度ウェイクアップフレーズを待機します。")
                break  # ウェイクアップフレーズの待機に戻る

def perform_action(command):
    """コマンドに基づいて処理を実行する関数."""
    time.sleep(10)
    print(f"受け取ったコマンドを実行: {command}")
    speak_text_aloud("コマンドを実行しました")


# 音声認識を初期化
vosk_asr = initialize_vosk_asr()

print("＜音声認識開始 - 入力を待機します＞")
while True:
    listen_for_wakeup_phrase(vosk_asr)
