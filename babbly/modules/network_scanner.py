import ipaddress
import netifaces
import subprocess
import xml.etree.ElementTree as ET
import logging
from typing import Optional, Tuple, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class NetworkScanner:
    def get_local_ip_and_netmask(self) -> Tuple[Optional[str], Optional[str]]:
        """Retrieve the local machine's IP address and netmask."""
        for interface in netifaces.interfaces():
            try:
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        ip = addr['addr']
                        netmask = addr['netmask']
                        if ip != '127.0.0.1':
                            return ip, netmask
            except ValueError as e:
                logging.error(f"Error retrieving addresses for interface {interface}: {e}")
        return None, None

    def get_network_address(self, ip: str, netmask: str) -> str:
        """Calculate the network address from an IP address and netmask."""
        interface = ipaddress.IPv4Interface(f"{ip}/{netmask}")
        return str(interface.network)

    def discover_hosts(self, network: str) -> List[Tuple[str, str]]:
        """Perform host discovery on the specified network."""
        try:
            result = subprocess.run(['nmap', '-sn', network, '-oX', '-'], capture_output=True, text=True)
            xml_output = result.stdout
            hosts_list = []
            root = ET.fromstring(xml_output)
            for host in root.findall('.//host'):
                ip = host.find('.//address[@addrtype="ipv4"]').get('addr')
                status = host.find('.//status').get('state')
                hosts_list.append((ip, status))
            return hosts_list
        except subprocess.CalledProcessError as e:
            logging.error("Error running nmap: %s", e)
            return []

    def run_vulnerability_scan(self, target_ip: str) -> None:
        """Run a vulnerability scan on a specified target IP and save results in XML."""
        try:
            result = subprocess.run(
                ['nmap', '-sV', '--script', 'vulners', target_ip, '-oX', 'nmap-vulners.xml'],
                capture_output=True,
                text=True
            )
            logging.info(f"Vulnerability scan result:\n{result.stdout}")
        except subprocess.CalledProcessError as e:
            logging.error("Error running vulnerability scan: %s", e)

    def network_scan(self, tts, ip_mgr, lang_ja):
        local_ip, netmask = self.get_local_ip_and_netmask()
        if not local_ip or not netmask:
            logging.error("Could not retrieve local IP or netmask.")
            return

        network = self.get_network_address(local_ip, netmask)

        if lang_ja:
            print("ネットワークをスキャン")
            tts.say("ネットワークをスキャンします")
        else:
            print("Scan the network")
            tts.say("Scanning the network")

        discovered_hosts = self.discover_hosts(network)

        for host, status in discovered_hosts:
            logging.info(f"Host: {host}, Status: {status}")
        if lang_ja:
            print(f"{str(len(discovered_hosts))}個のホストを発見")
            tts.say(f"{str(len(discovered_hosts))}個のホストを発見")
        else:
            print(f"{str(len(discovered_hosts))} hosts found")
            tts.say(f"{str(len(discovered_hosts))} hosts found")
        # discovered_hostsからIPアドレスを抽出
        ip_addresses = [host[0] for host in discovered_hosts]
        ip_mgr.register_ip_addresses(ip_addresses, True)

    def main(self):
        local_ip, netmask = self.get_local_ip_and_netmask()
        if not local_ip or not netmask:
            logging.error("Could not retrieve local IP or netmask.")
            return

        logging.info(f"Local IP Address: {local_ip}")
        logging.info(f"Netmask: {netmask}")

        network = self.get_network_address(local_ip, netmask)
        logging.info(f"Network Address: {network}")

        logging.info("Performing host discovery...")
        discovered_hosts = self.discover_hosts(network)
        logging.info(f"Discovered {len(discovered_hosts)} hosts.")

        for host, status in discovered_hosts:
            logging.info(f"Host: {host}, Status: {status}")

        response = input("Would you like to run a vulnerability scan? (y/n): ")
        if response.lower() == 'y':
            target_ip = input("Enter target IP address for scan: ")
            self.run_vulnerability_scan(target_ip)
        else:
            logging.info("Vulnerability scan canceled.")

if __name__ == "__main__":
    scanner = NetworkScanner()
    scanner.main()