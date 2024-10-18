import readline  # オートコンプリートのためのモジュール
from cmd import Cmd
import subprocess
from asr_streaming import *
from speech import speak_text_aloud
import os

BLACK = '\033[1;30m'
RED = '\033[1;31m'
GREEN = '\033[1;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[1;34m'
PURPLE = '\033[1;35m'
LIGHTBLUE = '\033[1;36m'
WHITE = '\033[1;37m'
END = '\033[0m'
readline.parse_and_bind("tab: complete")

class CustomShell(Cmd):
    intro = "ユーザーフレンドリーなCUIデモ"  # スタートメッセージ
    prompt = f"{RED}(デモ) {GREEN}{os.getcwd()}{END} > "  # プロンプト

    def __init__(self):
        Cmd.__init__(self)

    def do_test(self, arg):
        """テストコマンド"""
        print(f"テストが実行されました。引数: {arg}")

    def do_exit(self, arg):
        """終了コマンド"""
        print("プログラムを終了します。")
        return True

    def do_bocchi(self,arg):
        """音声入力"""
        result = transcribe_audio_stream()
        print(result)

    def do_hoge(self, arg):
        """hoge"""
        print("do anything")

    def help_hoge(self):
        """hoge help"""
        print("help : hoge")

    def do_hoge2(self, arg):
        """hoge2"""
        print("do anything 2")

    def help_hoge2(self):
        """hoge2 help"""
        print("help : hoge2")

    def do_cd(self, arg):
        """カレントディレクトリの変更"""
        try:
            if not arg:
                arg = os.path.expanduser('~')  # 引数がない場合はホームディレクトリに戻る
            os.chdir(arg)
            self.prompt = f"{RED}(デモ) {GREEN}{os.getcwd()}{END} > "
        except FileNotFoundError:
            print(f"ディレクトリが見つかりません: {arg}")
        except Exception as e:
            print(f"エラーが発生しました: {e}")

    def do_scan(self, arg):
        """nmapを使ったサンプル"""
        if not arg:
            print("引数が必要です。例: scan 192.168.1.1")
            return

        ip_address = arg
        try:
            # nmapの一部として、指定されたIPアドレスをスキャン
            result = subprocess.run(['nmap', '-p-', ip_address], capture_output=True, text=True)
            print(result.stdout)
        except Exception as e:
            print(f"エラーが発生しました: {e}")

    def do_EOF(self, arg):
        return True;

    # 入力が空に対するオーバーライド
    def emptyline(self):
        pass

    def default(self, line):
            """Run the given command as a system command."""
            try:
                subprocess.run(line, shell=True, check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error executing command: {e}")
if __name__ == "__main__":
    
    try:
        CustomShell().cmdloop() 
    except KeyboardInterrupt: # キーボードによる割り込み
        print('\nKeyboard Interrupt (Ctrl+C)')
        pass
    except:
        pass