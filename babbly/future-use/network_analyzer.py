from scapy.all import sniff, ARP, wrpcap
import ipaddress
import subprocess

class NetworkAnalyzer:
    def __init__(self, pcap_file="arp_capture.pcap"):
        self.pcap_file = pcap_file
        self.captured_ips = set()

    def capture_arp_packets(self, timeout=60):
        """
        ARPパケットを指定した時間キャプチャし、結果をpcapファイルに保存します。
        """
        print("ARPパケットをキャプチャ中...")
        packets = sniff(filter="arp", timeout=timeout)
        wrpcap(self.pcap_file, packets)  # pcapファイルに保存
        print(f"{self.pcap_file}にキャプチャを保存しました。")

        # キャプチャしたARPパケットからIPアドレスを収集
        for pkt in packets:
            if ARP in pkt and pkt[ARP].op == 1:  # ARPリクエストのみ
                src_ip = pkt[ARP].psrc
                self.captured_ips.add(src_ip)
                print(f"ARPリクエストを検出: 送信元IPアドレス - {src_ip}")

    def guess_subnet_mask(self):
        """
        収集したIPアドレスからサブネットマスクを推測し、ネットワークアドレスを返します。
        """
        if not self.captured_ips:
            print("IPアドレスがキャプチャされていません。")
            return None

        ip_networks = [ipaddress.IPv4Address(ip) for ip in self.captured_ips]
        network = ipaddress.IPv4Network(ip_networks[0].exploded + '/32', strict=False)

        for ip in ip_networks[1:]:
            network = network.supernet(new_prefix=network.prefixlen - 1)
            while ip not in network:
                network = network.supernet(new_prefix=network.prefixlen - 1)

        print(f"推測されるネットワークアドレス: {network}")
        return network

    def check_ip_conflicts(self, network):
        """
        推測したネットワーク内でIPアドレスの重複を確認し、重複のないIPアドレスをリストアップします。
        """
        available_ips = []
        for ip in network.hosts():
            if str(ip) not in self.captured_ips:
                available_ips.append(ip)

        if available_ips:
            print("利用可能なIPアドレスのリスト:")
            for ip in available_ips:
                print(ip)
            return available_ips
        else:
            print("利用可能なIPアドレスが見つかりませんでした。")
            return None

    def set_adapter_ip(self, ip_address, netmask="255.255.255.0", adapter="eth0"):
        """
        指定したIPアドレスとサブネットマスクをネットワークアダプタに設定します。
        """
        try:
            subprocess.run(["sudo", "ip", "addr", "add", f"{ip_address}/{netmask}", "dev", adapter], check=True)
            print(f"{adapter}にIPアドレス {ip_address} を設定しました。")
            return True
        except Exception as e:
            print(f"IPアドレスの設定に失敗しました: {e}")
            return False

    def analyze_network(self, current_ip, current_network, capture_timeout=60, adapter="eth0"):
        """
        ネットワークの分析を実行するメインメソッド。
        現在のIPアドレスとネットワークアドレスを確認し、設定が必要な場合は新しいIPアドレスを設定します。
        """
        self.capture_arp_packets(timeout=capture_timeout)
        detected_network = self.guess_subnet_mask()

        # 現在のネットワークが発見されたネットワークに一致するかを確認
        if detected_network == current_network:
            print("現在のネットワークアドレスが一致しているため、IPアドレスの変更は不要です。")
        else:
            print("ネットワークが異なるため、新しいIPアドレスを設定します...")
            available_ips = self.check_ip_conflicts(detected_network)
            if available_ips:
                selected_ip = available_ips[0]  # 利用可能なIPアドレスの最初のものを選択
                print(f"設定するIPアドレス: {selected_ip}")
                success = self.set_adapter_ip(selected_ip, adapter=adapter)
                if success:
                    print("ネットワークに参加しました。")
                else:
                    print("ネットワーク参加に失敗しました。")
            else:
                print("利用可能なIPアドレスが見つかりませんでした。")

# 使用例
# 現在のIPアドレスとネットワークアドレスを渡して実行
current_ip = "192.168.1.10"
current_network = ipaddress.IPv4Network("192.168.1.0/24")
analyzer = NetworkAnalyzer()
analyzer.analyze_network(current_ip=current_ip, current_network=current_network, capture_timeout=120, adapter="eth0")
