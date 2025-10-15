import datetime
import os, shutil
import pandas as pd
import openpyxl

class VerificarArquivoInput:
    def __init__(self, services, dicCredentials, dicParameters):
        self.services = services
        self.dicCredentials = dicCredentials
        self.dicParameters = dicParameters
        self.folderInput = self.dicParameters["folderInput"] #Ex: data\\input
        self.folderRede = self.dicParameters["folderRede"] # Ex: U:\\Financeiro\\05- RPA\\A PROCESSAR
        self.dataAtual = datetime.datetime.now().strftime("%Y-%m-%d") # ex: 2023-08-01
        self.configFile = self.dicParameters["configFile"] # Ex: C:\\RPA\\Financeiro\\FIN001_V3\\artifacts\\configfile\\Config.xlsx
        self.configFileSheet = self.dicParameters["configFileSheet"] # Ex: Feriado 
        self.folderLocalTemp = self.dicParameters["folderLocalTemp"] # Ex: C:\\BOT

    def verificarPasta(self):
        try:
            self.services.logger.log_info("verificarPasta", "Iniciando verificação da pasta de entrada")
            # Acessar planilha configFile, acessar a sheet configFileSheet e gravar em um dataframe usando pandas
            dfConfig = pd.read_excel(self.configFile, sheet_name=self.configFileSheet)

            # === Lógica para identificar o último dia útil, ignorando finais de semana e feriados ===
            # Extrair lista de feriados da planilha (tenta colunas com nomes contendo 'feriad' ou 'data')
            feriados = set()
            try:
                col_candidates = [
                    c for c in dfConfig.columns
                    if any(k in str(c).lower() for k in ["feriad", "data", "date"])  # cobre 'feriado', 'data', 'date'
                ]
                if not col_candidates:
                    col_candidates = [dfConfig.columns[0]]  # fallback: primeira coluna
                serie = dfConfig[col_candidates[0]]
                # Converte valores para datas (considerando formato dia/mês/ano)
                dates = pd.to_datetime(serie, dayfirst=True, errors="coerce").dt.date
                feriados = {d for d in dates.tolist() if d is not None}
                self.services.logger.log_info("verificarPasta", f"Feriados encontrados: {feriados}")
            except Exception:
                feriados = set()

            # Define o candidato como o dia imediatamente anterior a hoje
            hoje = datetime.datetime.now().date()
            candidato = hoje - datetime.timedelta(days=1)

            # Enquanto for fim de semana (sábado=5, domingo=6) ou feriado, subtrai 1 dia
            while candidato.weekday() >= 5 or candidato in feriados:
                candidato -= datetime.timedelta(days=1)

            # Monta a estrutura de pasta no padrão: U:\Financeiro\05- RPA\A PROCESSAR\MM.AAAA\DD
            base_rede = self.folderRede or r"U:\\Financeiro\\05- RPA\\A PROCESSAR"
            mes_ano = f"{candidato.strftime('%m')}.{candidato.strftime('%Y')}"
            dia = candidato.strftime('%d')  # já com zero à esquerda
            caminho_pasta = os.path.join(base_rede, mes_ano, dia)
            self.services.logger.log_info("verificarPasta", f"Caminho da pasta a processar: {caminho_pasta}")

            #verifica se caminho de pasta existe. se nao existir tem que mostrar erro
            if not os.path.exists(caminho_pasta):
                raise FileNotFoundError(f"Pasta não encontrada: {caminho_pasta}")
            
            #verificando arquivos da pasta
            fileSAL = None
            fileForn = None
            fileExtrel = None
            #verificando arquivos da pasta
            for file in os.listdir(caminho_pasta):
                if file.lower().endswith('.txt'):
                    if 'SAL' in file:
                        fileSAL = file
                    if 'FORN' in file:
                        fileForn = file
                    if 'EXTREL' in file:
                        fileExtrel = file
            #verificando se foram encontrados arquivos
            lstFileInput = [fileSAL, fileForn, fileExtrel]
            if fileSAL is None and fileForn is None and fileExtrel is None:
                raise FileNotFoundError(f"Não Houveram Arquivos para processar na Pasta: {caminho_pasta}")
            self.services.logger.log_info("verificarPasta", f"Arquivos encontrados na pasta: {lstFileInput}")
            self.services.logger.log_info("verificarPasta", f"Arquivo SAL encontrado: {fileSAL}")
            self.services.logger.log_info("verificarPasta", f"Arquivo FORN encontrado: {fileForn}")
            self.services.logger.log_info("verificarPasta", f"Arquivo EXTREL encontrado: {fileExtrel}")
            return caminho_pasta, lstFileInput
            
        except Exception as e:
            # Em erros, envie também a linha do erro no corpo do e-mail
            self.services.logger.log_error("verificarPasta", f"Error: {str(e)} - Line: {self.services.traceback.extract_tb(e.__traceback__)[0][1]}")
            # Em execução independente sem services, exibe no console
            try:
                if not hasattr(self, 'services') or self.services is None:
                    print(f"Erro em verificarPasta: {e}")
            except Exception:
                pass
            raise e

    def movimentarArquivoParaLocal(self, caminho_pasta, lstFileInput):
        """
        Move os arquivos listados em lstFileInput da pasta caminho_pasta para a pasta temporária local.
        
        :param caminho_pasta: Caminho completo da pasta de origem (ex: 'U:\\Financeiro\\05- RPA\\A PROCESSAR\\10.2025\\13')
        :param lstFileInput: Lista com os nomes dos arquivos a serem movidos (ex: ['SAL_DW07_02_131025P_MOV.TXT', ...])
        """
        try:
            self.services.logger.log_info("movimentarArquivoParaLocal", f"Iniciando movimentação de arquivos para pasta temporária local: {self.folderLocalTemp}")
            # Clear any files (and sub-folders) in the local temp folder
            for file in os.listdir(self.folderLocalTemp):
                if file.lower().endswith('.txt'):
                    os.remove(os.path.join(self.folderLocalTemp, file))            

            # Copia os arquivos da pasta de rede para a pasta temporária local
            for file_name in lstFileInput:
                if file_name is not None:
                    src_path = os.path.join(caminho_pasta, file_name)
                    dst_path = os.path.join(self.folderLocalTemp, file_name)
                    shutil.copy2(src_path, dst_path)

            # será uma lista com o diretorio e o nome do arquivo ouseja arquivo completo
            lstFileProcess = [os.path.join(self.folderLocalTemp, file) for file in os.listdir(self.folderLocalTemp) if file.lower().endswith('.txt')]	
            self.services.logger.log_info("movimentarArquivoParaLocal", f"Arquivos movidos para pasta temporária local: {lstFileProcess}")
            return lstFileProcess

        except Exception as e:
            self.services.logger.log_error("movimentarArquivoParaLocal", f"Error: {str(e)} - Line: {self.services.traceback.extract_tb(e.__traceback__)[0][1]}")
            raise e
