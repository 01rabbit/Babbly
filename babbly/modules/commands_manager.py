import threading
import subprocess
import logging
from babbly.modules.utils import get_phonetic_mapping


class CommandManager:
    """コマンドの管理・実行を行うクラス。"""

    def __init__(self, command_file_path):
        """
        初期化メソッド。コマンドマップをロードする。
        
        Args:
            command_file_path (str): コマンド定義ファイルのパス。
        """
        self.command_map = self._load_commands(command_file_path)

    @staticmethod
    def _load_commands(file_path):
        """コマンド定義ファイルを読み込むメソッド。
        
        Args:
           file_path (str): コマンドファイルのパス。
        
        Returns:
           dict: キーとコマンド情報を格納した辞書。
        """
        command_map = {}
        with open(file_path, 'r') as file:
            # 1行目をスキップする
            next(file)
            for line in file:
                key, command, arg_flg = line.strip().split(',')
                command_map[key] = {'command': command, 'arg_flg': int(arg_flg)}
        return command_map

    def get_command_map(self):
        """現在のコマンドマップを返すメソッド。
        
        Returns:
            dict: 現在ロードされているコマンドマップ。
        """
        return self.command_map

    def execute_command(self, matched_key, target_ip=None):
        """
        コマンド情報を取得し、スレッドでアクションを実行する。
        
        Args:
            matched_key (str): コマンドマップ内のキー。
            target_ip (str, optional): プレースホルダを置き換えるためのターゲットIP。デフォルトはNone。
        """
        try:
            # コマンド情報を取得
            command_info = self.command_map[matched_key]
            command = command_info['command']
            arg_flg = command_info.get('arg_flg', 0)  # デフォルト値は 0

            # 引数フラグが1のときにtarget_ipが指定されていない場合のチェック
            if arg_flg == 1 and not target_ip:
                raise ValueError("引数フラグが1の場合、target_ipを指定する必要があります。")

            # 引数フラグに基づきスレッドを作成
            if arg_flg == 1:
                action_thread = threading.Thread(target=self._perform_action, args=(command, target_ip))
            else:
                action_thread = threading.Thread(target=self._perform_action, args=(command,))

            # スレッドを開始
            action_thread.start()

        except KeyError:
            logging.error(f"Error: The key '{matched_key}' does not exist in the command map.")
        except ValueError as e:
            logging.error(f"Error: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")

    @staticmethod
    def _perform_action(command, target_ip=None):
        """コマンドに基づいて処理を実行するメソッド。
        
        Args:
            command (str): 実行するコマンド。
            target_ip (str, optional): コマンド内で使用するターゲットIP。デフォルトはNone。
        """
        try:
            # コマンド内のプレースホルダ `{target_ip}` を置き換える
            if target_ip:
                command = command.format(target_ip=target_ip)

            # コマンドを実行し、結果を取得
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # 実行結果を出力
            print(f"Execution result of the command:\n {result.stdout}")
        except subprocess.CalledProcessError as e:
            # エラー時の処理
            logging.error(f"コマンドの実行中にエラーが発生しました: {e.stderr}")

    def display_command_list(self):
        """コマンドマップをアルファベット付きで一覧表示する。"""
        print("コマンド一覧:")
        for index, (key, value) in enumerate(self.command_map.items(), start=0):
            print(f"{chr(97 + index)}. {key}: {value['command']}")


    def select_command_by_voice(self, user_input):
        """音声認識を使ってコマンドを選択し、対応するコマンドを実行する。"""
        # フォネティックコードのマッピングを取得
        phonetic_mapping = get_phonetic_mapping()

        # 音声入力をアルファベットにマッピング
        selected_key = phonetic_mapping.get(user_input)
        if selected_key:
            # 対応するコマンドを取得して実行
            matched_key = list(self.command_map.keys())[ord(selected_key) - 97]
            # print(f"選択されたコマンド: {matched_key}")
            self.execute_command(matched_key)
        else:
            logging.error("An unrecognized command was specified.")
