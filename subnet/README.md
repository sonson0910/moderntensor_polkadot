# ModernTensor Subnet — Complete Demo

## Quick Start

### Cách 1: Chạy tự động (1 lệnh)
```bash
python subnet/run_demo.py         # Chạy 3 rounds mặc định
python subnet/run_demo.py 5       # Chạy 5 rounds
```

### Cách 2: Chạy tay — 2 terminal (cho quay video demo)

**Terminal 1 — Miner:**
```bash
python subnet/miner_node.py
```

**Terminal 2 — Validator:**
```bash
python subnet/validator_node.py
```

### Cách 3: Truy vấn on-chain state
```bash
python subnet/query_chain.py              # Hiện tất cả
python subnet/query_chain.py subnet       # Chỉ subnet info
python subnet/query_chain.py nodes        # Chỉ danh sách nodes
python subnet/query_chain.py weights      # Chỉ validator weights
python subnet/query_chain.py metagraph    # Chỉ metagraph
```

### Cách 4: Chạy nhiều miner/validator
```bash
# Terminal 1: Miner 1
MINER_ID=1 python subnet/miner_node.py

# Terminal 2: Miner 2
MINER_ID=2 python subnet/miner_node.py

# Terminal 3: Validator 1
VALIDATOR_ID=1 python subnet/validator_node.py

# Terminal 4 (tùy chọn): Validator 2
VALIDATOR_ID=2 python subnet/validator_node.py
```

## Cấu trúc thư mục

```
subnet/
├── config.json            ← Cấu hình (RPC, wallets, nodes, timing)
├── miner_node.py          ← Miner: nhận task → AI inference → zkML proof
├── validator_node.py      ← Validator: tạo task → đánh giá → weights → epoch
├── run_demo.py            ← Demo tự động (1 lệnh chạy cả miner + validator)
├── query_chain.py         ← Truy vấn on-chain state (subnet, nodes, weights)
├── README.md              ← Hướng dẫn này
└── task_queue/            ← Hàng đợi task (tự động tạo)
```

## Biến môi trường

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| `MINER_ID`     | 1     | Chọn miner: 1 (UID=0) hoặc 2 (UID=1)    |
| `VALIDATOR_ID`  | 1     | Chọn validator: 1 (UID=2), 2 (UID=3), 3 (UID=4) |
| `MAX_ROUNDS`    | 0     | Giới hạn số vòng (0 = vô hạn)            |
| `POLL_INTERVAL` | 3/8   | Tần suất polling (giây)                   |
| `MINER_TIMEOUT` | 30    | Timeout chờ miner (giây)                  |

## Luồng hoạt động

```
┌────────────┐         ┌─────────────┐         ┌────────────┐
│  VALIDATOR  │────────▶│ TASK QUEUE   │◀────────│   MINER    │
│             │ create  │ (file-based) │  poll   │            │
│  1. Tạo    │  task   │              │  task   │  1. Nhận   │
│     task AI │         └─────────────┘         │     task   │
│  2. Chờ    │                                  │  2. Chạy   │
│     kết quả│◀──────── result returned ────────│     AI     │
│  3. Đánh   │                                  │  3. Tạo    │
│     giá    │                                  │     zkML   │
│  4. Set    │──── on-chain tx ────────────────▶│  4. Trả    │
│     weights│                                  │     kết quả│
│  5. Epoch  │──── on-chain tx ────────────────▶│            │
│  6. Claim  │                                  │  5. Claim  │
│     rewards│                                  │     rewards│
└────────────┘                                  └────────────┘
```

## Nodes hiện tại trên Testnet

| Node | Type | UID | Hotkey |
|------|------|-----|--------|
| miner1 | MINER | 0 | 0x526CE1A0... |
| miner2 | MINER | 1 | 0x3B67D5d2... |
| validator1 | VALIDATOR | 2 | 0x29D1f30b... |
| validator2 | VALIDATOR | 3 | 0xaFA853c8... |
| validator3 | VALIDATOR | 4 | 0x0eC02D64... |

## Kịch bản quay video demo

1. Mở 2 terminal cạnh nhau (split screen)
2. Terminal trái: `python subnet/miner_node.py` — xem banner, chờ task
3. Terminal phải: `python subnet/validator_node.py` — tạo task, chấm điểm, epoch
4. Quan sát: Miner nhận task → AI xử lý → zkML proof → Validator đánh giá → On-chain
5. Ctrl+C cả 2 → chạy `python subnet/query_chain.py` để verify on-chain
