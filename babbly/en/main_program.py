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
from babbly.modules.utils import load_config, assist_command_mode, select_target, introduce
from babbly.modules.commands_manager import CommandManager

tts = English_TTS()
lang_ja = 0

def set_globals(config):
    global WAKEUP_PHRASE, EXIT_PHRASE, COMMANDS_PATH, TARGETS_PATH, SOP_PATH, MODEL_PATH
    WAKEUP_PHRASE = config.get("WAKEUP_PHRASE")
    EXIT_PHRASE = config.get("EXIT_PHRASE")
    COMMANDS_PATH = config.get("COMMANDS_PATH")
    TARGETS_PATH = config.get("TARGETS_PATH")
    SOP_PATH = config.get("SOP_PATH")
    MODEL_PATH = config.get("MODEL_PATH")


def merge_target_with_next(array, target):
    """
    Merges 'target' with the next element in the list if it exists.
    Returns the list unchanged if 'target' is missing or has no next element.
    """
    if target in array:
        index = array.index(target)
        if index < len(array) - 1:  # Check if a next element exists
            array[index] = array[index] + " " + array[index + 1]
            array.pop(index + 1)
    return array


def listen_for_wakeup_phrase(vosk_asr):
    """Wait until the wake-up phrase is recognized.

    :param:vosk_asr (VoskStreamingASR): Voice Recognition Module
    """
    try:
        while True:
            recog_text = get_asr_result(vosk_asr)
            if recog_text:
                print(f"recognized text: {recog_text}")
                recog_text = merge_target_with_next(recog_text, "target")
                userOrder = merge_target_with_next(recog_text, "operation")
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
    command_dict = cmd_mgr.get_search_dict()

    ip_mgr = IPAddressManager(TARGETS_PATH)
    target_dict = ip_mgr.get_search_dict()

    op_mgr = OperationManager(SOP_PATH)
    operation_dict = op_mgr.get_search_dict()

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


                if EXIT_PHRASE in userOrder:
                    print("Recognizes the exit phrase! Exit system.")
                    tts.say("Exit the system. Thank you.")
                    sys.exit(0)  # 終了フレーズが認識されたらプログラムを終了

                elif "introduce" in userOrder:
                    introduce(tts,lang_ja=0)
                    print("Wait for the wake-up phrase again.")
                    break  # ウェイクアップフレーズの待機に戻る


                elif ("scan" or "scanning") and "network" in userOrder:
                    netscan = NetworkScanner()
                    netscan.network_scan(tts, ip_mgr, lang_ja=0)
                    break

                elif "tell" and "me" and "target" in userOrder:
                    target_name, target_ip = ip_mgr.find_target_ip(userOrder)
                    if target_name:
                        print(f"{target_name}: {target_ip}")
                        tts.say(f"{target_name}: {target_ip}")
                    else:
                        print(f"{target_name} not found")
                    break

                elif "command" in userOrder:
                    assist_command_mode(cmd_mgr, ip_mgr, vosk_asr, tts, command_dict, lang_ja)
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
