import xml.etree.ElementTree as ET
from collections import namedtuple, defaultdict

# 脆弱性情報を格納するための名前付きタプルを定義
Vulnerability = namedtuple('Vulnerability', ['host', 'port', 'name', 'cvss'])

def parse_nmap_xml(file_path):
    """
    NMAPのXML出力を解析し、高リスクの脆弱性（CVSS >= 7.5）を抽出する関数
    :param file_path: 解析するXMLファイルのパス
    :return: Vulnerabilityオブジェクトのリスト
    """
    try:
        tree = ET.parse(file_path)
    except (ET.ParseError, FileNotFoundError) as e:
        print(f"ファイルの読み込みまたは解析エラー: {e}")
        return []
    
    root = tree.getroot()
    vulnerabilities = []
    
    for host in root.findall('.//host'):
        ip = host.find('.//address[@addrtype="ipv4"]').get('addr')
        vulnerabilities.extend(get_host_vulnerabilities(host, ip))
    
    return vulnerabilities

def get_host_vulnerabilities(host, ip):
    """
    ホストの脆弱性情報を収集し、CVSSスコアが7.5以上の脆弱性を抽出する
    :param host: XMLのhost要素
    :param ip: ホストのIPアドレス
    :return: Vulnerabilityオブジェクトのリスト
    """
    host_vulnerabilities = []
    
    for port in host.findall('.//port'):
        port_id = port.get('portid')
        for script in port.findall('.//script[@id="vulners"]'):
            for table in script.findall('.//table'):
                cvss_score = get_cvss_score(table)
                if cvss_score and cvss_score >= 7.5:
                    name = table.find('.//elem[@key="id"]').text
                    host_vulnerabilities.append(Vulnerability(ip, port_id, name, cvss_score))
    
    return host_vulnerabilities

def get_cvss_score(table):
    """
    テーブル要素からCVSSスコアを抽出する
    :param table: XMLのtable要素
    :return: CVSSスコア（float）またはNone
    """
    cvss = table.find('.//elem[@key="cvss"]')
    if cvss is not None:
        try:
            return float(cvss.text)
        except ValueError:
            print(f"CVSSスコアの変換に失敗しました: {cvss.text}")
    return None

def get_vulnerability_count_by_host_port(vulnerabilities):
    """
    ホストごとのポート別脆弱性の件数を集計する
    :param vulnerabilities: 脆弱性のリスト
    :return: ホストごとのポート別脆弱性件数の辞書
    """
    host_port_vuln_count = defaultdict(lambda: defaultdict(int))
    for vuln in vulnerabilities:
        host_port_vuln_count[vuln.host][vuln.port] += 1
    return host_port_vuln_count

def main():
    file_path = 'nmap-vulners.xml'  # 解析するXMLファイルのパス
    vulnerabilities = parse_nmap_xml(file_path)
    
    print("高リスクの脆弱性 (CVSS >= 7.5):")
    for vuln in sorted(vulnerabilities, key=lambda x: x.cvss, reverse=True):
        print(f"ホスト: {vuln.host}")
        print(f"ポート: {vuln.port}")
        print(f"脆弱性: {vuln.name}")
        print(f"CVSSスコア: {vuln.cvss}")
        print("-" * 50)
    
    # ホストごとのポート別脆弱性の件数を取得し表示
    host_port_vuln_count = get_vulnerability_count_by_host_port(vulnerabilities)
    print("\nホストごとのポート別脆弱性の件数:")
    for host, ports in host_port_vuln_count.items():
        print(f"ホスト: {host}")
        for port, count in ports.items():
            print(f"  ポート: {port}, 脆弱性の件数: {count}")
        print("-" * 50)

if __name__ == "__main__":
    main()