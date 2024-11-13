import ipaddress
import netifaces
import subprocess
import xml.etree.ElementTree as ET

def get_local_ip_and_netmask():
    """
    ローカルマシンのIPアドレスとネットマスクを取得する。

    Returns:
        tuple: (IPアドレス, ネットマスク) のタプル。見つからない場合は (None, None)。
    """
    for interface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(interface)
        if netifaces.AF_INET in addrs:
            for addr in addrs[netifaces.AF_INET]:
                ip = addr['addr']
                netmask = addr['netmask']
                if ip != '127.0.0.1':
                    return ip, netmask
    return None, None

def get_network_address(ip, netmask):
    """
    IPアドレスとネットマスクからネットワークアドレスを計算する。

    Args:
        ip (str): IPアドレス
        netmask (str): ネットマスク

    Returns:
        str: ネットワークアドレス（CIDR表記）
    """
    interface = ipaddress.IPv4Interface(f"{ip}/{netmask}")
    return str(interface.network)

def discover_hosts(network):
    """
    指定されたネットワーク上でホストディスカバリーを実行する。

    Args:
        network (str): スキャン対象のネットワークアドレス（CIDR表記）

    Returns:
        list: (IPアドレス, ステータス) のタプルのリスト
    """
    result = subprocess.run(
        ['nmap', '-sn', network, '-oX', '-'],
        capture_output=True,
        text=True
    )
    xml_output = result.stdout
    hosts_list = []
    
    # XMLをパースしてホスト情報を取得
    root = ET.fromstring(xml_output)
    for host in root.findall('.//host'):
        ip = host.find('.//address[@addrtype="ipv4"]').get('addr')
        status = host.find('.//status').get('state')
        hosts_list.append((ip, status))
    
    return hosts_list

def get_discovered_hosts_array(network):
    """
    指定されたネットワーク上で発見されたホストのIPアドレスのリストを返す。

    Args:
        network (str): スキャン対象のネットワークアドレス（CIDR表記）

    Returns:
        list: 発見されたホストのIPアドレスのリスト
    """
    result = subprocess.run(
        ['nmap', '-sn', network, '-oX', '-'],
        capture_output=True,
        text=True
    )
    xml_output = result.stdout
    ip_list = []
    
    # XMLをパースしてIPアドレスを抽出
    root = ET.fromstring(xml_output)
    for host in root.findall('.//host'):
        ip = host.find('.//address[@addrtype="ipv4"]').get('addr')
        ip_list.append(ip)
    
    return ip_list

def run_vulnerability_scan(target_ip):
    """
    指定されたターゲットIPアドレスに対して脆弱性スキャンを実行し、結果をXMLファイルに保存する。

    Args:
        target_ip (str): スキャン対象のIPアドレス

    Returns:
        None: 結果を'nmap-vulners.xml'に保存する

    Note:
        - nmapの'-sV'オプションでバージョン検出を行い、'vulners'スクリプトで脆弱性をスキャンする。
        - 結果はXMLファイル 'nmap-vulners.xml' に保存される。
    """
    result = subprocess.run(
        ['nmap', '-sV', '--script', 'vulners', target_ip, '-oX', 'nmap-vulners.xml'],
        capture_output=True,
        text=True
    )
    
    # nmapの実行結果を標準出力に表示（デバッグ用）
    print(result.stdout)

def main():
    """
    メイン実行関数。
    ローカルネットワーク情報を取得し、ホストディスカバリーを実行して結果を表示する。
    """
    # ローカルIPアドレスとネットマスクを取得
    local_ip, netmask = get_local_ip_and_netmask()
    if not local_ip or not netmask:
        print("ローカルIPアドレスまたはネットマスクを取得できませんでした。")
        return

    print(f"自身のIPアドレス: {local_ip}")
    print(f"ネットマスク: {netmask}")

    # ネットワークアドレスを計算
    network = get_network_address(local_ip, netmask)
    print(f"ネットワークアドレス: {network}")

    print("ホストディスカバリーを実行中...")
    # ホストディスカバリーを実行し、結果を表示
    discovered_hosts = discover_hosts(str(network))

    print(f"\n発見されたホスト数: {len(discovered_hosts)}")
    print("発見されたホストのIPアドレス:")
    for host, status in discovered_hosts:
        print(f"  {host} ({status})")

    # IPアドレスの配列を取得し表示
    ip_array = get_discovered_hosts_array(str(network))
    print("\n発見されたホストのIPアドレス（配列形式）:")
    print(", ".join(ip_array))

    # 脆弱性スキャンの実行
    response = input("脆弱性スキャンを実行しますか？ (y/n): ")
    if response.lower() == 'y':
        target_ip = input("スキャン対象のIPアドレスを入力してください: ")
        print(f"{target_ip} に対して脆弱性スキャンを実行中...")
        scan_result = run_vulnerability_scan(target_ip)
        print(scan_result)
    else:
        print("脆弱性スキャンはキャンセルされました。")

if __name__ == "__main__":
    main()
