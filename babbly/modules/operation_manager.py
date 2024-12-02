import json
import subprocess
import threading
import time
import uuid
from typing import List, Optional, Union


class OperationManager:
    """
    JSONファイルからオペレーションを読み込み、コマンドを実行するクラス。
    Attributes:
        operations (list): オペレーションの情報を格納するリスト。
    """
    
    TMUX_CMD = 'tmux'
    ENTER_KEY = 'C-m'
    LOG_DIR = './logs'  # ログファイルを保存するディレクトリ

    def __init__(self, json_file_path):
        """
        初期化メソッド。コマンドデータをロードし補助辞書を作成する。

        Args:
            json_file_path (str): コマンド定義ファイルのパス。
        """
        self.operations_map = self._load_data(json_file_path)
        self.search_dict = {}
        self._build_search_dict()

    def _load_data(self, file_path):
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
        for key, record in self.operations_map.items():
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


    def get_operation_values(self, search_key):
        """
        指定されたキー（コマンド名、ID、アルファベット、フォネティックコード）に対応する arg_flg の値を返す。

        Args:
            search_key (str): 検索するキー（コマンド名、ID、アルファベット、フォネティックコードなど）。

        Returns:
            str: 該当する項目のオペレーション名と説明
        """
        try:
            record = self.search_dict[search_key]
            return record["VoiceAlias"], record["Info"]
        except KeyError:
            return None,None


    def display_all_operations(self):
        """
        すべてのオペレーション情報を表示する。

        Returns:
            list: すべてのオペレーション情報を含む文字列のリスト。
        """
        operation_list = [
            f"{key}. {record['ID']}: {record['VoiceAlias']} {record['Info']}"
            for key, record in self.operations_map.items()
        ]

        # 表示
        for operation in operation_list:
            print(operation)

        return operation_list


###### ここから下　要修正 #########


    def _execute_commands(self, commands: List[str], target_ip: Optional[str] = None, tmux_window_name: Optional[str] = None):
        """
        コマンドリストを実行し、必要に応じて{target}をIPアドレスに置換する。
        コメント行（#で始まる行）は無視し、tmuxの新しいウィンドウで実行する。
        :param commands: 実行するコマンドのリスト
        :param target_ip: {target}に置換するIPアドレス。デフォルトはNone
        :param tmux_window_name: 実行するtmuxウィンドウの名前。デフォルトはNone
        """
        if tmux_window_name:
            subprocess.run([self.TMUX_CMD, 'new-window', '-d', '-n', tmux_window_name])
            log_file = f"{self.LOG_DIR}/{tmux_window_name}.log"
            subprocess.run([self.TMUX_CMD, 'pipe-pane', '-t', tmux_window_name, f'cat > {log_file}'])

        for command in commands:
            command = command.strip()
            if command.startswith('#') or not command:
                continue
            if '{target}' in command and not target_ip:
                print(f"エラー: '{command}' にはIPが必要です。")
                continue
            command = command.replace('{target}', target_ip or '')
            print(f"tmuxウィンドウ '{tmux_window_name}' で実行中: {command}")
            try:
                subprocess.run([self.TMUX_CMD, 'send-keys', '-t', tmux_window_name, command, self.ENTER_KEY])
            except subprocess.SubprocessError as e:
                print(f"コマンド '{command}' の実行中にエラーが発生しました: {e}")

    def run_operation(self, voice_alias: str, target_ip: Optional[str] = None):
        """
        指定されたVoiceAliasに基づき、対応するコマンドファイルを読み込んで実行する。
        新しいtmuxウィンドウで実行する。
        :param voice_alias: 実行するオペレーションの識別子
        :param target_ip: {target}に置換するIPアドレス。デフォルトはNone
        """
        operation = self._find_operation(voice_alias)
        if not operation:
            print(f"オペレーション '{voice_alias}' が見つかりません。")
            return
        file_path = operation.get('file')
        if not file_path:
            print(f"オペレーション '{voice_alias}' にファイルが定義されていません。")
            return
        try:
            with open(file_path, 'r') as file:
                commands = file.readlines()
            
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            unique_id = uuid.uuid4()
            tmux_window_name = f"{voice_alias}_{timestamp}_{unique_id}"
            
            command_thread = threading.Thread(target=self._execute_commands, args=(commands, target_ip, tmux_window_name))
            command_thread.start()
            command_thread.join()  # スレッドの終了を待機
        except FileNotFoundError:
            print(f"ファイル '{file_path}' が見つかりません。")

    # def get_operation_info(self, voice_alias: str) -> str:
    #     """
    #     指定されたVoiceAliasに対応するオペレーションの説明(info)を返す。
    #     :param voice_alias: 説明を取得したいオペレーションの識別子
    #     :return: オペレーションの説明(info)。該当がない場合はエラーメッセージ。
    #     """
    #     operation = self._find_operation(voice_alias)
    #     if not operation:
    #         return f"オペレーション '{voice_alias}' が見つかりません。"
    #     return operation.get('info', '説明がありません。')

    # def get_operation_names(self) -> List[str]:
    #     """
    #     sop.jsonに登録されているすべてのオペレーション名を返す。
    #     :return: list, オペレーション名のリスト
    #     """
    #     return [operation['VoiceAlias'] for operation in self.operations] if self.operations else []

    # def _find_operation(self, voice_alias: str) -> Optional[dict]:
    #     """VoiceAliasに対応するオペレーションを検索して返す。見つからない場合はNone"""
    #     return next((op for op in self.operations if op['VoiceAlias'] == voice_alias), None)


if __name__ == "__main__":
    manager = OperationManager('sop.json')

    # IPアドレスを渡して実行
    manager.run_operation("オペレーションアルファ", "127.0.0.1")

    # オペレーションの説明を取得
    info = manager.get_operation_info("オペレーションアルファ")
    print(info)

    # すべてのオペレーション名を表示
    operation_names = manager.get_operation_names()
    print("登録されているオペレーション名:", operation_names)