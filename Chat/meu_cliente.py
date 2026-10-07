import socket
import threading
import sys
import os

# Thread dedicada para escutar respostas do servidor em tempo real.
def receber_mensagens(sock):
    while True:
        try:
            dados = sock.recv(1024)
            if not dados:
                print("\n[!] O servidor encerrou a conexao.")
                os._exit(0)  # Encerra o processo cliente imediatamente
            
            mensagens = dados.decode('utf-8', errors='ignore').split("\n")
            for msg in mensagens:
                if msg.strip():
                    print(f"\n{msg.strip()}\n> ", end="")
        except:
            print("\n[!] Erro de comunicacao com o servidor.")
            os._exit(0)

def main():
    HOST = "127.0.0.1"
    PORT = 5000

    try:
        cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cliente.connect((HOST, PORT))
    except Exception as e:
        print(f"[!] Nao foi possivel conectar ao servidor: {e}")
        sys.exit(1)

    # Thread para escutar mensagens do servidor
    thread_rec = threading.Thread(target=receber_mensagens, args=(cliente,))
    thread_rec.daemon = True
    thread_rec.start()

    print("=== BEM-VINDO AO CHAT MULTIUSUÁRIO ===")
    print("Comandos do Protocolo:")
    print("  /NICK <seu_nome>         -> Registrar ou alterar seu apelido")
    print("  /LIST                    -> Listar usuarios online")
    print("  /MSG ALL <texto>         -> Enviar mensagem pública para todos")
    print("  /MSG <nickname> <texto>  -> Enviar mensagem privada")
    print("  /QUIT                    -> Sair do bate-papo\n")

    while True:
        try:
            texto = input("> ").strip()
            if not texto:
                continue

            # Atalho: Se o usuário esquecer o comando /MSG e já estiver registrado, envia em broadcast
            if not texto.startswith("/"):
                texto = f"/MSG ALL {texto}"

            cliente.send((texto + "\n").encode('utf-8'))

            if texto.upper() == "/QUIT":
                print("Saindo...")
                cliente.close()
                sys.exit(0)

        except KeyboardInterrupt:
            print("\n\nSaindo (Ctrl+C)...")
            try:
                cliente.send("/QUIT\n".encode('utf-8'))
                cliente.close()
            except:
                pass
            sys.exit(0)
        except Exception as e:
            print(f"[!] Erro de envio: {e}")
            break

if __name__ == "__main__":
    main()
