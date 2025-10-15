import os, json
from dotenv import load_dotenv

class Config:
    def __init__(self):
        self.dicCredentials = {}
        self.dicParameters = {}
    
    def loadConfig():
        try:
            #Clear Console
            os.system("cls")

            #CREDENTIALS#
            #Load .env credentials
            load_dotenv()
            #Get credentials values
            #PROTHEUS
            credProtUser = os.getenv("PROTHEUS_USER")
            credProtPassword = os.getenv("PHOTHEUS_PASSWORD")
            #SUPABASE
            credSupabaseUser = os.getenv("SUPABASE_USER")
            credSupabasePassword = os.getenv("SUPABASE_PASSWORD")
            credSupabaseHost = os.getenv("SUPABASE_HOST")
            credSupabasePort = os.getenv("SUPABASE_PORT")
            credSupabaseDBNAME = os.getenv("SUPABASE_DBNAME")
            #GMAIL
            credGmailDomain = os.getenv("GMAIL_DOMAIN")
            credGmailPort = os.getenv("GMAIL_PORT")
            credGmailEmail = os.getenv("GMAIL_EMAIL")
            credGmailAppPassword = os.getenv("GMAIL_APP_PASSWORD")

            #Set credentials values
            dicCredentials = {
                "credProtUser": credProtUser, 
                "credProtPassword": credProtPassword,

                "credSupabaseUser": credSupabaseUser,
                "credSupabasePassword": credSupabasePassword,
                "credSupabaseHost": credSupabaseHost,
                "credSupabasePort": credSupabasePort,
                "credSupabaseDBNAME": credSupabaseDBNAME,

                "credGmailDomain": credGmailDomain,
                "credGmailPort": credGmailPort,
                "credGmailEmail": credGmailEmail,
                "credGmailAppPassword": credGmailAppPassword,
                }
            
            #PARAMETERS#

            #Load config.json parameters
            with open('config.json', 'r', encoding='utf-8') as jsonfile:
                jsondata = json.load(jsonfile)
            #Get parameters values
            processName = jsondata["process"]["processname"]
            processDeveloper = jsondata["process"]["developer"]
            processDescription = jsondata["process"]["description"]
            processIDProcess = jsondata["process"]["idprocess"]

            robotIDProcess = jsondata["robot"]["idprocess"]
            robotName = jsondata["robot"]["robotname"]
            robotCode = jsondata["robot"]["robotcode"]
            robotVersion = jsondata["robot"]["version"]

            folderLog = jsondata["folders"]["folderlog"]
            folderTemp = jsondata["folders"]["foldertemp"]
            folderInput = jsondata["folders"]["folderinput"]
            folderOutput = jsondata["folders"]["folderoutput"]
            folderRede = jsondata["folders"]["caminhoRede"]
            folderLocalTemp = jsondata["folders"]["CaminhoTempLocal"]

            emailRemetente = jsondata["email"]["remetente"]
            emailDestinatario = jsondata["email"]["destinatario"]
            emailCopia = jsondata["email"]["copiacc"]

            configFile = jsondata["configFile"]["file"]
            configFileSheet = jsondata["configFile"]["sheet"]

            #Set parameters values
            dicParameters = {
                "processName": processName,
                "processDeveloper": processDeveloper,
                "processDescription": processDescription,
                "processIDProcess": processIDProcess,

                "robotIDProcess": robotIDProcess,
                "robotName": robotName,
                "robotCode": robotCode,
                "robotVersion": robotVersion,

                "folderLog": folderLog,
                "folderTemp": folderTemp,
                "folderInput": folderInput,
                "folderOutput": folderOutput,
                "folderRede": folderRede,
                "folderLocalTemp": folderLocalTemp,

                "emailRemetente": emailRemetente,
                "emailDestinatario": emailDestinatario,
                "emailCopia": emailCopia,

                "configFile": configFile,
                "configFileSheet": configFileSheet,
                }

            #Provide Output
            return dicCredentials, dicParameters

        except Exception as e:
            raise e