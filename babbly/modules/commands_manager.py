import threading
import subprocess
import logging
import json


class CommandManager:
    """コマンドの管理・検索・実行を行うクラス。"""

    def __init__(self, json_file_path):
        """
        初期化メソッド。コマンドデータをロードし補助辞書を作成する。

        Args:
            json_file_path (str): コマンド定義ファイルのパス。
        """
        self.command_map = self._load_commands(json_file_path)
        self.search_dict = {}
        self._build_search_dict()

    def _load_commands(self, file_path):
        """JSONファイルからコマンドデータをロードする。

        Args:
            file_path (str): JSONファイルのパス。

        Returns:
            dict: コマンドデータ。
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            raise Exception(f"JSONファイル '{file_path}' が見つかりません。")
        except json.JSONDecodeError:
            raise Exception(f"JSONファイル '{file_path}' の形式が不正です。")


    def _build_search_dict(self):
        """補助辞書を作成する。"""
        phonetic_codes = {
            "a": ["alpha", "アルファ"],
            "b": ["bravo", "ブラボー"],
            "c": ["charlie", "チャーリー"],
            "d": ["delta", "デルタ"],
            "e": ["echo", "エコー"],
            "f": ["foxtrot", "フォックスロット"],
            "g": ["golf", "ゴルフ"],
            "h": ["hotel", "ホテル"],
            "i": ["india", "インディア"],
            "j": ["juliet", "ジュリエット"]
        }

        # 補助辞書作成
        for key, record in self.command_map.items():
            # 通常キーの登録
            self.search_dict[key] = record
            self.search_dict[record["ID"]] = record
            self.search_dict[record["VoiceAlias"]] = record

            # ID をキーにフォネティックコードを登録
            phonetic_entries = phonetic_codes.get(record["ID"])
            if phonetic_entries:
                for code in phonetic_entries:
                    self.search_dict[code.lower()] = record  # 小文字で登録


    def get_search_dict(self):
        return self.search_dict


    def get_command_values(self, search_key):
        """
        指定されたキー（コマンド名、ID、アルファベット、フォネティックコード）に対応する arg_flg の値を返す。

        Args:
            search_key (str): 検索するキー（コマンド名、ID、アルファベット、フォネティックコードなど）。

        Returns:
            str,int: 該当する項目のコマンド名と arg_flg 値。
        """
        try:
            record = self.search_dict[search_key]
            return record["VoiceAlias"], record["Arg_flg"]
        except KeyError:
            return None,None

    def display_all_commands(self):
        """
        すべてのコマンド情報を表示する。

        Returns:
            list: すべてのコマンド情報を含む文字列のリスト。
        """
        command_list = [
            f"{key}. {record['ID']}: {record['VoiceAlias']} {record['Command']}"
            for key, record in self.command_map.items()
        ]

        # 表示
        for command in command_list:
            print(command)

        return command_list


    def execute_command(self, matched_key, target_ip=None):
        """
        コマンド情報を取得し、スレッドでアクションを実行する。
        
        Args:
            matched_key (str): 番号、ID、またはVoiceAlias。
            target_ip (str, optional): プレースホルダを置き換えるためのターゲットIP。デフォルトはNone。
        """
        try:
            # 直接 command_map からコマンド情報を検索
            command_info = self.search_dict.get(matched_key)
            if not command_info:  # コマンド情報が見つからない場合のエラー
                raise KeyError(f"指定されたキー '{matched_key}' に対応するコマンドが見つかりません。")
            
            command = command_info["Command"]
            arg_flg = command_info["Arg_flg"]

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

        except KeyError as e:
            logging.error(f"Error: {e}")
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


if __name__ == "__main__":
    manager = CommandManager("babbly/ja/commands.json")
    command_dict = manager.get_search_dict()
    userOrder ={'ターゲットアルファ', 'に対して', 'テスト', 'を', '実行'}

