#!/usr/bin/python3
import os
from configparser import ConfigParser
from typing import Dict

def read_config(filename: str, section: str) -> Dict[str, str]:
    """
    指定された設定ファイルから指定されたセクションの設定を読み取ります。
    """
    parser = ConfigParser()
    parser.read(filename, encoding='utf-8')
    
    if not parser.has_section(section):
        raise ValueError(f'Section "{section}" not found in the {filename} file')
    
    return dict(parser.items(section))

def get_service_config(service_name: str) -> Dict[str, str]:
    """
    指定されたサービスの設定を取得します。
    """
    config_file = os.getenv("CONFIG_FILE", "service.ini")
    return read_config(config_file, service_name)

def test_service_config(service_name: str):
    """
    サービス設定を表示します。
    """
    try:
        config = get_service_config(service_name)
        print(f"\n=== {service_name} Configuration ===")
        for key, value in config.items():
            print(f"{key}: {value}")
    except Exception as e:
        print(f"Error loading {service_name} configuration: {e}")

if __name__ == '__main__':
    # 検証用のmattermost設定のテスト
    test_service_config('mattermost')
