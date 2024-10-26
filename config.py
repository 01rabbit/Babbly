#!/usr/bin/python3
import os
import re
from configparser import ConfigParser
from typing import Callable, Dict, List

def read_config(filename: str, section: str) -> Dict[str, str]:
    """
    指定された設定ファイルから指定されたセクションの設定を読み取ります。
    """
    parser = ConfigParser()
    filepath = os.path.join(os.path.dirname(__file__), filename)
    parser.read(filepath, encoding='utf-8')
    
    if not parser.has_section(section):
        raise ValueError(f'Section "{section}" not found in the {filename} file')
    
    return dict(parser.items(section))

def get_service_config(service_name: str) -> Dict[str, str]:
    """
    指定されたサービスの設定を取得します。
    """
    config_file = os.getenv("CONFIG_FILE", "service.ini")
    return read_config(config_file, service_name)

def mask_sensitive_info(value: str) -> str:
    """
    パスワードやトークンなどの機密情報をマスクします。
    """
    return value[:3] + '*' * (len(value) - 3) if len(value) > 3 else '***'

def test_service_config(service_name: str, config_getter: Callable[[], Dict[str, str]]):
    """
    機密情報をマスクしてサービス設定をテストおよび表示します。
    """
    print(f"\n=== {service_name} Configuration Test ===")
    try:
        config = config_getter()
        print(f"Successfully loaded {service_name} configuration:")
        for key, value in config.items():
            masked_value = mask_sensitive_info(value) if 'password' in key.lower() or 'token' in key.lower() else value
            print(f"  {key}: {masked_value}")
    except Exception as e:
        print(f"Error loading {service_name} configuration: {e}")

def validate_url(url: str) -> bool:
    """
    正規表現を使用してURLの形式を検証します。
    """
    url_regex = re.compile(r'^(http|https)://')
    return bool(url_regex.match(url))

def validate_config(config: Dict[str, str], service_name: str) -> List[str]:
    """
    各サービスのバリデーションルールに従って設定を検証します。
    """
    validation_rules = {
        'mattermost': {
            'required': ['bot_token', 'channel_id', 'mm_api_address'],
            'url_keys': ['mm_api_address', 'bocchi_server']
        },
        # 他のサービスのバリデーションルールは必要に応じて追加
    }
    
    errors = []
    service_rules = validation_rules.get(service_name.lower(), {})
    
    for param in service_rules.get('required', []):
        if param not in config:
            errors.append(f"Missing required parameter: {param}")
    
    for url_key in service_rules.get('url_keys', []):
        if url_key in config and not validate_url(config[url_key]):
            errors.append(f"Invalid URL format: {config[url_key]}")
    
    return errors

# 他のコードからインポート可能な関数
def load_and_validate_service_config(service_name: str) -> List[str]:
    """
    指定したサービスの設定を読み込み、バリデーションエラーを返します。
    他のコードからインポートして利用できる関数です。
    """
    config = get_service_config(service_name)
    errors = validate_config(config, service_name)
    return errors

# 検証用のコード（メイン関数として動作）
if __name__ == '__main__':
    # 設定ファイルの存在確認
    config_file = os.getenv("CONFIG_FILE", "service.ini")
    config_path = os.path.join(os.path.dirname(__file__), config_file)
    
    print(f"Checking configuration file: {config_path}")
    if not os.path.exists(config_path):
        print(f"Warning: Configuration file {config_file} not found!")
        exit(1)
    
    print(f"Configuration file {config_file} found.")
        
    # 検証用のmattermost設定のテスト
    service_name = 'mattermost'
    print(f"\nTesting configuration for service: {service_name}")
    test_service_config(service_name, lambda: get_service_config(service_name))
    
    try:
        config = get_service_config(service_name)
        errors = validate_config(config, service_name)
        if errors:
            print(f"\nValidation errors for {service_name}:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("\nAll validation checks passed for mattermost.")
    except Exception as e:
        print(f"\nError validating {service_name} configuration: {e}")