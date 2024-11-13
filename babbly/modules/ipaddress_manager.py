import json

class IPAddressManager:
    """
    IPアドレス管理クラス
    
    ターゲットの名前、キー、IPアドレスを管理し、
    JSONファイルからの読み込み、保存、IPアドレスの変更、
    特定のターゲットのIPアドレス取得機能を提供します。
    """

    def __init__(self, filename):
        """
        IPAddressManagerのコンストラクタ
        
        :param filename: ターゲット情報を含むJSONファイルの名前
        """
        self.filename = filename
        self.targets = self.load_targets()

    def load_targets(self):
        """
        JSONファイルからターゲット情報を読み込む
        
        :return: ターゲット情報を含む辞書
        """
        with open(self.filename, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return {item['ID']: {'name': item['VoiceAlias'], 'ip': item['IP']} for item in data}

    def save_targets(self):
        """
        ターゲット情報をJSONファイルに保存する
        """
        data = [{'VoiceAlias': value['name'], 'ID': key, 'IP': value['ip']} for key, value in self.targets.items()]
        with open(self.filename, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    def change_ip_address(self):
        """
        ユーザー入力に基づいてターゲットのIPアドレスを変更する
        """
        target_key = input("変更するターゲットを入力(a-z):")
        if target_key in self.targets:
            print(f"{self.targets[target_key]['name']}のipアドレスを変更します。")
            new_ip = input("ipアドレスを入力してください:")
            self.targets[target_key]['ip'] = new_ip
            self.save_targets()
            print(f"{self.targets[target_key]['name']}のipアドレスを変更しました。")
        else:
            print("指定されたターゲットが見つかりません。")

    def get_ip_address(self, input_text):
        """
        入力テキストに含まれるターゲット名に対応するIPアドレスを返す
        
        :param input_text: ターゲット名を含む入力テキスト
        :return: ターゲット名とIPアドレスを含む文字列、またはエラーメッセージ
        """
        if input_text is None:
            return "エラー: 入力がありません。"

        for key, value in self.targets.items():
            if value['name'] in input_text:
                return f"{value['name']}: {value['ip']}"
        return "指定されたターゲットが見つかりません。"


    def display_all_targets(self):
        """
        すべてのターゲットの名前とIPアドレスを表示する
        
        :return: すべてのターゲット情報を含む文字列のリスト
        """
        return [f"{value['name']}: {value['ip']}" for value in self.targets.values()]

    def register_ip_addresses(self, ip_addresses, overwrite=False):
        """
        複数のIPアドレスを一括で登録するメソッド

        :param ip_addresses: 登録するIPアドレスのリスト
        :param overwrite: True の場合、既存のIPアドレスを上書き。False の場合、IPアドレスが未設定のターゲットのみ更新
        """
        ip_index = 0
        for target_key, target_info in self.targets.items():
            if ip_index >= len(ip_addresses):
                break

            if overwrite or not target_info['ip']:
                self.targets[target_key]['ip'] = ip_addresses[ip_index]
                ip_index += 1

        self.save_targets()  # 変更を保存

    def clear_all_ip_addresses(self):
        """
        全てのターゲットのIPアドレスを消去するメソッド
        """
        for target in self.targets.values():
            target['ip'] = ""
        self.save_targets()
        print("全てのIPアドレスを消去しました。")

    def clear_specific_ip_address(self, target_identifier):
        """
        指定したターゲットのIPアドレスを消去するメソッド

        :param target_identifier: 消去するターゲットのID (a-z) または名前
        :return: 成功時はTrue、ターゲットが見つからない場合はFalse
        """
        target_key = None
        target_name = None

        # IDで検索
        if target_identifier in self.targets:
            target_key = target_identifier
            target_name = self.targets[target_key]['name']
        else:
            # 名前で検索
            for key, value in self.targets.items():
                if value['name'] == target_identifier:
                    target_key = key
                    target_name = target_identifier
                    break

        if target_key is not None:
            self.targets[target_key]['ip'] = ""
            self.save_targets()
            print(f"{target_name}のIPアドレスを消去しました。")
            return True
        else:
            print("指定されたターゲットが見つかりません。")
            return False


# 使用例
if __name__ == "__main__":
    # IPAddressManagerのインスタンスを作成
    manager = IPAddressManager("targets.json")

    # すべてのターゲットを表示
    all_targets = manager.display_all_targets()
    print("すべてのターゲット:")
    for target in all_targets:
        print(target)

    # IPアドレスの変更
    manager.change_ip_address()

    # 文字列入力によるIPアドレスの表示
    input_text = "ターゲットチャーリーのアドレスを教えて"
    result = manager.get_ip_address(input_text)
    print(result)

    # ホストディスカバリーで見つかったIPアドレスのリスト（例）
    discovered_ip_addresses = [
        "192.168.1.100",
        "192.168.1.101",
        "192.168.1.102",
        "192.168.1.103",
        "192.168.1.104"
    ]

    # 追加モードで登録（空のIPアドレスのみ更新）
    print("追加モードで登録:")
    manager.register_ip_addresses(discovered_ip_addresses, overwrite=False)

    # 現在のターゲット情報を表示
    print("\n現在のターゲット情報:")
    for target in manager.display_all_targets():
        print(target)

    # 上書きモードで登録（既存のIPアドレスも上書き）
    print("\n上書きモードで登録:")
    manager.register_ip_addresses(discovered_ip_addresses, overwrite=True)

    # 更新後のターゲット情報を表示
    print("\n更新後のターゲット情報:")
    for target in manager.display_all_targets():
        print(target)

    # 現在のターゲット情報を表示
    print("消去前のターゲット情報:")
    for target in manager.display_all_targets():
        print(target)

    # IDを使用してターゲットのIPアドレスを消去
    manager.clear_specific_ip_address("a")

    # 名前を使用してターゲットのIPアドレスを消去
    manager.clear_specific_ip_address("ターゲットブラボー")

    # 更新後のターゲット情報を表示
    print("\n消去後のターゲット情報:")
    for target in manager.display_all_targets():
        print(target)

    # 存在しないターゲットを指定した場合
    manager.clear_specific_ip_address("存在しないターゲット")