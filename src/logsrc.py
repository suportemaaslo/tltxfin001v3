import logging
import os
import datetime
import inspect
import psutil
import psycopg2
from psycopg2 import Error
import textwrap
import traceback
from enum import Enum
from pathlib import Path
from typing import Optional, Any, Dict

class ProcessType(str, Enum):
    ROBOTIC = "robotic"
    BUSINESS = "business"
    SYSTEM = "system"
    PROCESS = "process"

class LogStatus(str, Enum):
    FAILURE = "failure"
    SUCCESS = "success"
    WARNING = "warning"
    CRITICAL = "critical"
    INFO = "information"

class EnhancedLogger:
    """Logger avançado com suporte a arquivo, console e banco de dados Supabase."""
    
    def __init__(self, dcConfig: dict, dcParameter: dict, execution_id: int = None):
        self.project_name = dcConfig.get('projectName', 'FIN001_V3')
        self.dcConfig = dcConfig
        self.dcParameter = dcParameter
        self.execution_id = execution_id  # ID da execução atual
        self.transaction_id = None  # ID da transação atual (opcional)
        
        # Configurações de log
        self.log_dir = dcConfig.get('folderlog', './artifacts/logs')
        self.log_file: Optional[str] = None
        self.db_connection: Optional[psycopg2.extensions.connection] = None
        self.debug_mode = True
        
        # Configurações do banco Supabase
        self.connection_params = {
            'user': dcConfig.get("credSupabaseUser"),
            'password': dcConfig.get("credSupabasePassword"),
            'host': dcConfig.get("credSupabaseHost"),
            'port': dcConfig.get("credSupabasePort"),
            'dbname': dcConfig.get("credSupabaseDBNAME")
        }
        
        # Formato de colunas - definições de largura
        self.col_widths = {
            'timestamp': 25,    # TIMESTAMP
            'execution': 12,    # EXECUTION ID
            'transaction': 12,  # TRANSACTION ID
            'function': 25,     # FUNCTION
            'file': 20,         # FILE
            'line': 6,          # LINE NUMBER
            'message': 40,      # MESSAGE
            'process_type': 12, # PROCESS_TYPE
            'status': 12        # STATUS
        }
        
        # Largura para wrap de mensagens
        self.message_width = self.col_widths['message']
        
        # Quantidade de espaço entre borda e conteúdo da coluna
        self.padding = 1
        
        # Setup inicial
        self.setup_logging()
        
        # Tentar conectar ao banco de dados
        self._try_connect_to_database()
    
    def setup_logging(self) -> None:
        """Configuração inicial do logging."""
        try:
            # Ensure log directory exists
            os.makedirs(self.log_dir, exist_ok=True)
            
            # Create log file with timestamp
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            self.log_file = os.path.join(self.log_dir, f"rpa_{self.project_name}_{timestamp}.log")
            
            # Define UTF-8 encoding for the log file
            with open(self.log_file, 'w', encoding='utf-8') as f:
                # Escreve o cabeçalho do arquivo de log
                f.write(self._create_header())
            
            # Set up standard Python logging
            logging.basicConfig(
                level=logging.DEBUG if self.debug_mode else logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler()
                ]
            )
            
            # Register function to add closing line on program exit
            import atexit
            atexit.register(self._add_closing_line)
        except Exception as e:
            print(f"Erro ao configurar logging: {e}")
        
    def _create_separator_line(self) -> str:
        """Cria a linha separadora com + alinhado precisamente com as barras verticais."""
        try:
            separator = "+"
            for name, width in self.col_widths.items():
                # Adiciona dois traços extras para compensar o espaço de padding em cada lado
                separator += "-" * (width + self.padding * 2) + "+"
            return separator
        except Exception as e:
            print(f"Erro ao criar linha separadora: {e}")
            return ""

    def _create_header(self) -> str:
        """Cria o cabeçalho com alinhamento preciso e títulos melhor centralizados."""
        try:
            # Títulos das colunas
            headers = {
                'timestamp': " TIMESTAMP ",
                'execution': " EXEC_ID ",
                'transaction': " TRANS_ID ",
                'function': " FUNCTION ",
                'file': " FILE ",
                'line': " LINE ",
                'message': " MESSAGE ",
                'process_type': " PROC_TYPE ",
                'status': " STATUS "
            }
            
            # Criar linha separadora
            separator = self._create_separator_line()
            
            # Criar linha de cabeçalho
            header_line = "|"
            for name, width in self.col_widths.items():
                # Centraliza o título na coluna
                title = headers[name]
                padding_left = self.padding + (width - len(title) + 1) // 2
                padding_right = width - (len(title) - 1) - padding_left + self.padding
                header_line += " " * padding_left + title + " " * padding_right + "|"
            
            # Monta o cabeçalho completo
            full_header = separator + "\n" + header_line + "\n" + separator + "\n"
            return full_header
        except Exception as e:
            print(f"Erro ao criar cabeçalho: {e}")
            return ""

    def _try_connect_to_database(self) -> bool:
        """Tenta conectar ao banco de dados Supabase."""
        try:
            if all(self.connection_params.values()):
                self.db_connection = psycopg2.connect(**self.connection_params)
                print("Conexão com banco de dados estabelecida para logs")
                return True
            else:
                print("Parâmetros de conexão incompletos - logs serão salvos apenas em arquivo")
                return False
        except Exception as e:
            print(f"Falha ao conectar ao banco para logs: {str(e)} - logs serão salvos apenas em arquivo")
            return False

    def set_execution_id(self, execution_id: int) -> None:
        """Define o ID da execução atual."""
        self.execution_id = execution_id

    def set_transaction_id(self, transaction_id: int) -> None:
        """Define o ID da transação atual."""
        self.transaction_id = transaction_id

    def clear_transaction_id(self) -> None:
        """Limpa o ID da transação atual."""
        self.transaction_id = None

    def _get_caller_info(self, depth: int = 3) -> tuple[str, str, int]:
        """Get information about the caller (file, function, line number).
        
        Args:
            depth (int): How far back in the stack to look for the caller
        
        Returns:
            tuple: (filename, function_name, line_number)
        """
        try:
            # Pega a stack de chamadas até o depth desejado
            frame = inspect.currentframe()
            for _ in range(depth):
                if frame.f_back is None:
                    break
                frame = frame.f_back
            
            # Extrai informações do frame
            if frame:
                frame_info = inspect.getframeinfo(frame)
                filename = os.path.basename(frame_info.filename)
                function_name = frame_info.function
                line_number = frame_info.lineno
                return filename, function_name, line_number
        except Exception:
            pass
        
        return "unknown.py", "unknown", 0
        
    def log_entry(self, function_name: str, log_message: str,
                process_type: ProcessType = ProcessType.SYSTEM,
                status: LogStatus = LogStatus.INFO,
                line_number: int = None) -> None:
        """Log a new entry to both file and database with precise alignment."""
        
        # Get current timestamp
        now = datetime.datetime.now()
        timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
        
        # Get caller info if line_number not provided
        if line_number is None:
            source_file, caller_function, line_number = self._get_caller_info(depth=3)
        else:
            source_file, caller_function, _ = self._get_caller_info(depth=3)
        
        # Validate enum values
        if not isinstance(process_type, ProcessType):
            try:
                if isinstance(process_type, str):
                    process_type = ProcessType(process_type.lower())
                else:
                    process_type = ProcessType.SYSTEM
            except (ValueError, AttributeError):
                process_type = ProcessType.SYSTEM
                
        if not isinstance(status, LogStatus):
            try:
                if isinstance(status, str):
                    status = LogStatus(status.lower())
                else:
                    status = LogStatus.INFO
            except (ValueError, AttributeError):
                status = LogStatus.INFO
        
        # Quebra a mensagem em múltiplas linhas se necessário
        message_lines = textwrap.wrap(log_message, width=self.message_width)
        if not message_lines:
            message_lines = [""]
            
        # Prepara valores para cada coluna (truncando se necessário)
        values = {
            'timestamp': timestamp[:self.col_widths['timestamp']],
            'execution': str(self.execution_id or 'N/A')[:self.col_widths['execution']],
            'transaction': str(self.transaction_id or 'N/A')[:self.col_widths['transaction']],
            'function': function_name[:self.col_widths['function']],
            'file': source_file[:self.col_widths['file']],
            'line': str(line_number)[:self.col_widths['line']],
            'message': message_lines[0],
            'process_type': process_type.value[:self.col_widths['process_type']],
            'status': status.value[:self.col_widths['status']]
        }
        
        # Formata a linha usando o mesmo padrão de padding que o cabeçalho
        log_line = "|"
        for name, width in self.col_widths.items():
            content = values[name]
            padding_right = width - len(content) + self.padding
            log_line += " " * self.padding + content + " " * padding_right + "|"
            
        # Escreve no arquivo de log com codificação UTF-8
        if self.log_file:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(log_line + "\n")
                    
                    # Se houver mais linhas na mensagem, adiciona-as com alinhamento preciso
                    if len(message_lines) > 1:
                        for i in range(1, len(message_lines)):
                            cont_line = "|"
                            for name, width in self.col_widths.items():
                                if name == 'message':
                                    content = message_lines[i]
                                    padding_right = width - len(content) + self.padding
                                    cont_line += " " * self.padding + content + " " * padding_right + "|"
                                else:
                                    cont_line += " " * (width + self.padding * 2) + "|"
                            f.write(cont_line + "\n")
                    
                    # Adiciona separador após erros críticos para ênfase
                    if status == LogStatus.CRITICAL:
                        f.write(self._create_separator_line() + "\n")
            except Exception as e:
                print(f"Erro ao escrever no arquivo de log: {e}")
        
        # Log to console
        log_level = self._get_log_level(status)
        logging.log(log_level, f"{function_name}: {log_message}")
        
        # Save to database if connected and execution_id is available
        if self.execution_id:
            self._log_to_database(function_name, source_file, line_number, 
                                log_message, process_type, status)
    
    def _add_closing_line(self) -> None:
        """Add closing line to log file on program exit with exact alignment."""
        if hasattr(self, 'log_file') and self.log_file and os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(self._create_separator_line() + "\n")
            except Exception:
                pass  # Silently fail if we can't write to the file
                
    def _get_log_level(self, status: LogStatus) -> int:
        """Map log status to Python logging level."""
        status_map = {
            LogStatus.CRITICAL: logging.CRITICAL,
            LogStatus.FAILURE: logging.ERROR,
            LogStatus.WARNING: logging.WARNING,
            LogStatus.INFO: logging.INFO,
            LogStatus.SUCCESS: logging.INFO
        }
        return status_map.get(status, logging.INFO)
    
    def _log_to_database(self, function_name: str, source_file: str, line_number: int,
                        log_message: str, process_type: ProcessType, status: LogStatus) -> bool:
        """Salva o log na tabela LOG do Supabase."""
        if not self.db_connection or not self.execution_id:
            return False
            
        try:
            cursor = self.db_connection.cursor()
            
            # Query para inserir na tabela LOG
            insert_query = """
                INSERT INTO LOG (IDEXECUTION, IDTRANSACTION, FUNCTION, FILE, LINENUMBER, 
                               MESSAGE, PROCESSTYPE, STATUS, CREATED_AT) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP);
            """
            
            cursor.execute(insert_query, (
                self.execution_id,
                self.transaction_id,  # Pode ser None
                function_name,
                source_file,
                line_number,
                log_message,
                process_type.value,
                status.value
            ))
            
            self.db_connection.commit()
            cursor.close()
            return True
            
        except Error as e:
            print(f"Erro ao salvar log no banco: {e}")
            # Tenta reconectar uma vez
            try:
                if self._try_connect_to_database():
                    return self._log_to_database(function_name, source_file, line_number,
                                               log_message, process_type, status)
            except Exception:
                pass
            return False
        except Exception as e:
            print(f"Erro inesperado ao salvar log: {e}")
            return False
    
    def log_info(self, function_name: str, message: str, process_type: ProcessType = ProcessType.SYSTEM) -> None:
        """Log information message."""
        self.log_entry(function_name, message, process_type, LogStatus.INFO)
    
    def log_success(self, function_name: str, message: str, process_type: ProcessType = ProcessType.SYSTEM) -> None:
        """Log success message."""
        self.log_entry(function_name, message, process_type, LogStatus.SUCCESS)
    
    def log_warning(self, function_name: str, message: str, process_type: ProcessType = ProcessType.SYSTEM) -> None:
        """Log warning message."""
        self.log_entry(function_name, message, process_type, LogStatus.WARNING)
    
    def log_error(self, function_name: str, message: str, exception: Exception = None, 
                 process_type: ProcessType = ProcessType.SYSTEM) -> None:
        """Log error message with traceback information."""
        # Captura informações do traceback da exceção
        line_number = None
        try:
            if exception and hasattr(exception, '__traceback__') and exception.__traceback__:
                # Usa o traceback da exceção fornecida
                tb_list = traceback.extract_tb(exception.__traceback__)
                if tb_list:
                    line_number = tb_list[-1][1]  # Última linha do traceback
            else:
                # Fallback para o comportamento original
                frame = inspect.currentframe()
                if frame and frame.f_back:
                    line_number = frame.f_back.f_lineno
        except Exception:
            pass
        
        self.log_entry(function_name, message, process_type, LogStatus.FAILURE, line_number)
    
    def log_critical(self, function_name: str, message: str, process_type: ProcessType = ProcessType.SYSTEM) -> None:
        """Log critical error message with traceback information."""
        # Captura informações do traceback
        line_number = None
        try:
            frame = inspect.currentframe()
            if frame and frame.f_back:
                line_number = frame.f_back.f_lineno
        except Exception:
            pass
        
        self.log_entry(function_name, message, process_type, LogStatus.CRITICAL, line_number)

    def disconnect(self) -> None:
        """Fecha a conexão com o banco de dados."""
        try:
            if self.db_connection:
                self.db_connection.close()
                self.db_connection = None
                print("Conexão com banco de dados fechada")
        except Exception as e:
            print(f"Erro ao fechar conexão com banco: {e}")