#!/usr/bin/python3
import os
from configparser import ConfigParser

def read_config(filename, section):
    """
    指定された設定ファイルから指定されたセクションの設定を読み取るメソッド。
    Parameters:
        filename (str): 設定ファイルのパス
        section (str): 読み取るセクションの名前
    Returns:
        dict: セクション内の設定項目と値を含むディクショナリ
    """
    parser = ConfigParser()
    filepath = os.path.join(os.path.dirname(__file__), filename)
    parser.read(filepath, encoding='utf-8')
    
    if not parser.has_section(section):
        raise Exception(f'Section {section} not found in the {filename} file')
    
    return dict(parser.items(section))

def get_service_config(service_name):
    """
    サービス名に基づいて設定を読み取る共通関数
    Parameters:
        service_name (str): サービスの名前
    Returns:
        dict: サービスの設定
    """
    return read_config('service.ini', service_name)

# 各サービスの設定を取得する関数
matter_conf = lambda: get_service_config('mattermost')
faraday_conf = lambda: get_service_config('faraday')
gvm_conf = lambda: get_service_config('gvm')
brutespray_conf = lambda: get_service_config('brutespray')

if __name__ == '__main__':
    # テスト用のコード
    try:
        print("Mattermost config:", matter_conf())
    except Exception as e:
        print(f"Error: {e}")