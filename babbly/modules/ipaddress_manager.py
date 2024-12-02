import json

class IPAddressManager:
    """IPアドレス管理クラス """

    def __init__(self, json_file_path):
        """
        IPAddressManagerのコンストラクタ
        
        Args:
            json_file_path(str): ターゲット情報を含むJSONファイルの名前
        """
        self.addressmap = self._load_data(json_file_path)
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
            with open(file_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            raise Exception(f"JSONファイル '{file_path}' が見つかりません。")
        except json.JSONDecodeError:
            raise Exception(f"JSONファイル '{file_path}' の形式が不正です。")


    def _build_search_dict(self):
        """補助辞書を構築する。"""
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
        for key, record in self.addressmap.items():
            # 番号、ID、VoiceAliasをキーとしてIPを登録
            self.search_dict[key] = record
            self.search_dict[record["ID"]] = record
            self.search_dict[record["VoiceAlias"]] = record

            # ID をキーにフォネティックコードを登録
            phonetic_entries = phonetic_codes.get(record["ID"])
            if phonetic_entries:
                for code in phonetic_entries:
                    self.search_dict[code.lower()] = record  # 小文字で登録


    # def save_targets(self):
    #     """
    #     ターゲット情報をJSONファイルに保存する
    #     """
    #     data = [{'VoiceAlias': value['name'], 'ID': key, 'IP': value['ip']} for key, value in self.targets.items()]
    #     with open(self.filename, 'w', encoding='utf-8') as file:
    #         json.dump(data, file, ensure_ascii=False, indent=4)


    # def change_ip_address(self):
    #     """
    #     ユーザー入力に基づいてターゲットのIPアドレスを変更する
    #     """
    #     target_key = input("変更するターゲットを入力(a-z):")
    #     if target_key in self.targets:
    #         print(f"{self.targets[target_key]['name']}のipアドレスを変更します。")
    #         new_ip = input("ipアドレスを入力してください:")
    #         self.targets[target_key]['ip'] = new_ip
    #         self.save_targets()
    #         print(f"{self.targets[target_key]['name']}のipアドレスを変更しました。")
    #     else:
    #         print("指定されたターゲットが見つかりません。")


    # def get_ip_address(self, input_text):
    #     if not input_text:
    #         raise ValueError("エラー: 入力がありません。")

    #     for target in self.targets.values():
    #         if target['name'] in input_text:
    #             return target['ip']

    #     raise KeyError("エラー: 一致するターゲットが見つかりません。")


    def get_search_dict(self):
        return self.search_dict


    def find_target_ip(self, message):
        """
        message内の名前を使用して、target_dictから一致するターゲットのIPアドレスを探す。

        :param message: 検査する名前のリスト。ターゲット名が含まれている。
        :return: 一致するターゲット名とIPアドレス
        """
        # messageの各要素をチェック
        for item in message:
            record = self.search_dict[item]
            if record['IP']:
                # 一致する名前とIPアドレスを返す
                return record['VoiceAlias'], record['IP']
        # 一致するものがない場合
        return None, None


    def get_target_values(self, search_key):
        """
        指定されたキー（ターゲット名、ID、アルファベット、フォネティックコード）に対応する arg_flg の値を返す。

        Args:
            search_key (str): 検索するキー（ターゲット名、ID、アルファベット、フォネティックコードなど）。

        Returns:
            str: 該当する項目のターゲット名と IPアドレス
        """
        try:
            record = self.search_dict[search_key]
            return record["VoiceAlias"], record["IP"]
        except KeyError:
            return None,None


    def display_all_targets(self):
        """
        すべてのターゲットのVoiceAlias（名前）とIPアドレスを表示する。
        
        :return: すべてのターゲット情報を含む文字列のリスト
        """
        target_list = [
            f"{key}. {record['ID']}: {record['VoiceAlias']} {record['IP']}" 
            for key, record in self.addressmap.items()
        ]
        
        for target in target_list:
            print(target)
        
        return target_list

    # def register_ip_addresses(self, ip_addresses, overwrite=False):
    #     """
    #     複数のIPアドレスを一括で登録するメソッド

    #     :param ip_addresses: 登録するIPアドレスのリスト
    #     :param overwrite: True の場合、既存のIPアドレスを上書き。False の場合、IPアドレスが未設定のターゲットのみ更新
    #     """
    #     ip_index = 0
    #     for target_key, target_info in self.targets.items():
    #         if ip_index >= len(ip_addresses):
    #             break

    #         if overwrite or not target_info['ip']:
    #             self.targets[target_key]['ip'] = ip_addresses[ip_index]
    #             ip_index += 1

    #     self.save_targets()  # 変更を保存

    # def clear_all_ip_addresses(self):
    #     """
    #     全てのターゲットのIPアドレスを消去するメソッド
    #     """
    #     for target in self.targets.values():
    #         target['ip'] = ""
    #     self.save_targets()
    #     print("全てのIPアドレスを消去しました。")


    # def clear_specific_ip_address(self, target_identifier):
    #     """
    #     指定したターゲットのIPアドレスを消去するメソッド

    #     :param target_identifier: 消去するターゲットのID (a-z) または名前
    #     :return: 成功時はTrue、ターゲットが見つからない場合はFalse
    #     """
    #     target_key = None
    #     target_name = None

    #     # IDで検索
    #     if target_identifier in self.targets:
    #         target_key = target_identifier
    #         target_name = self.targets[target_key]['name']
    #     else:
    #         # 名前で検索
    #         for key, value in self.targets.items():
    #             if value['name'] == target_identifier:
    #                 target_key = key
    #                 target_name = target_identifier
    #                 break

    #     if target_key is not None:
    #         self.targets[target_key]['ip'] = ""
    #         self.save_targets()
    #         print(f"{target_name}のIPアドレスを消去しました。")
    #         return True
    #     else:
    #         print("指定されたターゲットが見つかりません。")
    #         return False


# 使用例
if __name__ == "__main__":
    # IPAddressManagerのインスタンスを作成
    manager = IPAddressManager("babbly/ja/targets.json")

    targetname, targetip = manager.get_target_values("ターゲットブラボー")
    print(targetip)


    # すべてのターゲットを表示
    manager.display_all_targets()

    # IPアドレスの変更
    # manager.change_ip_address()

    # 文字列入力によるIPアドレスの表示
    # input_text = "ターゲットチャーリーのアドレスを教えて"
    # result = manager.get_ip_address(input_text)
    # print(result)

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
    # manager.display_all_targets()

    # 上書きモードで登録（既存のIPアドレスも上書き）
    # print("\n上書きモードで登録:")
    # manager.register_ip_addresses(discovered_ip_addresses, overwrite=True)

    # 更新後のターゲット情報を表示
    # print("\n更新後のターゲット情報:")
    # manager.display_all_targets()

    # 現在のターゲット情報を表示
    # print("消去前のターゲット情報:")
    # manager.display_all_targets()

    # IDを使用してターゲットのIPアドレスを消去
    # manager.clear_specific_ip_address("a")

    # 名前を使用してターゲットのIPアドレスを消去
    # manager.clear_specific_ip_address("ターゲットブラボー")

    # 更新後のターゲット情報を表示
    # print("\n消去後のターゲット情報:")
    # manager.display_all_targets()

    # 存在しないターゲットを指定した場合
    # manager.clear_specific_ip_address("存在しないターゲット")