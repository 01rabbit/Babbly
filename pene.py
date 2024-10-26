import asyncio
import json
import os
import sys
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from pymetasploit3.msfrpc import MsfRpcClient
from contextlib import asynccontextmanager
import logging
import re
from logging.handlers import RotatingFileHandler
import queue

# Configuration and Constants
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
MAX_LOG_FILES = 5

class PentestAutomationError(Exception):
    """Base exception for pentest automation"""
    pass

class ConfigurationError(PentestAutomationError):
    """Configuration related errors"""
    pass

class ConnectionError(PentestAutomationError):
    """Connection related errors"""
    pass

class ExploitError(PentestAutomationError):
    """Exploit execution related errors"""
    pass

class ValidationError(PentestAutomationError):
    """Data validation related errors"""
    pass

class ExploitStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"

@dataclass
class ExploitConfiguration:
    target_ip: str
    target_port: int
    module_path: str
    cve: str
    options: Dict[str, Any]
    timeout: Optional[int] = None
    retry_count: int = 3

    def validate(self) -> bool:
        if not re.match(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$", self.target_ip):
            return False
        if not (1 <= self.target_port <= 65535):
            return False
        return all([self.module_path, self.cve])

@dataclass
class ExploitResult:
    target_ip: str
    target_port: int
    cve: str
    module_path: str
    status: ExploitStatus
    message: str
    timestamp: datetime
    execution_time: float
    session_id: Optional[str] = None

class SecureLogger:
    """Enhanced secure logging functionality"""

    def __init__(self, name: str, log_dir: str = "logs"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f'{name}_{datetime.now().strftime("%Y%m%d")}.log')
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=MAX_LOG_SIZE,
            backupCount=MAX_LOG_FILES,
            mode='a'
        )
        file_handler.setLevel(logging.DEBUG)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(threadName)s - %(message)s'
        )
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )

        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def _mask_sensitive_info(self, message: str) -> str:
        patterns = [
            (r'password["\\s]*:["\\s]*[^"}\\s]+', 'password: *****'),
            (r'session[_\\s]?id["\\s]*:["\\s]*[^"}\\s]+', 'session_id: *****'),
            (r'token["\\s]*:["\\s]*[^"}\\s]+', 'token: *****'),
            (r'\\b\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\b', '[MASKED_IP]')
        ]
        for pattern, replacement in patterns:
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
        return message

    def info(self, message: str):
        self.logger.info(self._mask_sensitive_info(message))

    def error(self, message: str):
        self.logger.error(self._mask_sensitive_info(message))

class PentestAutomation:
    def __init__(self, config_path: str, max_concurrent_exploits: int = 5):
        """Initialize with configuration file and max concurrency for exploits"""
        self.logger = SecureLogger(__name__)
        self.config = self._load_config(config_path)
        self.results_queue: queue.Queue = queue.Queue()
        self.active_sessions: Dict[str, Any] = {}
        self._initialize_connection()
        self.semaphore = asyncio.Semaphore(max_concurrent_exploits)

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)

            required_fields = ['msf_host', 'msf_port', 'msf_password', 'lhost', 'lport']
            for field in required_fields:
                if field not in config:
                    raise ConfigurationError(f"Missing required configuration field: {field}")

            return config
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {str(e)}")

    def _initialize_connection(self):
        """Initialize connection to Metasploit RPC server"""
        try:
            self.client = MsfRpcClient(
                password=self.config['msf_password'],
                server=self.config['msf_host'],
                port=self.config['msf_port']
            )
            self.logger.info("Successfully connected to Metasploit RPC server")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Metasploit RPC server: {str(e)}")

    def parse_scan_results(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse the Nmap scan XML file to extract IP, port, and CVE information."""
        results = []
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # IPアドレスとポート、CVE番号の抽出
            for host in root.findall('host'):
                ip_address = host.find('address').get('addr')
                for port in host.findall('.//port'):
                    port_number = int(port.get('portid'))
                    for script in port.findall('script'):
                        if script.get('id') == 'vulners':
                            for elem in script.findall('.//elem'):
                                cve = elem.text
                                if cve and cve.startswith('CVE'):
                                    results.append({
                                        'ip': ip_address,
                                        'port': port_number,
                                        'cve': cve
                                    })
            return results
        except Exception as e:
            self.logger.error(f"Failed to parse scan results: {str(e)}")
            return []

    def find_exploits_for_cve(self, cve: str) -> List[str]:
        """Find Metasploit modules that support the specified CVE."""
        matching_modules = []
        try:
            for module in self.client.modules.exploits:
                module_info = self.client.modules.use('exploit', module).info
                if 'cve' in module_info and cve in module_info['cve']:
                    matching_modules.append(module)
            self.logger.info(f"Found {len(matching_modules)} exploit(s) for CVE {cve}")
            return matching_modules
        except Exception as e:
            self.logger.error(f"Failed to find exploits for CVE {cve}: {str(e)}")
            return []

    async def run_exploits_from_scan_results(self, scan_results: List[Dict[str, Any]]):
        """Run exploits on each target based on the scan results and CVE mappings."""
        for result in scan_results:
            target_ip = result['ip']
            target_port = result['port']
            cve = result['cve']
            
            # CVE番号に対応するエクスプロイトモジュールを検索
            exploit_modules = self.find_exploits_for_cve(cve)
            for module_path in exploit_modules:
                config = ExploitConfiguration(
                    target_ip=target_ip,
                    target_port=target_port,
                    module_path=module_path,
                    cve=cve,
                    options={},  # 必要なオプションを指定
                    timeout=30,
                    retry_count=3
                )
                result = await self.run_exploit_with_retry(config)
                self.logger.info(f"Exploit result for {cve} on {target_ip}:{target_port} using {module_path}: {result.status}")

async def main():
    if len(sys.argv) != 3:
        print("Usage: python pentest_automation.py <config.json> <nmap-vulners.xml>")
        sys.exit(1)

    config_path = sys.argv[1]
    scan_results_path = sys.argv[2]

    automation = PentestAutomation(config_path=config_path)
    
    # スキャン結果を解析してCVE、IP、ポート情報を抽出
    scan_results = automation.parse_scan_results(scan_results_path)
    
    # 抽出したスキャン結果を使ってエクスプロイトを実行
    await automation.run_exploits_from_scan_results(scan_results)

if __name__ == "__main__":
    asyncio.run(main())