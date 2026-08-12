#!/usr/bin/python3
import yaml
import logging
from janome.analyzer import Analyzer
from janome.tokenfilter import CompoundNounFilter
from babbly.ja.vosk_asr_module import get_asr_result as get_asr_result_ja
from babbly.en.vosk_asr_module import get_asr_result as get_asr_result_en


def analyze_text(message):
    """受け取った文字列を形態素解析する"""
    messages = []
    a = Analyzer(token_filters=[CompoundNounFilter()])
    for token in a.analyze(message):
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


def listen_text(asr, lang_ja=True):
    """Return one recognized utterance from either the new ASR interface or legacy Vosk."""
    if hasattr(asr, "listen"):
        result = asr.listen()
        return result.text if hasattr(result, "text") else str(result)
    return get_asr_result_ja(asr) if lang_ja else get_asr_result_en(asr)


def assist_command_mode(cmd_mgr, ip_mgr, asr, tts, search_dict, lang_ja):
    if lang_ja:
        logging.info("コマンドアシストモードが有効になりました")
        tts.say("コマンドの一覧を表示します")
    else:
        logging.info("Command Assist Mode is now active")
        tts.say("Displaying the command list")

    cmd_mgr.display_all_commands()
    tts.say("実行するコマンドを選択してください" if lang_ja else "Please select the command to execute.")
    result = listen_text(asr, bool(lang_ja))
    print(f"認識テキスト: {result}" if lang_ja else f"recognized text: {result}")

    cmd_name, cmd_arg_flg = cmd_mgr.get_command_values(result)
    if cmd_name is not None:
        if cmd_arg_flg:
            target_ip = select_target(ip_mgr, tts, asr, lang_ja)
            if target_ip is not None:
                cmd_mgr.execute_command(cmd_name, target_ip)
            else:
                logging.error("Target not found.")
        else:
            cmd_mgr.execute_command(cmd_name)


def select_target(ip_mgr, tts, asr, lang_ja):
    tts.say("ターゲットの一覧を表示します" if lang_ja else "Displaying the list of targets.")
    ip_mgr.display_all_targets()
    tts.say("ターゲットを選択してください" if lang_ja else "Please select a target.")
    target_name = listen_text(asr, bool(lang_ja))
    print(f"認識テキスト: {target_name}" if lang_ja else f"recognized text: {target_name}")
    _, ipaddress = ip_mgr.find_target_ip(target_name)
    return ipaddress


def introduce(tts, lang_ja):
    if lang_ja:
        print("自己紹介をします")
        tts.say("私はバブリー。ミスターラビットによって開発された人工無能システムです")
        tts.say("私の役割は、ペネトレーションテストにおいて、あなたをサポートすることです")
    else:
        print("Self Introductions.")
        tts.say("I am Babbly. I am an artificial incompetence system developed by Mr.Rabbit.")
        tts.say("My role is to support you effectively in penetration testing.")
