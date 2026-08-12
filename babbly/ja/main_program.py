#!/usr/bin/python3
import logging
import sys

import pyfiglet

from babbly.asr import create_asr
from babbly.ja.japanese_tts import Japanese_TTS
from babbly.modules.commands_manager import CommandManager
from babbly.modules.ipaddress_manager import IPAddressManager
from babbly.modules.network_scanner import NetworkScanner
from babbly.modules.operation_manager import OperationManager
from babbly.modules.utils import analyze_text, assist_command_mode, introduce, load_config, select_target
from babbly.nlu.japanese import IntentResolver, normalize_japanese


tts = Japanese_TTS()
lang_ja = 1
intent_resolver = IntentResolver()


def set_globals(config):
    global WAKEUP_PHRASE, EXIT_PHRASE, COMMANDS_PATH, TARGETS_PATH, SOP_PATH
    WAKEUP_PHRASE = config.get("WAKEUP_PHRASE")
    EXIT_PHRASE = config.get("EXIT_PHRASE")
    COMMANDS_PATH = config.get("COMMANDS_PATH")
    TARGETS_PATH = config.get("TARGETS_PATH")
    SOP_PATH = config.get("SOP_PATH")


def listen_text(asr):
    result = asr.listen()
    if result.is_empty:
        return ""
    confidence = "unknown" if result.confidence is None else f"{result.confidence:.2f}"
    logging.info("ASR backend=%s confidence=%s text=%s", result.backend, confidence, result.text)
    return result.text


def listen_for_wakeup_phrase(asr):
    try:
        while True:
            recog_text = listen_text(asr)
            if not recog_text:
                continue
            print(f"認識テキスト: {recog_text}")
            if normalize_japanese(WAKEUP_PHRASE) in normalize_japanese(recog_text):
                print("ウェイクアップフレーズ認識。次の入力を待機します。")
                tts.say("はい、ボス")
                listen_for_command(asr)
    except KeyboardInterrupt:
        print("\nCtrl+Cが押されました。プログラムを終了します。")
        logging.info("システム終了")
        raise SystemExit(0)


def listen_for_command(asr):
    cmd_mgr = CommandManager(COMMANDS_PATH)
    command_dict = cmd_mgr.get_search_dict()
    ip_mgr = IPAddressManager(TARGETS_PATH)
    op_mgr = OperationManager(SOP_PATH)

    try:
        print(f"コマンドを入力してください（終了するには {EXIT_PHRASE} を言ってください）")
        tts.say("指示をどうぞ")

        while True:
            recog_text = listen_text(asr)
            if not recog_text:
                continue

            print(f"認識テキスト: {recog_text}")
            intent = intent_resolver.resolve(recog_text)
            normalized = intent.normalized_text
            user_order = analyze_text(normalized)
            logging.info("intent=%s confidence=%.2f normalized=%s", intent.name, intent.confidence, normalized)

            if intent.name == "system.exit" or normalize_japanese(EXIT_PHRASE) in normalized:
                print("終了フレーズ認識。処理を終了します。")
                tts.say("システムを終了します。お疲れ様でした。")
                raise SystemExit(0)

            if intent.name == "system.introduce":
                introduce(tts, lang_ja)
                break

            if intent.name == "network.scan":
                NetworkScanner().network_scan(tts, ip_mgr, lang_ja)
                break

            if intent.name == "target.show":
                target_name, target_ip = ip_mgr.find_target_ip(user_order)
                if target_name:
                    print(f"{target_name}: {target_ip}")
                    tts.say(f"{target_name}: {target_ip}")
                else:
                    print("ターゲットが見つかりません")
                    tts.say("ターゲットが見つかりません")
                break

            if intent.name == "command.mode":
                assist_command_mode(cmd_mgr, ip_mgr, asr, tts, command_dict, lang_ja)
                break

            ipaddress = cmd_name = op_name = None
            cmd_arg = None
            for word in user_order:
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
                if ipaddress and (op_name or cmd_name):
                    break

            if op_name:
                if ipaddress is None:
                    ipaddress = select_target(ip_mgr, tts, asr, lang_ja)
                op_mgr.run_operation(op_name, ipaddress)
                break

            if cmd_name:
                if cmd_arg and not ipaddress:
                    ipaddress = select_target(ip_mgr, tts, asr, lang_ja)
                cmd_mgr.execute_command(cmd_name, ipaddress if cmd_arg else None)
                break

            tts.say("指示を特定できませんでした。もう一度お願いします")

        print("再度ウェイクアップフレーズを待機します。")
    except KeyboardInterrupt:
        print("\nCtrl+Cが押されました。プログラムを終了します。")
        logging.info("システム終了")
        raise SystemExit(0)


def main():
    ascii_art = pyfiglet.figlet_format("Babbly", font="dos_rebel")
    print(ascii_art)
    logging.info("プログラム開始")

    config = load_config("babbly/ja/config_ja.yaml")
    set_globals(config)
    logging.info("設定読み込み完了")

    asr = create_asr(config)
    logging.info("音声認識機能 初期化完了 backend=%s", config.get("ASR_BACKEND", "vosk"))

    print("＜音声認識開始 - 入力を待機します＞")
    tts.say("人工無能システム、バブリー、起動します。")
    while True:
        listen_for_wakeup_phrase(asr)


if __name__ == '__main__':
    main()
