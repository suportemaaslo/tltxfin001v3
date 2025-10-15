from src.services import Services; services = Services()

class main:
    try:
        #Teste de Conexao do Banco
        connectionTest = services.bdManager.test_connection()
        #Gerando ID de Execution - STATUS TEMPLATE > 'SUCCESS', 'FAILURE', 'RUNNING', 'PENDING', 'STARTING'
        executionID = services.bdManager.start_execution('STARTING')
        services.logger.set_execution_id(executionID)
        # Enviar email de início da execução
        ####services.gmail.enviaremail('Start',f"Processo {services.dicParameters.get('robotName')} iniciado",executionID)
        services.logger.log_info("main", f"ExecutionID: {executionID} - Process: {services.dicParameters.get('processName')} - Status: STARTING")
        #Atualizando o Status da Execução
        services.bdManager.update_execution(executionID, 'RUNNING')

        # Get Transaction Data (Cada def Precisa de Log para Entrada Processo e Saída)
        dfConfig, lstFileInput = services.arquivoInput.verificarPasta()
        lstFileProcess = services.arquivoInput.movimentarArquivoParaLocal(dfConfig, lstFileInput)


        # Process Item Transaction Data
        for itemListFile in lstFileProcess:
            try:
                ## Here is a Iterator
                itemData = services.bdManager.start_transaction(executionID, transaction_data=f"Item File: {itemListFile}", status='RUNNING')
                # Vincular o ID da transação ao logger para que seja gravado em LOG.IDTRANSACTION
                services.logger.set_transaction_id(itemData)
                services.logger.log_info("main", f"Inicio do Processo Item: {itemListFile} - ItemID: {itemData} - Status: RUNNING")
                #Core Item Run
                print("Teste")
                
                # Update Item Transaction status
                services.bdManager.update_transaction(itemData, 'SUCCESS')
                services.logger.log_info("main", f"Fim Processo Item: {itemListFile} - Status: SUCCESS")
            except Exception as e:
                # Em erros, envie também a linha do erro no corpo do e-mail
                services.logger.log_error("main", f"Error: {str(e)} - Line: {services.traceback.extract_tb(e.__traceback__)[0][1]}")
                services.logger.clear_transaction_id()
            finally:
                # Fora do bloco de transação, o ID é opcional (não enviar)
                services.logger.clear_transaction_id()

        #Finalizando Execução do Processo
        services.bdManager.update_execution(executionID, 'SUCCESS')
        # Enviar email de conclusão da execução
        services.logger.clear_transaction_id()
        ####services.gmail.enviaremail('Finish', f"Processo {services.dicParameters.get('robotName')} concluído com sucesso", executionID)
        services.logger.log_info("main", f"ExecutionID: {executionID} - Process: {services.dicParameters.get('processName', 'N/A')} - Status: SUCCESS")
    except Exception as e:
        #Atualizando o Status da Execução
        ####services.gmail.enviaremail('Error', f"Erro na execução do processo {services.dicParameters.get('robotName')}", executionID, idtransacao="", mensagem=f"Error: {str(e)} - Line: {services.traceback.extract_tb(e.__traceback__)[0][1]}")
        services.bdManager.update_execution(executionID, 'FAILURE')
        services.logger.log_error("main", f"Error: {str(e)} - Line: {services.traceback.extract_tb(e.__traceback__)[0][1]}")
    finally:
        services.logger.log_info("main", f"ExecutionID: {executionID} - Process: {services.dicParameters.get('processName', 'N/A')} - Status: FINISHED")
if __name__ == "__main__":
    main()