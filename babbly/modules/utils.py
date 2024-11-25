#!/usr/bin/python3
import yaml
import logging
from janome.analyzer import Analyzer
from janome.tokenfilter import CompoundNounFilter
from babbly.ja.vosk_asr_module import get_asr_result as get_asr_result_ja
from babbly.en.vosk_asr_module import get_asr_result as get_asr_result_en

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

def load_config(file_path):
    """Read the configuration file"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

def get_phonetic_mapping():
    """Generate a mapping of phonetic codes (Japanese and English) to corresponding alphabets."""
    phonetic_codes_ja = [
        "アルファ", "ブラボー", "チャーリー", "デルタ", "エコー", "フォックストロット",
        "ゴルフ", "ホテル", "インディア", "ジュリエット", "キロ", "リマ", "マイク",
        "ノーベンバー", "オスカー", "パパ", "ケベック", "ロメオ", "シエラ",
        "タンゴ", "ユニフォーム", "ビクター", "ウイスキー", "エックスレイ", "ヤンキー", "ズールー"
    ]

    phonetic_codes_en = [
        "Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot",
        "Golf", "Hotel", "India", "Juliett", "Kilo", "Lima", "Mike",
        "November", "Oscar", "Papa", "Quebec", "Romeo", "Sierra",
        "Tango", "Uniform", "Victor", "Whiskey", "X-ray", "Yankee", "Zulu"
    ]

    mapping = {code: chr(97 + index) for index, code in enumerate(phonetic_codes_ja)}
    mapping.update({code.lower(): chr(97 + index) for index, code in enumerate(phonetic_codes_en)})

    return mapping


def assist_command_mode(cmd_mgr, ip_mgr, vosk_asr, tts, command_map, lang_ja):
    """
    コマンドアシストモードを実行する関数。

    Args:
        cmd_mgr (CommandManager): コマンドの管理を行うインスタンス。
        ip_mgr (IPAddressManager): IPアドレスの管理を行うインスタンス。
        vosk_asr (vosk_asr_module): VOSK音声認識モデルのインスタンス。
        tts (TextToSpeech): テキスト読み上げ機能のインスタンス。
        command_map (dict): 実行可能なコマンドとその引数情報を格納した辞書。
        lang_ja: 日本語かどうか
    Returns:
        None
    """
    if lang_ja:
        logging.info("コマンドアシストモードが有効になりました")
        tts.say("コマンドの一覧を表示します")
    else:
        logging.info("Command Assist Mode is now active")
        tts.say("コマンドの一覧を表示します")

    cmd_mgr.display_command_list()

    if lang_ja:
        tts.say("実行するコマンドを選択してください")
        cmd_name = get_asr_result_ja(vosk_asr)
        print(f"認識テキスト: {cmd_name}")
    else:
        tts.say("Please select the command to execute.")
        cmd_name = get_asr_result_en(vosk_asr)
        print(f"recognized text: {cmd_name}")

    if cmd_name in command_map:
        if command_map[cmd_name]['arg_flg']:
            target_ip = select_target(ip_mgr, tts, vosk_asr, lang_ja)
            if target_ip:
                cmd_mgr.execute_command(cmd_name, target_ip)
            else:
                logging.error("Target not found.")
        else:
            cmd_mgr.execute_command(cmd_name)
    else:
        logging.error(f"Command not found.")


def select_target(ip_mgr, tts, vosk_asr, lang_ja):
    """ターゲット選択処理"""
    if lang_ja:
        tts.say("ターゲットの一覧を表示します")
    else:
        tts.say("Displaying the list of targets.")

    ip_mgr.display_all_targets()

    if lang_ja:
        tts.say("ターゲットを選択してください")
        target_name = get_asr_result_ja(vosk_asr)
        print(f"認識テキスト: {target_name}")
    else:
        tts.say("Please select a target.")
        target_name = get_asr_result_en(vosk_asr)
        print(f"recognized text:  {target_name}")

    return ip_mgr.get_ip_address(target_name)

def introduce(tts, lang_ja):
    if lang_ja:
        print("自己紹介をします")
        message = f"私はバブリー。ミスターラビットによって開発された人工無能システムです"
        tts.say(message)
        message = "私の役割は、ペネトレーションテストにおいて、あなたをサポートすることです"
        tts.say(message)
    else:
        print("Self Introductions.")
        message = f"I am Babbly. I am an artificial incompetence system developed by Mr.Rabbit."
        tts.say(message)
        message = "My role is to support you effectively in penetration testing."
        tts.say(message)

