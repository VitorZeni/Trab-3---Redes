import socket
import os
import threading

# --- Configurações ---
ENCODING = 'utf-8' # HTTP usa UTF-8 por padrão para texto
IP = '0.0.0.0' # Escuta em todas as interfaces de rede disponíveis
PORTA = 8080
BUFFER_SIZE = 4096

def get_content_type(caminho_arquivo):
    """ Determina o Content-Type (MIME type) baseado na extensão do arquivo. """
    if caminho_arquivo.endswith(".html"):
        return "text/html"
    elif caminho_arquivo.endswith(".jpg") or caminho_arquivo.endswith(".jpeg"):
        return "image/jpeg"
    elif caminho_arquivo.endswith(".png"):
        return "image/png"
    elif caminho_arquivo.endswith(".css"):
        return "text/css"
    else:
        # Tipo genérico para download de arquivos binários
        return "application/octet-stream"

def handle_client(conn, addr):
    """
    Função executada em uma thread para cada cliente conectado.
    Processa uma única requisição HTTP e fecha a conexão.
    """
    print(f"[NOVA CONEXÃO] {addr} conectado.")

    try:
        # 1. Recebe a requisição completa do browser
        dados_requisicao = conn.recv(BUFFER_SIZE).decode(ENCODING)
        if not dados_requisicao:
            print(f"[{addr}] Browser desconectou sem enviar dados.")
            return

        # Imprime a requisição para fins de depuração
        print(f"[{addr}] Requisição recebida:\n---INICIO---\n{dados_requisicao.strip()}\n----FIM-----\n")

        # 2. Analisa (Parse) a linha de requisição HTTP
        # Ex: "GET /index.html HTTP/1.1"
        header_lines = dados_requisicao.split('\r\n')
        linha_de_requisicao = header_lines[0]
        partes = linha_de_requisicao.split()

        # Validação básica da requisição
        if len(partes) < 2 or partes[0].upper() != 'GET':
            # Ignora requisições malformadas ou que não sejam GET
            print(f"[{addr}] Requisição inválida ou não suportada.")
            return

        metodo = partes[0]
        caminho_url = partes[1]

        # Se o caminho for "/", sirva o "index.html" por padrão
        if caminho_url == '/':
            caminho_url = '/index.html'

        # Monta o caminho local para o arquivo, removendo a barra inicial
        # Assumimos que os arquivos web (html, jpg) estão no mesmo diretório do script
        caminho_arquivo = caminho_url.strip('/')

        # 3. Trata a requisição: Envia o arquivo ou um erro 404
        if os.path.exists(caminho_arquivo) and os.path.isfile(caminho_arquivo):
            # --- ARQUIVO ENCONTRADO - Resposta 200 OK ---
            print(f"[{addr}] Servindo arquivo: {caminho_arquivo}")

            # Pega o tamanho e o tipo do conteúdo
            tamanho_arquivo = os.path.getsize(caminho_arquivo)
            content_type = get_content_type(caminho_arquivo)

            # Monta o cabeçalho da resposta HTTP
            # A linha de status (HTTP/1.1 200 OK)
            # Os headers (Content-Type, Content-Length)
            # Uma linha em branco (\r\n) para separar o cabeçalho do corpo
            cabecalho_http = (
                f"HTTP/1.1 200 OK\r\n"
                f"Content-Type: {content_type}\r\n"
                f"Content-Length: {tamanho_arquivo}\r\n"
                f"Connection: close\r\n" # Informa ao browser para fechar a conexão após a resposta
                f"\r\n" # Linha em branco crucial
            )
            conn.sendall(cabecalho_http.encode(ENCODING))

            # Envia o corpo da resposta (o conteúdo do arquivo) em pedaços
            with open(caminho_arquivo, 'rb') as f:
                while True:
                    bloco = f.read(BUFFER_SIZE)
                    if not bloco:
                        break # Fim do arquivo
                    conn.sendall(bloco)
            print(f"[{addr}] Arquivo '{caminho_arquivo}' enviado com sucesso.")

        else:
            # --- ARQUIVO NÃO ENCONTRADO - Resposta 404 Not Found ---
            print(f"[{addr}] Arquivo não encontrado: {caminho_arquivo}")

            corpo_erro = (
                f"<html>"
                f"<head><title>404 Not Found</title></head>"
                f"<body><h1>404 Not Found</h1><p>O arquivo '{caminho_arquivo}' nao foi encontrado neste servidor.</p></body>"
                f"</html>"
            ).encode(ENCODING)

            cabecalho_http = (
                f"HTTP/1.1 404 Not Found\r\n"
                f"Content-Type: text/html\r\n"
                f"Content-Length: {len(corpo_erro)}\r\n"
                f"Connection: close\r\n"
                f"\r\n"
            )
            
            # Envia o cabeçalho e o corpo do erro
            conn.sendall(cabecalho_http.encode(ENCODING))
            conn.sendall(corpo_erro)
            print(f"[{addr}] Resposta de erro 404 enviada.")

    except (ConnectionResetError, BrokenPipeError) as e:
        print(f"[{addr}] Conexão fechada pelo cliente: {e}")
    except Exception as e:
        print(f"[{addr}] Erro inesperado: {e}")
    finally:
        # 4. Fecha a conexão com este cliente
        print(f"[{addr}] Fechando conexão.")
        conn.close()

def main():
    # Criação e configuração do socket do servidor
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        servidor.bind((IP, PORTA))
        servidor.listen(5)
        local_ip = socket.gethostbyname(socket.gethostname())
        print(f"=== Servidor HTTP Simplificado ===")
        print(f"Escutando em {IP}:{PORTA}")
        print(f"Acesse no seu browser: http://{local_ip}:{PORTA} ou http://127.0.0.1:{PORTA}")
        print("Pressione Ctrl+C para encerrar.")
    except socket.error as e:
        print(f"Erro no bind do socket: {e}")
        exit()

    # Loop principal que aguarda novas conexões
    try:
        while True:
            conn, addr = servidor.accept()
            # Para cada nova conexão, cria e inicia uma thread para lidar com ela
            thread_cliente = threading.Thread(target=handle_client, args=(conn, addr))
            thread_cliente.start()
    except KeyboardInterrupt:
        print("\nServidor sendo encerrado...")
    finally:
        servidor.close()
        print("Servidor encerrado.")

if __name__ == "__main__":
    main()