# ComputerNetwork_SocketProgramming
# Hybrid FTP Application

A socket programming project that implements a **Hybrid FTP** system using:

- **TCP** for the control channel: commands, replies, login state, and session management.
- **UDP** for the data channel: file upload/download payloads.
- A custom **Reliable Data Transfer (RDT)** layer on top of UDP using sequence numbers, ACKs, checksums, timeout, and retransmission.

This project is designed for the *Internetworking Protocols* lab project: **Design and Implementation of the Hybrid FTP Application**.

---

## 1. Description

The application aims to demonstrate how an FTP-like system can separate the control plane and data plane:

| Channel | Protocol | Purpose |
|---|---|---|
| Control Channel | TCP | Send FTP commands, server reply codes, authentication, and session state |
| Data Channel | UDP | Transfer actual file data using a custom reliability mechanism |

The project supports the following core features:

- Basic user authentication using `USER` and `PASS`.
- FTP-style command handling over TCP.
- File listing and directory navigation.
- File upload and download over UDP.
- Custom reliable UDP transfer using Stop-and-Wait.
- Packet checksum validation.
- Duplicate packet handling.
- Timeout and retransmission.
- SHA-256 file hash verification.
- Multi-client server structure using threads.

---

## 2. Project Structure

```txt
hybrid_ftp/
│
├── README.md
├── requirements.txt
├── .gitignore
│
├── config/
│   ├── users.json
│   └── server_config.json
│
├── data/
│   ├── server_root/
│   │   └── sample.txt
│   └── client_downloads/
│
├── docs/
│   ├── protocol.md
│   ├── udp_rdt_design.md
│   └── manual_test_plan.md
│
├── report/
│   ├── genai_log.md
│   └── diagrams/
│
├── hybridftp/
│   ├── __init__.py
│   │
│   ├── common/
│   │   ├── __init__.py
│   │   ├── constants.py
│   │   ├── ftp_reply.py
│   │   ├── logger.py
│   │   ├── checksum.py
│   │   └── file_utils.py
│   │
│   ├── protocol/
│   │   ├── __init__.py
│   │   ├── command.py
│   │   ├── command_parser.py
│   │   └── udp_packet.py
│   │
│   ├── rdt/
│   │   ├── __init__.py
│   │   ├── reliable_udp_sender.py
│   │   ├── reliable_udp_receiver.py
│   │   └── rdt_config.py
│   │
│   ├── server/
│   │   ├── __init__.py
│   │   ├── ftp_server.py
│   │   ├── client_session.py
│   │   ├── command_handler.py
│   │   ├── auth_service.py
│   │   ├── file_service.py
│   │   └── session_manager.py
│   │
│   └── client/
│       ├── __init__.py
│       ├── ftp_client.py
│       ├── client_cli.py
│       └── progress_printer.py
│
├── server_main.py
├── client_main.py
│
└── tests/
    ├── test_command_parser.py
    ├── test_udp_packet.py
    └── test_checksum.py
```

---

## 3. Folder Responsibilities

### `config/`

Stores application-level runtime configuration.

| File | Responsibility |
|---|---|
| `users.json` | Stores simple username/password pairs for authentication |
| `server_config.json` | Stores server host, TCP control port, server root path, UDP timeout, buffer size, and retry limit |



---

### `data/`

Stores files used during upload/download testing.

| Folder | Responsibility |
|---|---|
| `server_root/` | The FTP server's root directory. Clients can only access files inside this folder. |
| `client_downloads/` | Stores files downloaded by the client. |


---

### `docs/`

Stores technical design notes and manual testing documents.

| File | Responsibility |
|---|---|
| `protocol.md` | Describes the TCP control flow, UDP data flow, FTP commands, and reply code format |
| `udp_rdt_design.md` | Describes the custom UDP packet header and reliable transfer mechanism |
| `manual_test_plan.md` | Contains step-by-step manual test cases for demo preparation |

---

### `report/`

Stores final report materials.

| File/Folder | Responsibility |
|---|---|
| `genai_log.md` | Documents all GenAI prompts, raw outputs, and manual refinements |
| `diagrams/` | Stores sequence diagrams, flowcharts, and state machines used in the report |


---

### `hybridftp/`

Main Python package that contains the application source code.

---

## 4. Source Code Modules

### `hybridftp/common/`

Contains utilities shared by both client and server.

| File | Responsibility |
|---|---|
| `constants.py` | Stores shared constants such as encoding, default host, default port, timeout, and payload size |
| `ftp_reply.py` | Stores FTP reply codes and response formatting helper |
| `logger.py` | Provides timestamped logging for server/client events |
| `checksum.py` | Provides CRC32 packet checksum and SHA-256 file hash helpers |
| `file_utils.py` | Provides safe path resolution to prevent access outside `server_root` |

---

### `hybridftp/protocol/`

Contains protocol-level data structures and parsers.

| File | Responsibility |
|---|---|
| `command.py` | Defines the `Command` data object after parsing raw client input |
| `command_parser.py` | Parses raw TCP command text into a `Command` object |
| `udp_packet.py` | Defines the custom UDP packet format, flags, encoding, decoding, and checksum validation |

Custom UDP packet header:

```txt
seq_no          uint32
ack_no          uint32
flags           uint8
payload_length  uint16
checksum        uint32
payload         bytes
```

Packet flags:

| Flag | Meaning |
|---|---|
| `DATA` | Packet contains file payload |
| `ACK` | Packet acknowledges received data |
| `FIN` | End of file transfer |
| `ERROR` | Error packet, optional |

---

### `hybridftp/rdt/`

Contains the custom reliable UDP implementation.

| File | Responsibility |
|---|---|
| `rdt_config.py` | Stores RDT parameters such as payload size, timeout, and max retries |
| `reliable_udp_sender.py` | Sends file chunks over UDP and waits for ACKs |
| `reliable_udp_receiver.py` | Receives UDP packets, validates sequence/checksum, writes payload to file, and sends ACKs |

Initial RDT algorithm:

```txt
Stop-and-Wait
```

Sender flow:

```txt
1. Read file chunk.
2. Build DATA packet with sequence number.
3. Send packet through UDP.
4. Wait for ACK.
5. If timeout occurs, retransmit packet.
6. If valid ACK is received, send the next packet.
7. Send FIN packet after the final chunk.
```

Receiver flow:

```txt
1. Receive UDP packet.
2. Decode and validate checksum.
3. Check expected sequence number.
4. Write payload if packet is valid and in order.
5. Send ACK.
6. Ignore duplicate packets but resend the latest ACK.
7. Stop when FIN is received.
```

---

### `hybridftp/server/`

Contains all server-side logic.

| File | Responsibility |
|---|---|
| `ftp_server.py` | Starts the TCP server, accepts clients, creates client threads, receives commands, and sends responses |
| `client_session.py` | Stores per-client state such as username, login status, current directory, and transfer type |
| `command_handler.py` | Handles FTP commands such as `USER`, `PASS`, `PWD`, `LIST`, `RETR`, `STOR`, and `HASH` |
| `auth_service.py` | Loads `users.json` and verifies login credentials |
| `file_service.py` | Handles server-side file and directory operations |
| `session_manager.py` | Tracks active connected clients for logging and demo evidence |

---

### `hybridftp/client/`

Contains all client-side logic.

| File | Responsibility |
|---|---|
| `ftp_client.py` | Connects to the server through TCP, sends commands, receives replies, and coordinates UDP transfer |
| `client_cli.py` | Provides the command-line interface for users |
| `progress_printer.py` | Prints upload/download progress information |

---

### `tests/`

Contains small unit tests for important modules.

| File | Responsibility |
|---|---|
| `test_command_parser.py` | Tests FTP command parsing |
| `test_udp_packet.py` | Tests UDP packet encoding, decoding, flags, and checksum validation |
| `test_checksum.py` | Tests CRC32 and SHA-256 helper functions |

---

## 5. How to Run

### Step 1: Prepare Python

Recommended Python version:

```txt
Python 3.10+
```

No third-party transfer libraries or FTP frameworks are required.

---

### Step 2: Start the Server

Open the first terminal:

```bash
python server_main.py
```

Expected output:

```txt
[YYYY-MM-DD HH:MM:SS] Hybrid FTP Server listening on 127.0.0.1:2121
```

---

### Step 3: Start the Client

Open the second terminal:

```bash
python client_main.py
```

Expected output:

```txt
220 Hybrid FTP Server Ready
Hybrid FTP Client
Type HELP for command list.
ftp>
```

---

## 6. Demo Commands

### Login

```txt
USER mickey
PASS 123456
```

Expected response:

```txt
331 Username OK, need password
230 Login successful
```

---

### Basic Directory Commands

```txt
PWD
LIST
NLST
SIZE sample.txt
```

---

### Set Transfer Type

ASCII mode:

```txt
TYPE A
```

Binary mode:

```txt
TYPE I
```

---

### Download File

Client local command:

```txt
LRETR sample.txt 5001
```

Expected result:

```txt
File saved to data/client_downloads/sample.txt
```

---

### Upload File

Client local command:

```txt
LSTOR data/client_downloads/sample.txt uploaded_sample.txt 6001
```

Expected result:

```txt
File saved to data/server_root/uploaded_sample.txt
```

---

### Hash Verification

```txt
HASH sample.txt
HASH uploaded_sample.txt
```

The SHA-256 values should match if the transfer is successful and the files are identical.

---

### Quit

```txt
QUIT
```

Expected response:

```txt
221 Goodbye
```

---

## 7. Supported Commands

Initial supported command list:

| Command | Description | Status |
|---|---|---|
| `USER <username>` | Send username | Planned / Implemented |
| `PASS <password>` | Send password | Planned / Implemented |
| `QUIT` | Close session | Planned / Implemented |
| `NOOP` | Keep-alive command | Planned / Implemented |
| `PWD` | Print current server directory | Planned / Implemented |
| `CWD <path>` | Change working directory | Planned |
| `CDUP` | Move to parent directory | Planned |
| `LIST [path]` | Detailed directory listing | Planned / Implemented |
| `NLST [path]` | Name-only directory listing | Planned / Implemented |
| `SIZE <filename>` | Get file size | Planned / Implemented |
| `TYPE {A | I}` | Set ASCII/Binary transfer type | Planned / Implemented |
| `PASV` | Passive mode placeholder or implementation | Planned |
| `RETR <filename>` | Download file through UDP data channel | Planned / Implemented |
| `STOR <filename>` | Upload file through UDP data channel | Planned / Implemented |
| `HASH <filename>` | Get SHA-256 hash of file | Planned / Implemented |
| `HELP [command]` | Show command help | Planned / Implemented |

Optional commands if time allows:

| Command | Description |
|---|---|
| `MKD <dirname>` | Create directory |
| `RMD <dirname>` | Remove empty directory |
| `DELE <filename>` | Delete file |
| `RNFR <oldname>` | Rename source |
| `RNTO <newname>` | Rename target |
| `MDTM <filename>` | Get last modification timestamp |
| `APPE <filename>` | Append uploaded data |
| `STOU` | Store file with unique server-generated name |
| `ABOR` | Abort current transfer |
| `PORT` | Active mode |
| `MODE` | Transfer mode |

---

## 8. Reliable UDP Design

The UDP data channel does not rely on built-in reliability. Instead, this application includes application-layer reliability.

### Reliability Features

| Feature | Implementation |
|---|---|
| Packet loss recovery | ACK + timeout + retransmission |
| Corruption detection | CRC32 checksum per UDP packet |
| Duplicate handling | Sequence number validation |
| Correct ordering | Stop-and-Wait expected sequence number |
| End-of-transfer signaling | FIN packet |
| End-to-end integrity | SHA-256 file hash comparison |

---

## 9. Server Logging Requirements

As running, the server should log:

```txt
- Server startup host and port
- Client connection and disconnection
- Client IP and port
- Commands received from each client
- Login success/failure
- Upload/download start
- Upload/download completion
- Retransmission events
- Active session table
```

---


## 12. About the team



---

## 13. Report

The technical report includes:

```txt
1. Application Scenario & Protocol Interaction
2. Project-Wide Data Structures
3. Functional Workflows / Flowcharts
4. Task Assignment Matrix
5. Self-Assessment & Peer Evaluation
6. GenAI Usage & Code Refinement Log
7. Application Demo Evidence
```

---


