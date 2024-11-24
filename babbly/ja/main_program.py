#!/usr/bin/python3
import sys
import logging
import pyfiglet
from janome.analyzer import Analyzer
from janome.tokenfilter import CompoundNounFilter
from babbly.ja.vosk_asr_module import initialize_vosk_asr, get_asr_result
from babbly.ja.japanese_tts import Japanese_TTS
from babbly.modules.ipaddress_manager import IPAddressManager
from babbly.modules.operation_manager import OperationManager
from babbly.modules.network_scanner import NetworkScanner
from babbly.modules.utils import load_config, assist_command_mode
from babbly.modules.commands_manager import CommandManager

tts = Japanese_TTS()

# グローバル変数に代入する関数
def set_globals(config):
    global WAKEUP_PHRASE, EXIT_PHRASE, COMMANDS_PATH, TARGETS_PATH, SOP_PATH, MODEL_PATH
    WAKEUP_PHRASE = config.get("WAKEUP_PHRASE")
    EXIT_PHRASE = config.get("EXIT_PHRASE")
    COMMANDS_PATH = config.get("COMMANDS_PATH")
    TARGETS_PATH = config.get("TARGETS_PATH")
    SOP_PATH = config.get("SOP_PATH")
    MODEL_PATH = config.get("MODEL_PATH")

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
    cmd_manager = CommandManager(COMMANDS_PATH)
    command_map =cmd_manager.get_command_map()

    ip_manager = IPAddressManager(TARGETS_PATH)
    # target_dict = ip_manager.load_targets()

    op_manager = OperationManager(SOP_PATH)
    valid_operations = set(op_manager.get_operation_names())

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

                target_name, target_ip = ip_manager.find_target_ip(userOrder)

                if EXIT_PHRASE in userOrder:
                    print("終了フレーズ認識！処理を終了します。")
                    tts.say("システムを終了します。お疲れ様でした。")
                    sys.exit(0)  # 終了フレーズが認識されたらプログラムを終了

                elif "自己紹介" in userOrder:
                    print("自己紹介をします")
                    message = f"私は{WAKEUP_PHRASE}。ミスターラビットによって開発された人工無能です"
                    tts.say(message)
                    message = "私の役割は、ペネトレーションテストにおいて、あなたを効果的にサポートすることです"
                    tts.say(message)
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

                elif "ネットワーク" and "スキャン" in userOrder:
                    netscan = NetworkScanner()
                    local_ip, netmask = netscan.get_local_ip_and_netmask()
                    if not local_ip or not netmask:
                        logging.error("Could not retrieve local IP or netmask.")
                        return
                    network = netscan.get_network_address(local_ip, netmask)
                    tts.say("ネットワークをスキャンします")
                    discovered_hosts = netscan.discover_hosts(network)
                    for host, status in discovered_hosts:
                        logging.info(f"Host: {host}, Status: {status}")
                    tts.say(f"{str(len(discovered_hosts))}個のホストを発見")
                    # discovered_hostsからIPアドレスを抽出
                    ip_addresses = [host[0] for host in discovered_hosts]
                    ip_manager.register_ip_addresses(ip_addresses, True)
                    break

                elif "ターゲット" and ("教える" or "表示") in userOrder:
                    print(f"{target_name}: {target_ip}")
                    tts.say(f"{target_name}: {target_ip}")
                    break

                elif "コマンド" in userOrder:
                    assist_command_mode(cmd_manager, ip_manager, vosk_asr, tts, command_map,lang_ja=1)
                    break

                else:
                    matching_items = set(userOrder) & set(command_map)
                    if matching_items:
                        logging.info(f"コマンド実行: {recog_text}")
                        for matched_key in matching_items:
                            tts.say(f"{matched_key}を実行します")
                            cmd_manager.execute_command(matched_key, target_ip)
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

    tts.say(f"人工無能システム、バブリー、起動します。")
    print("＜音声認識開始 - 入力を待機します＞")
    while True:
        listen_for_wakeup_phrase(vosk_asr)

if __name__ == '__main__':
    main()
