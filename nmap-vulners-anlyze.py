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
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    vulnerabilities = []
    
    # XMLツリーをトラバースして脆弱性情報を収集
    for host in root.findall('.//host'):
        ip = host.find('.//address[@addrtype="ipv4"]').get('addr')
        
        for port in host.findall('.//port'):
            port_id = port.get('portid')
            
            # vulnersスクリプトの結果を検索
            for script in port.findall('.//script[@id="vulners"]'):
                for table in script.findall('.//table'):
                    cvss = table.find('.//elem[@key="cvss"]')
                    if cvss is not None:
                        cvss_score = float(cvss.text)
                        # 高リスクの脆弱性（CVSS >= 7.5）のみを抽出
                        if cvss_score >= 7.5:
                            name = table.find('.//elem[@key="id"]').text
                            vulnerabilities.append(Vulnerability(ip, port_id, name, cvss_score))
    
    return vulnerabilities

def main():
    file_path = 'nmap-vulners.xml'  # 解析するXMLファイルのパス
    vulnerabilities = parse_nmap_xml(file_path)
    
    # 高リスクの脆弱性を表示
    print("高リスクの脆弱性 (CVSS >= 7.5):")
    for vuln in sorted(vulnerabilities, key=lambda x: x.cvss, reverse=True):
        print(f"ホスト: {vuln.host}")
        print(f"ポート: {vuln.port}")
        print(f"脆弱性: {vuln.name}")
        print(f"CVSSスコア: {vuln.cvss}")
        print("-" * 50)
    
    # ホストごとにポートごとの脆弱性件数を集計
    host_port_vuln_count = defaultdict(lambda: defaultdict(int))
    for vuln in vulnerabilities:
        host_port_vuln_count[vuln.host][vuln.port] += 1
    
    # 集計結果を表示
    print("\nホストごとのポート別脆弱性の件数:")
    for host, ports in host_port_vuln_count.items():
        print(f"ホスト: {host}")
        for port, count in ports.items():
            print(f"  ポート: {port}, 脆弱性の件数: {count}")
        print("-" * 50)

if __name__ == "__main__":
    main()