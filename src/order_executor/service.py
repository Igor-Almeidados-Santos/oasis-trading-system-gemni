import os

import grpc
from concurrent import futures
from src.contracts_generated import trading_system_pb2
from src.contracts_generated import trading_system_pb2_grpc
from .client import CoinbaseClient
from src.common.db_manager import PostgresManager

class ExecutionService(trading_system_pb2_grpc.ExecutionServiceServicer):
    def __init__(self):
        self.coinbase_client = CoinbaseClient()
        self.db_manager = PostgresManager()  
        print("ExecutionService iniciado.")

    def PlaceLimitBuyOrder(self, request: trading_system_pb2.OrderRequest, context):
        try:
            # 1. Primeiro, insere a ordem no DB com status 'PENDING'
            insert_query = """
            INSERT INTO orders (client_order_id, product_id, exchange, side, quantity, price, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            # client_order_id viria do RiskEngine, por agora geramos um
            client_order_id = f"test-{request.symbol}-{request.price}"
            self.db_manager.execute_query(
                insert_query,
                (
                    client_order_id,
                    request.symbol,
                    os.getenv("DEFAULT_EXCHANGE", "coinbase"),
                    'BUY',
                    request.quantity,
                    request.price,
                    'PENDING',
                ),
            )

            # 2. Envia a ordem para a exchange
            result = self.coinbase_client.create_limit_buy_order(
                symbol=request.symbol,
                quantity=request.quantity,
                price=request.price
            )

            # 3. Atualiza a ordem no DB com o ID da exchange e o status 'NEW'
            update_query = "UPDATE orders SET exchange_order_id = %s, status = %s WHERE client_order_id = %s"
            self.db_manager.execute_query(
                update_query,
                (result['orderId'], result['status'], client_order_id)
            )

            return trading_system_pb2.OrderResponse(
                order_id=str(result['orderId']),
                status=result['status']
            )
        except Exception as e:
            # Em caso de falha, atualiza o status para 'FAILED'
            # (a lógica de rollback seria mais complexa)
            print(f"Erro na execução, marcando ordem como FAILED: {e}")
            fail_query = "UPDATE orders SET status = %s WHERE client_order_id = %s"
            self.db_manager.execute_query(fail_query, ('FAILED', client_order_id))
            
            context.set_details(f"Erro na API da Coinbase: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return trading_system_pb2.OrderResponse()
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    trading_system_pb2_grpc.add_ExecutionServiceServicer_to_server(ExecutionService(), server)
    server.add_insecure_port('[::]:50052')
    server.start()
    print("Servidor ExecutionService escutando na porta 50052.")
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
