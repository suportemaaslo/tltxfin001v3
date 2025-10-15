import psycopg2
from psycopg2 import sql, Error
from typing import Optional, Dict, Any

class DBManager:
    def __init__(self, dicConfig: Dict[str, str], dicParameters: Dict[str, str]):
        #Atributos
        self.dicConfig = dicConfig
        self.dicParameters = dicParameters
        # Credenciais de conexão direta
        self.connection_params = {
            'user': self.dicConfig["credSupabaseUser"],
            'password': self.dicConfig["credSupabasePassword"],
            'host': self.dicConfig["credSupabaseHost"],
            'port': self.dicConfig["credSupabasePort"],
            'dbname': self.dicConfig["credSupabaseDBNAME"]
        }

        self.connection: Optional[psycopg2.extensions.connection] = None
        self.cursor: Optional[psycopg2.extensions.cursor] = None
    
    def connect(self) -> bool:
        try:
            self.connection = psycopg2.connect(**self.connection_params)
            self.cursor = self.connection.cursor()
            return True
        except Error as e:
            print(f"Erro ao conectar com o banco de dados: {e}")
            return False
        except Exception as e:
            print(f"Erro inesperado ao conectar: {e}")
            return False

    def disconnect(self):
        """
        Fecha a conexão com o banco de dados
        """
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
            print("Conexão fechada com sucesso")
        except Exception as e:
            print(f"Erro ao fechar conexão: {e}")
    
    def execute_query(self, query: str, params: tuple = None) -> Optional[list]:
        try:
            if not self.connection or self.connection.closed:
                if not self.connect():
                    return None
            
            self.cursor.execute(query, params)
            
            # Se for uma query SELECT, retorna os resultados
            if query.strip().upper().startswith('SELECT'):
                return self.cursor.fetchall()
            else:
                # Para INSERT, UPDATE, DELETE, etc.
                self.connection.commit()
                return [f"Query executada com sucesso. Linhas afetadas: {self.cursor.rowcount}"]
                
        except Error as e:
            print(f"Erro ao executar query: {e}")
            if self.connection:
                self.connection.rollback()
            return None
        except Exception as e:
            print(f"Erro inesperado ao executar query: {e}")
            return None

    def start_execution(self, status: str) -> Optional[int]:
        try:
            # Conectar ao banco se necessário
            if not self.connection or self.connection.closed:
                if not self.connect():
                    print("Falha ao conectar com o banco de dados")
                    return None
            
            # Obter o ID do robô dos parâmetros
            robot_id = self.dicParameters.get("robotIDProcess")
            if not robot_id:
                print("robotIDProcess não encontrado nos parâmetros")
                return None
            
            # Query para inserir nova execução
            insert_query = """
                INSERT INTO EXECUTIONS (IDROBOT, STATUS, START_TIME, CREATED_AT) 
                VALUES (%s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) 
                RETURNING IDEXECUTION;
            """
            # Executar a inserção
            self.cursor.execute(insert_query, (robot_id, status))
            # Obter o ID da execução criada
            execution_id = self.cursor.fetchone()[0]
            # Confirmar a transação
            self.connection.commit()
            print(f"Execução iniciada com sucesso. ID: {execution_id}, Robot ID: {robot_id}")
            return execution_id
            
        except Error as e:
            print(f"Erro ao iniciar execução: {e}")
            if self.connection:
                self.connection.rollback()
            return None
        except Exception as e:
            print(f"Erro inesperado ao iniciar execução: {e}")
            if self.connection:
                self.connection.rollback()
            return None

    def update_execution(self, execution_id: int, status: str) -> Optional[int]:
        try:
            # Conectar ao banco se necessário
            if not self.connection or self.connection.closed:
                if not self.connect():
                    print("Falha ao conectar com o banco de dados")
                    return None            
            # Query para atualizar o status da execução (SEM UPDATED_AT)
            update_query = """
                UPDATE EXECUTIONS 
                SET STATUS = %s, END_TIME = CURRENT_TIMESTAMP
                WHERE IDEXECUTION = %s;
            """
            # Executar a atualização
            self.cursor.execute(update_query, (status, execution_id))
            # Confirmar a transação
            self.connection.commit()
            print(f"Execução atualizada com sucesso. ID: {execution_id}, Novo status: {status}")
            return execution_id
            
        except Error as e:
            print(f"Erro ao atualizar execução: {e}")
            if self.connection:
                self.connection.rollback()
            return None
        except Exception as e:
            print(f"Erro inesperado ao atualizar execução: {e}")
            if self.connection:
                self.connection.rollback()
            return None

    def finish_execution(self, execution_id: int, status: str) -> Optional[int]:
        """
        Finaliza uma execução atualizando o status e definindo END_TIME
        """
        try:
            # Conectar ao banco se necessário
            if not self.connection or self.connection.closed:
                if not self.connect():
                    print("Falha ao conectar com o banco de dados")
                    return None            
            
            # Query para finalizar execução com END_TIME
            update_query = """
                UPDATE EXECUTIONS 
                SET STATUS = %s, END_TIME = CURRENT_TIMESTAMP
                WHERE IDEXECUTION = %s;
            """
            # Executar a atualização
            self.cursor.execute(update_query, (status, execution_id))
            # Confirmar a transação
            self.connection.commit()
            print(f"Execução finalizada com sucesso. ID: {execution_id}, Status final: {status}")
            return execution_id
            
        except Error as e:
            print(f"Erro ao finalizar execução: {e}")
            if self.connection:
                self.connection.rollback()
            return None
        except Exception as e:
            print(f"Erro inesperado ao finalizar execução: {e}")
            if self.connection:
                self.connection.rollback()
            return None

    def start_transaction(self, execution_id: int, transaction_data: Optional[str] = None, status: str = 'RUNNING') -> Optional[int]:
        try:
            # Conectar ao banco se necessário
            if not self.connection or self.connection.closed:
                if not self.connect():
                    print("Falha ao conectar com o banco de dados")
                    return None

            insert_query = """
                INSERT INTO TRANSACTION (IDEXECUTION, STATUS, TRANSACTION_DATA, START_TIME, CREATED_AT)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING IDTRANSACTION;
            """

            # Executa a inserção
            self.cursor.execute(insert_query, (execution_id, status, transaction_data))
            transaction_id = self.cursor.fetchone()[0]
            self.connection.commit()
            print(f"Transação iniciada com sucesso. ID: {transaction_id}, Execução: {execution_id}")
            return transaction_id

        except Error as e:
            print(f"Erro ao iniciar transação: {e}")
            if self.connection:
                self.connection.rollback()
            return None
        except Exception as e:
            print(f"Erro inesperado ao iniciar transação: {e}")
            if self.connection:
                self.connection.rollback()
            return None

    def update_transaction(self, transaction_id: int, status: str, transaction_data: Optional[str] = None) -> Optional[int]:
        """
        Atualiza uma transação existente seguindo o padrão de update_execution:
        - Atualiza STATUS
        - Opcionalmente atualiza TRANSACTION_DATA
        - Define END_TIME = CURRENT_TIMESTAMP
        Retorna o IDTRANSACTION atualizado.
        """
        try:
            # Conectar ao banco se necessário
            if not self.connection or self.connection.closed:
                if not self.connect():
                    print("Falha ao conectar com o banco de dados")
                    return None

            if transaction_data is not None:
                update_query = """
                    UPDATE TRANSACTION
                    SET STATUS = %s, TRANSACTION_DATA = %s, END_TIME = CURRENT_TIMESTAMP
                    WHERE IDTRANSACTION = %s;
                """
                params = (status, transaction_data, transaction_id)
            else:
                update_query = """
                    UPDATE TRANSACTION
                    SET STATUS = %s, END_TIME = CURRENT_TIMESTAMP
                    WHERE IDTRANSACTION = %s;
                """
                params = (status, transaction_id)

            # Executa a atualização
            self.cursor.execute(update_query, params)
            self.connection.commit()
            print(f"Transação atualizada com sucesso. ID: {transaction_id}, Novo status: {status}")
            return transaction_id

        except Error as e:
            print(f"Erro ao atualizar transação: {e}")
            if self.connection:
                self.connection.rollback()
            return None
        except Exception as e:
            print(f"Erro inesperado ao atualizar transação: {e}")
            if self.connection:
                self.connection.rollback()
            return None

    def test_connection(self) -> Dict[str, Any]:
        test_result = {
            'status': 'failed',
            'message': '',
            'connection_info': {}
        }
        
        try:
            if not self.connect():
                test_result['message'] = 'Falha na conexão com o banco'
                return test_result
            
            # Teste básico de conexão
            self.cursor.execute("SELECT version();")
            db_version = self.cursor.fetchone()
            
            # Informações da conexão
            self.cursor.execute("SELECT current_database(), current_user;")
            db_info = self.cursor.fetchone()
            
            test_result['connection_info'] = {
                'database': db_info[0],
                'user': db_info[1],
                'version': db_version[0]
            }
            
            test_result['status'] = 'success'
            test_result['message'] = 'Conexão estabelecida com sucesso'
            
            print("Teste de conexão realizado com sucesso")
            
        except Error as e:
            test_result['message'] = f'Erro durante o teste: {e}'
            print(f"Erro durante teste de conexão: {e}")
            raise e
        except Exception as e:
            test_result['message'] = f'Erro inesperado: {e}'
            print(f"Erro inesperado durante teste: {e}")
            raise e
        finally:
            self.disconnect()
        
        return test_result
