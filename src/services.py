import traceback as tcb
from src.configsrc import Config
from src.databasesrc import DBManager
from src.logsrc import EnhancedLogger
from src.utils.gmailService import GmailService
from src.Task.verificarArquivoInput import VerificarArquivoInput

class Services:
    def __init__(self):
        self.traceback = tcb
        self.dicConfig, self.dicParameters = Config.loadConfig()
        self.bdManager = DBManager(self.dicConfig, self.dicParameters)
        self.logger = EnhancedLogger(self.dicConfig, self.dicParameters)
        self.gmail = GmailService(self, self.dicConfig, self.dicParameters)
        self.arquivoInput = VerificarArquivoInput(self, self.dicConfig, self.dicParameters)
        

