import csv

class IPAddressManager:
    """
    IPアドレス管理クラス
    
    ターゲットの名前、キー、IPアドレスを管理し、
    CSVファイルからの読み込み、保存、IPアドレスの変更、
    特定のターゲットのIPアドレス取得機能を提供します。
    """

    def __init__(self, filename):
        """
        IPAddressManagerのコンストラクタ
        
        :param filename: ターゲット情報を含むCSVファイルの名前
        """
        self.filename = filename
        self.targets = self.load_targets()

    def load_targets(self):
        """
        CSVファイルからターゲット情報を読み込む
        
        :return: ターゲット情報を含む辞書
        """
        targets = {}
        with open(self.filename, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                targets[row[1]] = {'name': row[0], 'ip': row[2]}
        return targets

    def save_targets(self):
        """
        ターゲット情報をCSVファイルに保存する
        """
        with open(self.filename, 'w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            for key, value in self.targets.items():
                writer.writerow([value['name'], key, value['ip']])

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
        for key, value in self.targets.items():
            if value['name'] in input_text:
                return f"{value['name']}: {value['ip']}"
        return "指定されたターゲットが見つかりません。"

    def display_all_targets(self):
        """
        すべてのターゲットの名前とIPアドレスを表示する
        
        :return: すべてのターゲット情報を含む文字列のリスト
        """
        result = []
        for value in self.targets.values():
            result.append(f"{value['name']}: {value['ip']}")
        return result

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

# 使用例
if __name__ == "__main__":
    # IPAddressManagerのインスタンスを作成
    manager = IPAddressManager("target.csv")

    # すべてのターゲットを表示
    all_targets = manager.display_all_targets()
    print("すべてのターゲット:")
    for target in all_targets:
        print(target)

    # IPアドレスの変更
    # manager.change_ip_address()

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
    # print("追加モードで登録:")
    # manager.register_ip_addresses(discovered_ip_addresses, overwrite=False)

    # 現在のターゲット情報を表示
    # print("\n現在のターゲット情報:")
    # for target in manager.display_all_targets():
    #     print(target)

    # 上書きモードで登録（既存のIPアドレスも上書き）
    # print("\n上書きモードで登録:")
    # manager.register_ip_addresses(discovered_ip_addresses, overwrite=True)

    # 更新後のターゲット情報を表示
    # print("\n更新後のターゲット情報:")
    # for target in manager.display_all_targets():
    #     print(target)
    