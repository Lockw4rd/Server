# RELATÓRIO TÉCNICO DO PROJETO: SISTEMA DE BATE-PAPO MULTIUSUÁRIO COM SOCKETS

---

## 1. Descrição da Aplicação e Arquitetura da Solução

### 1.1 Problema Resolvido
Em sistemas distribuídos e redes de computadores, a troca de mensagens em tempo real exige uma infraestrutura capaz de gerenciar múltiplos fluxos contínuos de comunicação, manter o estado das conexões e garantir a integridade dos dados trafegados. 

Esta aplicação resolve o problema de **comunicação simultânea e bidirecional entre múltiplos usuários em rede**, fornecendo um ambiente de bate-papo em tempo real (*chat*) com suporte a transmissões em massa (*broadcast*), mensagens privadas (*unicast/PVT*), controle de acesso por apelidos (*nicknames*) e monitoramento de presença de usuários online.

### 1.2 Arquitetura da Solução
A solução adota uma arquitetura **Cliente-Servidor Concorrente**, fundamentada no uso de **Sockets POSIX/TCP** e **Multithreading** em Python.

* **Servidor (`servidor.py`):**
  * Atua como ponto central da rede (escutando na porta `5000` em `0.0.0.0`).
  * Mantém o estado global da aplicação em uma lista de objetos `Cliente`, contendo a referência da conexão (`socket`), endereço de IP/Porta e o `nickname` registrado.
  * Executa uma thread dedicada para cada cliente conectado para processar requisições em paralelo.
  * Utiliza um mecanismo de exclusão mútua (`threading.Lock()`) para garantir segurança de memória (*thread safety*) no acesso e modificação das conexões compartilhadas.

* **Cliente (`meu_cliente.py`):**
  * Interface de linha de comando (CLI) que se conecta ao servidor no endereço IP de destino.
  * Implementa concorrência interna com duas threads ativas:
    1. **Thread de Envio (Loop Principal):** Captura entradas do usuário no terminal (`input()`), aplica atalhos de protocolo e transmite via socket.
    2. **Thread de Recepção (Segundo Plano/Daemon):** Escuta continuamente as respostas do servidor e exibe as mensagens assincronamente na tela, sem travar a digitação do usuário.

---

## 2. Protocolo de Transporte Utilizado e Justificativa

### 2.1 Protocolo Escolhido: TCP (Transmission Control Protocol)
A aplicação utiliza exclusivamente o protocolo **TCP** na Camada de Transporte, configurado através da constante `socket.SOCK_STREAM` da família `socket.AF_INET`.

### 2.2 Justificativa da Escolha
A escolha do TCP é estritamente alinhada às necessidades funcionais da aplicação de bate-papo:

1. **Orientação à Conexão e Confiabilidade:** 
   O TCP realiza o aperto de mão em três vias (*Three-Way Handshake*) antes da troca de dados. Em um sistema de texto, a perda de um único pacote contendo um comando (como `/NICK` ou `/MSG`) corromperia a semântica da conversa. O TCP garante a retransmissão automática de pacotes perdidos.
2. **Garantia de Ordenação dos Dados:** 
   As mensagens do chat e os comandos de controle precisam ser processados na exata ordem em que foram enviados. O TCP numera os segmentos e os reordena no receptor.
3. **Orientação a Fluxo de Bytes (*Byte Stream*):** 
   Permite o envio contínuo de caracteres estruturados, onde a terminação de linha `\n` serve como delimitador de mensagem na camada de aplicação.
4. **Controle de Fluxo e Congestionamento:** 
   Impede que um servidor muito rápido sobrecarregue um cliente lento ou que o tráfego de mensagens congestione o enlace da rede.

---

## 3. Descrição do Protocolo de Aplicação e Formato das Mensagens

Para padronizar a comunicação entre clientes e servidor, foi criado um **Protocolo de Aplicação Textual de Alto Nível baseado em Comandos e Códigos de Status**.

### 3.1 Estruturação dos Dados
* **Delimitador de Pacote:** Todas as mensagens trafegadas na rede terminam obrigatoriamente com o caractere de quebra de linha (`\n`), codificadas no padrão `UTF-8`.
* **Requisições (Cliente -> Servidor):** Seguem o formato `<COMANDO> [PARÂMETROS]\n`.
* **Respostas/Notificações (Servidor -> Cliente):** Seguem o formato `<CÓDIGO> <CATEGORIA/TIPO> [CONTEÚDO]\n`.

### 3.2 Tabela de Comandos do Cliente

| Comando | Sintaxe | Descrição | Exemplo |
| :--- | :--- | :--- | :--- |
| `/NICK` | `/NICK <nome>` | Registra ou altera o apelido único do cliente na sessão. | `/NICK Maria` |
| `/LIST` | `/LIST` | Requisita a lista de apelidos de todos os usuários online. | `/LIST` |
| `/MSG` | `/MSG <destino> <texto>` | Envia mensagem pública (se `destino` = `ALL`) ou privada (se `destino` = `<nickname>`). | `/MSG ALL Olá!` ou `/MSG Joao Oi!` |
| `/QUIT` | `/QUIT` | Notifica o servidor e solicita o encerramento seguro da conexão. | `/QUIT` |

### 3.3 Tabela de Respostas e Notificações do Servidor

| Código/Identificador | Categoria | Descrição | Exemplo de Retorno |
| :--- | :--- | :--- | :--- |
| `200` | `OK / LIST / CONNECTED` | Operação realizada com sucesso ou confirmação. | `200 OK Bem-vindo(a), Maria!` |
| `300` | `INFO` | Notificação do sistema sobre eventos globais da rede. | `300 INFO Joao entrou no chat.` |
| `400` | `ERROR / UNKNOWN` | Erro de sintaxe, comando desconhecido ou falta de parâmetros. | `400 ERROR Uso correto: /NICK <nome>` |
| `401` | `UNAUTHORIZED` | Tentativa de enviar mensagens sem ter registrado um nickname. | `401 UNAUTHORIZED Voce precisa...` |
| `404` | `NOT_FOUND` | Usuário de destino de mensagem privada não existe ou está offline. | `404 NOT_FOUND Usuario 'Pedro' nao encontrado.` |
| `409` | `CONFLICT` | Tentativa de registrar um nickname que já está em uso por outro nó. | `409 CONFLICT Nickname 'Maria' ja esta em uso.` |
| `MSG_PUBLIC` | Repasse Broadcast | Mensagem transmitida publicamente para todos. | `MSG_PUBLIC Maria: Olá a todos` |
| `MSG_PRIVATE` | Repasse Unicast | Mensagem privada recebida diretamente de outro usuário. | `MSG_PRIVATE [Maria (reservado)]: Oi!` |

---

## 4. Fluxo de Comunicação e Atendimento Simultâneo

### 4.1 Tratamento de Concorrência no Servidor
O servidor suporta múltiplos acessos simultâneos utilizando **Threads de Execução Paralelas**:
1. A thread principal roda um loop infinito preso na instrução `servidor.accept()`.
2. Quando um cliente se conecta, o sistema operacional estabelece um novo socket de conexão e retorna o par `(conn, endereco)`.
3. O servidor empacota a conexão num objeto `Cliente`, armazena na lista global sob proteção de um `threading.Lock()` e dispara uma thread *daemon* dedicada executando `tratar_cliente(cliente)`.
4. A nova thread passa a responder exclusivamente àquele socket, liberando a thread principal para aceitar novas conexões imediatamente.

---

## 5. Tratamento de Erros e Desconexões

1. **Nicknames Duplicados e Reservados:**
   Se um cliente tenta se registrar com um nome que já pertence a outro usuário conectado (comparação *case-insensitive*), o servidor recusa o pedido enviando a resposta `409 CONFLICT`. O apelido `ALL` é bloqueado (`400 ERROR`).
2. **Queda Abrupta de Clientes:**
   Se o programa do cliente for fechado involuntariamente, as chamadas de I/O no servidor disparam exceções do tipo `ConnectionResetError` ou `BrokenPipeError`. O servidor captura esses erros, remove o cliente da lista com proteção de *lock* e notifica a rede com `300 INFO`.
3. **Queda do Servidor / Desconexão do Lado do Cliente:**
   A thread de recepção do cliente monitora o retorno de `sock.recv(1024)`. Se retornar um valor vazio (`b""`), o cliente imprime um aviso amigável e força a saída imediata chamando `os._exit(0)`.
4. **Mensagens Incompletas e Fragmentadas:**
   As leituras de stream são decodificadas e divididas por quebras de linha (`.split("\n")`), prevenindo que pacotes fragmentados corrompam a execução.

---

## 6. Instruções para Execução

### 6.1 Pré-requisitos
* **Linguagem:** Python 3.8 ou superior instalado.
* **Rede:** Ambiente local (Loopback `127.0.0.1`) ou máquinas distintas na mesma rede local.

### 6.2 Passo a Passo

1. **Iniciando o Servidor:**
   ```bash
   python servidor.py
   ```
2. **Iniciando os Clientes:**
   ```bash
   python meu_cliente.py
   ```
3. **Exemplo de Comandos no Terminal:**
   ```plaintext
   > /NICK Maria
   > /LIST
   > /MSG ALL Olá pessoal!
   > /MSG Joao Oi em privado!
   > /QUIT
   ```

---

## 7. Conclusões

O projeto desenvolvido cumpre integralmente os requisitos propostos para uma aplicação distribuída baseada em sockets. A utilização direta da API de Sockets POSIX e da biblioteca de threading nativa do Python permitiu compreender a dinâmica de baixo nível dos protocolos de rede, destacando-se a separação clara entre as camadas de transporte e aplicação, a eficiência no tratamento de concorrência e a resiliência a falhas de comunicação.