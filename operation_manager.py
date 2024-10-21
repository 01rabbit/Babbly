import json
import subprocess
import threading
import time  # タイムスタンプを生成するために追加


class OperationManager:
    """
    sop.jsonからオペレーションを読み込み、コマンドを実行するクラス。
    
    Attributes:
        operations (list): オペレーションの情報を格納するリスト。
    """

    def __init__(self, json_file):
        """
        初期化メソッド。JSONファイルからオペレーション情報を読み込む。

        :param json_file: 読み込むJSONファイルのパス
        """
        with open(json_file, 'r', encoding='utf-8') as f:
            self.operations = json.load(f)  # JSONをリストとして読み込む

    def _execute_commands(self, commands, target_ip=None, tmux_window_name=None):
        """
        コマンドリストを実行し、必要に応じて{target}をIPアドレスに置換する。

        コメント行（#で始まる行）は無視。tmuxの新しいウィンドウで実行する。

        :param commands: 実行するコマンドのリスト
        :param target_ip: {target}に置換するIPアドレス。デフォルトはNone
        :param tmux_window_name: 実行するtmuxウィンドウの名前。デフォルトはNone
        """
        # 新しいtmuxウィンドウをバックグラウンドで作成 (-d オプションを使用)
        if tmux_window_name:
            subprocess.run(['tmux', 'new-window', '-d', '-n', tmux_window_name])

        for command in commands:
            command = command.strip()
            if command.startswith('#') or not command:
                # コメント行や空行はスキップ
                continue
            if '{target}' in command and not target_ip:
                print(f"エラー: '{command}' にはIPが必要です。")
                continue
            command = command.replace('{target}', target_ip or '')
            print(f"tmuxウィンドウ '{tmux_window_name}' で実行中: {command}")
            # tmuxウィンドウ内でコマンドを実行
            subprocess.run(['tmux', 'send-keys', '-t', tmux_window_name, command, 'C-m'])

    def run_operation(self, voice_alias, target_ip=None):
        """
        指定されたVoiceAliasに基づき、対応するコマンドファイルを読み込んで実行する。
        新しいtmuxウィンドウで実行（元のウィンドウには遷移しない）。

        :param voice_alias: 実行するオペレーションの識別子
        :param target_ip: {target}に置換するIPアドレス。デフォルトはNone
        """
        operation = next((op for op in self.operations if op['VoiceAlias'] == voice_alias), None)
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
            
            # タイムスタンプを使用して一意のウィンドウ名を生成
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            tmux_window_name = f"{voice_alias}_{timestamp}"
            
            # コマンド実行をスレッド化
            command_thread = threading.Thread(target=self._execute_commands, args=(commands, target_ip, tmux_window_name))
            command_thread.start()
        except FileNotFoundError:
            print(f"ファイル '{file_path}' が見つかりません。")

    def get_operation_info(self, voice_alias):
        """
        指定されたVoiceAliasに対応するオペレーションの説明(info)を返す。

        :param voice_alias: 説明を取得したいオペレーションの識別子
        :return: オペレーションの説明(info)。該当がない場合はエラーメッセージ。
        """
        operation = next((op for op in self.operations if op['VoiceAlias'] == voice_alias), None)
        if not operation:
            return f"オペレーション '{voice_alias}' が見つかりません。"
        return operation.get('info', '説明がありません。')

    def get_operation_names(self):
        """
        sop.jsonに登録されているすべてのオペレーション名を返す。

        :return: list, オペレーション名のリスト
        """
        return [operation['VoiceAlias'] for operation in self.operations]

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
