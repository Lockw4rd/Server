import socket
import threading

# Servidor de Bate-Papo Concorrente

class Cliente:
    def __init__(self, conn, endereco):
        self.conn = conn
        self.endereco = endereco
        self.nickname = None

# Estrutura de dados compartilhada
clientes = []
lock = threading.Lock()

# Auxiliar para enviar mensagem codificada garantindo quebras de linha.
def enviar_para_socket(sock, texto):
    try:
        sock.send((texto + "\n").encode('utf-8'))
    except (BrokenPipeError, ConnectionResetError):
        pass

# Envia mensagem para todos os clientes registrados (exceto o remetente).
def broadcast(msg, remetente=None):
    with lock:
        para_remover = []
        for cliente in clientes:
            if cliente.nickname is not None and cliente != remetente:
                try:
                    cliente.conn.send((msg + "\n").encode('utf-8'))
                except (BrokenPipeError, ConnectionResetError):
                    para_remover.append(cliente)
        
        for c in para_remover:
            remover_cliente(c)

# Remove cliente da lista e fecha o socket com seguranca.
def remover_cliente(cliente):
    with lock:
        if cliente in clientes:
            clientes.remove(cliente)
    try:
        cliente.conn.close()
    except Exception:
        pass

# Processa a mensagem/comando do cliente conforme o Protocolo de Aplicação.
def tratar_comando(cliente, linha):
    partes = linha.strip().split(" ", 2)
    comando = partes[0].upper()

    # REGISTRO DE NICKNAME
    if comando == "/NICK":
        if len(partes) < 2 or not partes[1].strip():
            enviar_para_socket(cliente.conn, "400 ERROR Uso correto: /NICK <seu_nickname>")
            return

        novo_nick = partes[1].strip()

        if novo_nick.upper() == "ALL":
            enviar_para_socket(cliente.conn, "400 ERROR O nickname 'ALL' eh reservado.")
            return

        with lock:
            # Validação de Nickname Único (Requisito 7)
            if any(c.nickname and c.nickname.lower() == novo_nick.lower() for c in clientes):
                enviar_para_socket(cliente.conn, f"409 CONFLICT Nickname '{novo_nick}' ja esta em uso.")
                return

            nick_antigo = cliente.nickname
            cliente.nickname = novo_nick

        if nick_antigo is None:
            enviar_para_socket(cliente.conn, f"200 OK Bem-vindo(a), {novo_nick}!")
            broadcast(f"300 INFO {novo_nick} entrou no chat.", remetente=cliente)
            print(f"[+] {cliente.endereco} registrou o nickname '{novo_nick}'")
        else:
            enviar_para_socket(cliente.conn, f"200 OK Nickname alterado para '{novo_nick}'.")
            broadcast(f"300 INFO {nick_antigo} alterou o nickname para {novo_nick}.", remetente=cliente)

    # LISTAR USUÁRIOS CONECTADOS
    elif comando == "/LIST":
        with lock:
            nicks = [c.nickname for c in clientes if c.nickname is not None]
        
        lista_str = ", ".join(nicks) if nicks else "Nenhum usuario registrado."
        enviar_para_socket(cliente.conn, f"200 LIST Usuarios online ({len(nicks)}): {lista_str}")

    # MENSAGEM (UNICAST OU BROADCAST)
    elif comando == "/MSG":
        if cliente.nickname is None:
            enviar_para_socket(cliente.conn, "401 UNAUTHORIZED Voce precisa definir um nickname primeiro com /NICK <nome>")
            return

        if len(partes) < 3:
            enviar_para_socket(cliente.conn, "400 ERROR Uso correto: /MSG <destino|ALL> <mensagem>")
            return

        destino = partes[1].strip()
        texto = partes[2].strip()

        if destino.upper() == "ALL":
            # Broadcast
            print(f"[{cliente.nickname} -> ALL] {texto}")
            broadcast(f"MSG_PUBLIC {cliente.nickname}: {texto}", remetente=cliente)
            enviar_para_socket(cliente.conn, f"200 OK Mensagem enviada para todos.")
        else:
            # Unicast (Mensagem Privada)
            destinatario_cliente = None
            with lock:
                for c in clientes:
                    if c.nickname and c.nickname.lower() == destino.lower():
                        destinatario_cliente = c
                        break
            
            if destinatario_cliente:
                enviar_para_socket(destinatario_cliente.conn, f"MSG_PRIVATE [{cliente.nickname} (reservado)]: {texto}")
                enviar_para_socket(cliente.conn, f"200 OK Mensagem privada enviada para {destinatario_cliente.nickname}.")
                print(f"[{cliente.nickname} -> {destinatario_cliente.nickname} (PVT)] {texto}")
            else:
                enviar_para_socket(cliente.conn, f"404 NOT_FOUND Usuario '{destino}' nao encontrado.")

    # SAIR
    elif comando == "/QUIT":
        enviar_para_socket(cliente.conn, "200 OK Conexao encerrada pelo usuario.")
        raise ConnectionResetError("Cliente solicitou saída com /QUIT.")

    else:
        enviar_para_socket(cliente.conn, "400 UNKNOWN_COMMAND Comando invalido. Use /NICK, /MSG, /LIST ou /QUIT.")


def tratar_cliente(cliente):
    print(f"[+] Cliente conectado: {cliente.endereco}")
    enviar_para_socket(cliente.conn, "200 CONNECTED Servidor Bate-Papo v2.0. Use /NICK <nome> para registrar seu usuario.")

    while True:
        try:
            dados = cliente.conn.recv(1024)
            if not dados:
                break

            mensagens = dados.decode('utf-8', errors='ignore').split("\n")
            for msg in mensagens:
                if msg.strip():
                    tratar_comando(cliente, msg.strip())

        except (ConnectionResetError, BrokenPipeError):
            break
        except Exception as e:
            print(f"[!] Erro inesperado com {cliente.endereco}: {e}")
            break

    # Desconexão
    nick_saindo = cliente.nickname or f"{cliente.endereco[0]}:{cliente.endereco[1]}"
    print(f"[-] Cliente desconectado: {nick_saindo}")
    remover_cliente(cliente)
    if cliente.nickname:
        broadcast(f"300 INFO Usuario {cliente.nickname} saiu do chat.")


def main():
    HOST = "0.0.0.0"
    PORT = 5000

    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((HOST, PORT))
    servidor.listen()

    print(f"[*] Servidor iniciado em {HOST}:{PORT}")
    print("[*] Aguardando conexões...")

    while True:
        try:
            conn, endereco = servidor.accept()
            cliente = Cliente(conn, endereco)

            with lock:
                clientes.append(cliente)

            thread = threading.Thread(target=tratar_cliente, args=(cliente,))
            thread.daemon = True
            thread.start()
        except KeyboardInterrupt:
            print("\n[*] Encerrando o servidor...")
            servidor.close()
            break

if __name__ == "__main__":
    main()
