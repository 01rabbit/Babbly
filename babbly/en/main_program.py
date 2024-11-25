#!/usr/bin/python3
import sys
import time
import logging
import pyfiglet
from babbly.en.vosk_asr_module import initialize_vosk_asr, get_asr_result
from babbly.en.english_tts import English_TTS
from babbly.modules.ipaddress_manager import IPAddressManager
from babbly.modules.operation_manager import OperationManager
from babbly.modules.network_scanner import NetworkScanner
from babbly.modules.utils import load_config, assist_command_mode, introduce
from babbly.modules.commands_manager import CommandManager

tts = English_TTS()

def set_globals(config):
    global WAKEUP_PHRASE, EXIT_PHRASE, COMMANDS_PATH, TARGETS_PATH, SOP_PATH, MODEL_PATH
    WAKEUP_PHRASE = config.get("WAKEUP_PHRASE")
    EXIT_PHRASE = config.get("EXIT_PHRASE")
    COMMANDS_PATH = config.get("COMMANDS_PATH")
    TARGETS_PATH = config.get("TARGETS_PATH")
    SOP_PATH = config.get("SOP_PATH")
    MODEL_PATH = config.get("MODEL_PATH")

def find_target_ip(comparison_list, target_dict):
    """
    Find the IP address of the matching target in target_dict using the name in comparison_list.

    :param comparison_list: List of names to examine. It contains the target names.
    :param target_dict: A dictionary containing information about the target. The key is the target ID and the value is a dictionary (in the form of {'name': target name, 'ip': IP address}).
    :return: A tuple of matching target names and IP addresses. If not found, returns (None, None).
    """
    # target_dictから名前のリストを作成
    target_names = [value['name'] for value in target_dict.values()]

    try:
        target_num = comparison_list.index("target")
        target_name = f"{comparison_list[target_num]} {comparison_list[target_num + 1]}"

        # comparison_listの各要素をチェック
        if target_name in target_names:
            # 一致する名前が見つかった場合、そのIPアドレスを返す
            for value in target_dict.values():
                if value['name'] == target_name:
                    return target_name, value['ip']
    except (ValueError, IndexError):
        pass  # Do nothing if an error occurs
    
    return None, None  # 一致するターゲットが見つからない場合


def listen_for_wakeup_phrase(vosk_asr):
    """Wait until the wake-up phrase is recognized.

    :param:vosk_asr (VoskStreamingASR): Voice Recognition Module
    """
    try:
        while True:
            recog_text = get_asr_result(vosk_asr)
            if recog_text:
                print(f"recognized text: {recog_text}")
                userOrder = recog_text
                if WAKEUP_PHRASE in userOrder:
                    print("Wakeup phrase recognition! Wait for next input.")
                    tts.say("Yes Boss")
                    listen_for_command(vosk_asr)  # ウェイクアップ後にコマンドを待機
    except KeyboardInterrupt:
        print("\nCtrl+C is pressed. Exit the program.")
        logging.info("System Shutdown")
        exit()

def listen_for_command(vosk_asr):
    """Waits for command input after wake-up.

    :param:vosk_asr (VoskStreamingASR): Voice Recognition Module
    """
    cmd_mgr = CommandManager(COMMANDS_PATH)
    command_map =cmd_mgr.get_command_map()

    ip_mgr = IPAddressManager(TARGETS_PATH)
    # target_dict = ip_mgr.load_targets()

    op_manager = OperationManager(SOP_PATH)
    # sop.jsonからオペレーション名のリストを取得
    valid_operations = set(op_manager.get_operation_names())

    try:
        print(f"Enter command (say '{EXIT_PHRASE}' to exit)")
        tts.say("Please give me some direction.")
        time.sleep(1)
        while True:
            # 音声認識結果を取得
            recog_text = get_asr_result(vosk_asr)
            if recog_text:
                print(f"recognized text: {recog_text}")
                userOrder = recog_text

                target_name, target_ip = find_target_ip(userOrder)

                if EXIT_PHRASE in userOrder:
                    print("Recognizes the exit phrase! Exit system.")
                    tts.say("Exit the system. Thank you.")
                    sys.exit(0)  # 終了フレーズが認識されたらプログラムを終了

                elif "introduce" in userOrder:
                    introduce(tts,lang_ja=0)
                    print("Wait for the wake-up phrase again.")
                    break  # ウェイクアップフレーズの待機に戻る
                
                # オペレーション名のチェックと実行処理
                elif "operation" in userOrder:
                    try:
                        operation_num = userOrder.index("operation")
                        operation_name = f"{userOrder[operation_num]} {userOrder[operation_num + 1]}"
                        
                        if operation_name in op_manager.get_operation_names():
                            if "describe" or "explain" in userOrder:
                                print(op_manager.get_operation_info(operation_name))
                            else:
                                print(f"'{operation_name}' has been recognized. Execute.")
                                # ここにオペレーション実行のコードを追加
                            break  # 最初に一致したオペレーションを処理した後ループを抜ける
                    except (ValueError, IndexError):
                        pass  # Do nothing if an error occurs

                elif ("scan" or "scanning") and "network" in userOrder:
                    netscan = NetworkScanner()
                    netscan.network_scan(tts, ip_mgr, lang_ja=0)
                    break

                elif "tell" and "me" and "target" in userOrder:
                    print(f"{target_name}: {target_ip}")
                    tts.say(f"{target_name}: {target_ip}")
                    break

                elif "command" in userOrder:
                    assist_command_mode(cmd_mgr, ip_mgr, vosk_asr, tts, command_map, lang_ja=0)
                    break

                else:
                    matching_items = set(userOrder) & set(cmd_mgr)
                    if matching_items:
                        logging.info(f"command execution: {recog_text}")
                        for matched_key in matching_items:
                            tts.say(f"Execute {matched_key}")
                            cmd_mgr.execute_command(matched_key, target_ip)
                    break  # ウェイクアップフレーズの待機に戻る
        print("Wait for wake-up phrase again.")

    except KeyboardInterrupt:
        print("\nCtrl+C is pressed. Exit the program.")
        logging.info("System Shutdown")
        exit()

def main():
    ascii_art = pyfiglet.figlet_format("Babbly", font="dos_rebel")
    print(ascii_art)

    logging.info("Program start")

    config = load_config("babbly/en/config_en.yaml")
    set_globals(config)
    logging.info("Configuration loading complete")

    # 音声認識を初期化
    vosk_asr = initialize_vosk_asr(MODEL_PATH)
    logging.info("Voice recognition function Initialization complete")

    tts.say(f"Artificial incompetence System , Babbly, activate")
    print("<Start speech recognition - waits for input>.")
    while True:
        listen_for_wakeup_phrase(vosk_asr)

if __name__ == '__main__':
    main()
