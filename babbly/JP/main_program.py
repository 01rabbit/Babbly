#!/usr/bin/python3
import sys
import os
import subprocess
import yaml
import threading
from janome.analyzer import Analyzer
from janome.tokenfilter import CompoundNounFilter
from babbly.JP.vosk_asr_module import initialize_vosk_asr, get_asr_result
from babbly.JP.speech import speak_text_aloud
from babbly.modules.ipaddress_manager import IPAddressManager
from babbly.modules.operation_manager import OperationManager
from dotenv import load_dotenv

load_dotenv(".env")

# 環境変数からパスを取得
WAKEUP_PHRASE = os.getenv('WAKEUP_PHRASE')      # ウェイクアップフレーズ
EXIT_PHRASE = os.getenv('EXIT_PHRASE')          # 終了フレーズ
COMMANDS_PATH = os.getenv('COMMANDS_PATH')
TARGETS_PATH = os.getenv('TARGETS_PATH')
SOP_PATH = os.getenv('SOP_PATH')


def load_config(file_path):
        """設定ファイルを読み込む"""
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)

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
        # 1行目をスキップする
        next(file)
        for line in file:
            key, command, arg_flg = line.strip().split(',')
            command_map[key] = {'command': command, 'arg_flg': int(arg_flg)}
    return command_map

def find_target_ip(comparison_list, target_dict):
    """
    comparison_list内の名前を使用して、target_dictから一致するターゲットのIPアドレスを探す。

    :param comparison_list: 検査する名前のリスト。ターゲット名が含まれている。
    :param target_dict: ターゲットの情報を含む辞書。キーはターゲットのID、値は辞書（{'name': ターゲット名, 'ip': IPアドレス}の形）。
    :return: 一致するターゲットの名前とIPアドレスのタプル。見つからない場合は (None, None) を返す。
    """
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


def listen_for_wakeup_phrase(vosk_asr):
    """ウェイクアップフレーズが認識されるまで待機する.

    :param:vosk_asr (VoskStreamingASR): 音声認識モジュール
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

def listen_for_command(vosk_asr):
    """ウェイクアップ後のコマンド入力を待機する.

    :param:vosk_asr (VoskStreamingASR): 音声認識モジュール
    """
    command_map = load_commands(COMMANDS_PATH)
    last_modified = os.path.getmtime(COMMANDS_PATH)

    #-----test--------
    ip_manager = IPAddressManager(TARGETS_PATH)
    target_dict = ip_manager.load_targets()
    # OperationManager クラスのインスタンスを作成
    op_manager = OperationManager(SOP_PATH)
    # sop.jsonからオペレーション名のリストを取得
    valid_operations = set(op_manager.get_operation_names())


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
            # userOrder=[]　# 空リストの初期は不要
            userOrder = analyze_text(recog_text)
            #------test--------
            target_name, target_ip = find_target_ip(userOrder, target_dict)

            if EXIT_PHRASE in userOrder:
                print("終了フレーズ認識！処理を終了します。")
                speak_text_aloud("終了フレーズ認識！終了します。")
                sys.exit(0)  # 終了フレーズが認識されたらプログラムを終了

            elif "自己紹介" in userOrder:
                print("自己紹介をします")
                message = f"私は{WAKEUP_PHRASE}。ミスターラビットによって開発された人工無能です"
                speak_text_aloud(message)
                message = "私の役割は、ペネトレーションテストにおいて、あなたを効果的にサポートすることです"
                speak_text_aloud(message)
                print("再度ウェイクアップフレーズを待機します。")
                break  # ウェイクアップフレーズの待機に戻る
            
            # オペレーション名のチェックと実行処理
            elif any(operation in userOrder for operation in valid_operations):
                # userOrder と valid_operations を直接比較して最適化
                matching_operations = [op for op in userOrder if op in valid_operations]
                if matching_operations:
                    # 一致するオペレーションがある場合、最初のものを処理
                    operation = matching_operations[0]
                    if "説明" in userOrder:
                        print(op_manager.get_operation_info(operation))
                    else:
                        print(f"オペレーション '{operation}' が認識されました。実行します。")
                        # ここにオペレーション実行のコードを追加
                    break  # 最初に一致したオペレーションを処理した後ループを抜ける
    
            else:
                print(f"コマンド実行: {recog_text}")
                matching_items = set(userOrder) & set(command_map)

                if matching_items:
                    for matched_key in matching_items:
                        speak_text_aloud(f"{matched_key}を実行します")

                        # コマンド情報を取得
                        command_info = command_map[matched_key]
                        command = command_info['command']
                        arg_flg = command_info['arg_flg']

                        # 引数フラグが1ならプレースホルダを置き換える
                        if arg_flg == 1:
                            action_thread = threading.Thread(target=perform_action, args=(command, target_ip))
                        else:
                            action_thread = threading.Thread(target=perform_action, args=(command,))

                        action_thread.start()
                print("再度ウェイクアップフレーズを待機します。")
                break  # ウェイクアップフレーズの待機に戻る

def perform_action(command, target_ip=None):
    """コマンドに基づいて処理を実行する関数."""
    try:
        # コマンド内のプレースホルダ `{target_ip}` を置き換える
        if target_ip:
            command = command.format(target_ip=target_ip)
        
        # コマンドを実行し、結果を取得
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # 実行結果を出力
        print(f"コマンドの実行結果: {result.stdout}")
        speak_text_aloud("コマンドを実行しました")
    except subprocess.CalledProcessError as e:
        # エラー時の処理
        print(f"コマンドの実行中にエラーが発生しました: {e.stderr}")
        speak_text_aloud("コマンドの実行に失敗しました")

def main():
    # 音声認識を初期化
    vosk_asr = initialize_vosk_asr()

    print("＜音声認識開始 - 入力を待機します＞")
    while True:
        listen_for_wakeup_phrase(vosk_asr)

if __name__ == '__main__':
    main()
