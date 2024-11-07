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

    def __init__(self, json_file: str):
        """
        初期化メソッド。JSONファイルからオペレーション情報を読み込む。
        :param json_file: 読み込むJSONファイルのパス
        """
        self.operations = self._load_operations(json_file)
    
    def _load_operations(self, json_file: str) -> Union[List[dict], None]:
        """JSONファイルからオペレーションを読み込む"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"エラー: JSONファイルの読み込みに失敗しました。{e}")
            return None

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

    def get_operation_info(self, voice_alias: str) -> str:
        """
        指定されたVoiceAliasに対応するオペレーションの説明(info)を返す。
        :param voice_alias: 説明を取得したいオペレーションの識別子
        :return: オペレーションの説明(info)。該当がない場合はエラーメッセージ。
        """
        operation = self._find_operation(voice_alias)
        if not operation:
            return f"オペレーション '{voice_alias}' が見つかりません。"
        return operation.get('info', '説明がありません。')

    def get_operation_names(self) -> List[str]:
        """
        sop.jsonに登録されているすべてのオペレーション名を返す。
        :return: list, オペレーション名のリスト
        """
        return [operation['VoiceAlias'] for operation in self.operations] if self.operations else []

    def _find_operation(self, voice_alias: str) -> Optional[dict]:
        """VoiceAliasに対応するオペレーションを検索して返す。見つからない場合はNone"""
        return next((op for op in self.operations if op['VoiceAlias'] == voice_alias), None)


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