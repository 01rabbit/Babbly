#!/usr/bin/python3
import sys
import logging
import pyfiglet
from babbly.ja.vosk_asr_module import initialize_vosk_asr, get_asr_result
from babbly.ja.japanese_tts import Japanese_TTS
from babbly.modules.ipaddress_manager import IPAddressManager
from babbly.modules.operation_manager import OperationManager
from babbly.modules.network_scanner import NetworkScanner
from babbly.modules.utils import analyze_text # 日本語環境限定
from babbly.modules.utils import load_config, assist_command_mode, select_target, introduce
from babbly.modules.commands_manager import CommandManager

tts = Japanese_TTS()
lang_ja = 1

# グローバル変数に代入する関数
def set_globals(config):
    global WAKEUP_PHRASE, EXIT_PHRASE, COMMANDS_PATH, TARGETS_PATH, SOP_PATH, MODEL_PATH
    WAKEUP_PHRASE = config.get("WAKEUP_PHRASE")
    EXIT_PHRASE = config.get("EXIT_PHRASE")
    COMMANDS_PATH = config.get("COMMANDS_PATH")
    TARGETS_PATH = config.get("TARGETS_PATH")
    SOP_PATH = config.get("SOP_PATH")
    MODEL_PATH = config.get("MODEL_PATH")


def listen_for_wakeup_phrase(vosk_asr):
    """ウェイクアップフレーズが認識されるまで待機する.

    :param:vosk_asr (VoskStreamingASR): 音声認識モジュール
    """
    try:
        while True:
            recog_text = get_asr_result(vosk_asr)
            if recog_text:
                print(f"認識テキスト: {recog_text}")
                userOrder=[]
                userOrder = analyze_text(recog_text)
                if WAKEUP_PHRASE in userOrder:
                    print("ウェイクアップフレーズ認識！次の入力を待機します。")
                    tts.say("はい、ボス")
                    listen_for_command(vosk_asr)  # ウェイクアップ後にコマンドを待機
    except KeyboardInterrupt:
        print("\nCtrl+Cが押されました。プログラムを終了します。")
        logging.info("システム終了")
        exit()


def listen_for_command(vosk_asr):
    """ウェイクアップ後のコマンド入力を待機する.

    :param:vosk_asr (VoskStreamingASR): 音声認識モジュール
    """
    cmd_mgr = CommandManager(COMMANDS_PATH)
    command_dict = cmd_mgr.get_search_dict()

    ip_mgr = IPAddressManager(TARGETS_PATH)
    target_dict = ip_mgr.get_search_dict()

    op_mgr = OperationManager(SOP_PATH)
    operation_dict = op_mgr.get_search_dict()

    try:
        print(f"コマンドを入力してください（終了するには {EXIT_PHRASE} を言ってください）")
        tts.say("指示をどうぞ")
        # time.sleep(1)
        while True:
            # 音声認識結果を取得
            recog_text = get_asr_result(vosk_asr)
            if recog_text:
                print(f"認識テキスト: {recog_text}")
                userOrder = analyze_text(recog_text)


                if EXIT_PHRASE in userOrder:
                    print("終了フレーズ認識！処理を終了します。")
                    tts.say("システムを終了します。お疲れ様でした。")
                    sys.exit(0)  # 終了フレーズが認識されたらプログラムを終了

                elif "自己紹介" in userOrder:
                    introduce(tts, lang_ja)
                    break
                
                elif "ネットワーク" and "スキャン" in userOrder:
                    netscan = NetworkScanner()
                    netscan.network_scan(tts, ip_mgr, lang_ja)
                    break

                elif "ターゲット" and ("教える" or "表示") in userOrder:
                    target_name, target_ip = ip_mgr.find_target_ip(userOrder)
                    if target_name:
                        print(f"{target_name}: {target_ip}")
                        tts.say(f"{target_name}: {target_ip}")
                    else:
                        print(f"{target_name}が見つかりません")
                    break

                elif "コマンド" in userOrder:
                    assist_command_mode(cmd_mgr, ip_mgr, vosk_asr, tts, command_dict,lang_ja)
                    break

                else:
                    ipaddress, cmd_name, op_name = None, None, None
                    for word in userOrder:
                        if not ipaddress:
                            result = ip_mgr.get_target_values(word)
                            if result:
                                _, ipaddress = result
                        if not cmd_name:
                            result = cmd_mgr.get_command_values(word)
                            if result:
                                cmd_name, cmd_arg = result
                        if not op_name:
                            result = op_mgr.get_operation_values(word)
                            if result:
                                op_name, _ = result
                        if ipaddress and op_name:
                            break
                        elif ipaddress and cmd_name:
                            break

                    if op_name:
                        if ipaddress == None:
                            ipaddress = select_target(ip_mgr, tts, vosk_asr, lang_ja)
                        op_mgr.run_operation(op_name, ipaddress)
                        break
                    elif cmd_name:
                        if cmd_arg and not ipaddress:
                            ipaddress = select_target(ip_mgr, tts, vosk_asr, lang_ja)
                        cmd_mgr.execute_command(cmd_name, ipaddress if cmd_arg else None)
                        break
        print("再度ウェイクアップフレーズを待機します。")
    except KeyboardInterrupt:
        print("\nCtrl+Cが押されました。プログラムを終了します。")
        logging.info("システム終了")
        exit()

def main():
    ascii_art = pyfiglet.figlet_format("Babbly", font="dos_rebel")
    print(ascii_art)
    
    logging.info("プログラム開始")

    config = load_config("babbly/ja/config_ja.yaml")
    set_globals(config)
    logging.info("設定読み込み完了")

    # 音声認識を初期化
    vosk_asr = initialize_vosk_asr(MODEL_PATH)
    logging.info("音声認識機能 初期化完了")

    print("＜音声認識開始 - 入力を待機します＞")
    tts.say(f"人工無能システム、バブリー、起動します。")
    while True:
        listen_for_wakeup_phrase(vosk_asr)

if __name__ == '__main__':
    main()
