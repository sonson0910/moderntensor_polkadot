#!/usr/bin/env python3
"""
ModernTensor — Demo Narration Script (v2 — with Web Frontend)
═══════════════════════════════════════════════════════════════
Hướng dẫn chi tiết từng scene: nói gì, show gì, thời gian bao lâu.

Tổng thời lượng: ~5 phút
Cần: 2 terminal tabs, 1 browser (Web Frontend + Blockscout), Screen recorder

⚡ TRƯỚC KHI QUAY:
  1. rm -f subnet/task_queue/*.json
  2. cd web && npm run dev     (start web frontend on localhost:3000)
  3. Mở sẵn browser tabs:
     • Tab 1: http://localhost:3000  (Web Frontend)
     • Tab 2: https://blockscout-westend-hub.polkadot.io/
  4. Terminal font size 18-20px
  5. 2 terminal tabs sẵn sàng
"""

# ╔════════════════════════════════════════════════════════════════════╗
# ║  CONTRACT ADDRESSES — để mở sẵn trên browser                      ║
# ╚════════════════════════════════════════════════════════════════════╝

CONTRACTS = {
    "MDTToken":        "0x5aC2455272378Be57d985a156C638f0E35EE61f4",
    "MDTVesting":      "0x482ec97FBc840bFD10bA37eA76aFD285394B5A66",
    "MDTStaking":      "0x8c4E7D144783315E8783aE7c562fB19dD4Ad22F8",
    "ZkMLVerifier":    "0x8C46Cc7d759AAB0158770bfD8c8BB4681ae03696",
    "AIOracle":        "0x0699A9a79f9007C523bB8AceB80870aB6cbdd052",
    "SubnetRegistry":  "0xE11F3F86B69578cAF3Db5Be80111B8484c8B6115",
}
EXPLORER_BASE = "https://blockscout-westend-hub.polkadot.io/address/"
WEB_URL       = "http://localhost:3000"

print("=" * 70)
print("  🎬 MODERNTENSOR — DEMO VIDEO NARRATION SCRIPT (v2)")
print("  📹 Polkadot Solidity Hackathon 2026")
print("  ⏱️  ~5 phút | Tiếng Anh (hackathon quốc tế)")
print("  🖥️  SỬ DỤNG WEB FRONTEND + TERMINAL + BLOCKSCOUT")
print("=" * 70)

SCENES = [
    # ──────────────────────────────────────────────────────────────────
    # SCENE 1: HOOK + WEB FRONTEND (0:00 - 0:40)
    # ──────────────────────────────────────────────────────────────────
    {
        "scene": 1,
        "title": "🎯 THE HOOK — Web Frontend Landing",
        "time": "0:00 → 0:40 (40s)",
        "show": "Browser — Web Frontend → Subnets Hub (localhost:3000)",
        "browser_url": WEB_URL,
        "voiceover": """
"Hi everyone. I'm [Tên bạn], and this is ModernTensor.

Imagine a world where ANYONE with a GPU can sell AI compute —
and every single result is MATHEMATICALLY VERIFIED on-chain.

[Browser hiện trang Subnets Hub — hiệu ứng BIOS boot animation xong]

ModernTensor is a decentralized AI inference network deployed
on Polkadot Hub via pallet-revive EVM.

As you can see, our Dashboard shows the live network stats:
11 Active Nodes, 4 subnets, emissions flowing in real time.
This is our cyberpunk-themed control center for the whole network.

Let me walk you through the full system — live on testnet."
""",
    },

    # ──────────────────────────────────────────────────────────────────
    # SCENE 2: WEB — SUBNET DETAIL + METAGRAPH (0:40 - 1:20)
    # ──────────────────────────────────────────────────────────────────
    {
        "scene": 2,
        "title": "🧠 SUBNET DETAIL — Metagraph Visualization",
        "time": "0:40 → 1:20 (40s)",
        "show": "Browser — Click into Subnet 1 → Subnet Detail page",
        "browser_url": f"{WEB_URL}/subnet/1",
        "voiceover": """
"Let me click into Subnet 1 — our flagship AI subnet.

[Click vào Subnet 1 card]

Here's the Subnet Detail page. You can see the subnet info:
- Owner address, creation block, nodes registered
- Maximum capacity, tempo, and emission parameters

Now scroll down to the METAGRAPH — this is the heart of
our network topology. It shows ALL 11 registered nodes:
each with their UID, identity, stake, trust score,
incentive, and 24-hour performance graph.

[Hover trên một node row]

You can filter by Miners or Validators. The pink dots
are Miners, the cyan dots are Validators. The 'Top Nodes'
sidebar shows the highest-performing participants.

All of this data is pulled LIVE from our SubnetRegistry
smart contract on Polkadot Hub."
""",
    },

    # ──────────────────────────────────────────────────────────────────
    # SCENE 3: WEB — VALIDATORS PAGE (1:20 - 1:50)
    # ──────────────────────────────────────────────────────────────────
    {
        "scene": 3,
        "title": "✅ VALIDATORS — Staking & Trust",
        "time": "1:20 → 1:50 (30s)",
        "show": "Browser — Navigate to Validators page",
        "browser_url": f"{WEB_URL}/validators",
        "voiceover": """
"Now let's look at the Validators page.

[Click 'Validators' in sidebar navigation]

This shows all registered validators with their stake,
trust scores, and recent validation activity. You can see
who's actively securing the network.

Validators need a minimum trust score to set consensus weights,
and their staking amount determines their influence. This
creates a robust incentive structure — bad actors lose stake,
good validators earn more.

The glassmorphic cards show real-time data from the blockchain."
""",
    },

    # ──────────────────────────────────────────────────────────────────
    # SCENE 4: WEB — TOKENOMICS + YIELD SIMULATOR (1:50 - 2:20)
    # ──────────────────────────────────────────────────────────────────
    {
        "scene": 4,
        "title": "💎 TOKENOMICS + YIELD SIMULATOR",
        "time": "1:50 → 2:20 (30s)",
        "show": "Browser — Navigate to Tokenomics page → use Yield Simulator",
        "browser_url": f"{WEB_URL}/tokenomics",
        "voiceover": """
"This is our Tokenomics page — showing the full MDT token economy.

[Click 'Tokenomics' in sidebar]

The distribution chart shows how the 21 million MDT max supply
is allocated: mining rewards, staking, ecosystem grants,
team vesting, and the community pool.

[Scroll to Yield Simulator]

And here's our Yield Simulator — this is a powerful tool for
potential participants. Adjust the stake amount, lock period,
and network parameters to see projected returns.

[Drag sliders to show APY changing]

As you can see, longer lock periods and higher stake give
better APY — this incentivizes long-term network commitment."
""",
    },

    # ──────────────────────────────────────────────────────────────────
    # SCENE 5: ON-CHAIN VERIFICATION (2:20 - 2:50)
    # ──────────────────────────────────────────────────────────────────
    {
        "scene": 5,
        "title": "🌐 ON-CHAIN CONTRACTS — Blockscout Explorer",
        "time": "2:20 → 2:50 (30s)",
        "show": "Browser — Switch to Blockscout tab → SubnetRegistry contract",
        "browser_url": f"{EXPLORER_BASE}{CONTRACTS['SubnetRegistry']}",
        "voiceover": """
"Now let me switch to Blockscout — the Polkadot Hub Testnet explorer.

You can see our SubnetRegistry contract deployed at this address.
We have 6 core smart contracts live on-chain:
- MDT Token — our ERC-20 with 21 million max supply
- Staking and Vesting contracts
- A ZkML Verifier — for on-chain proof verification
- An AI Oracle — for request and fulfillment
- And this SubnetRegistry — which implements our Enhanced Yuma
  Consensus directly in Solidity.

All deployed, all verifiable, all on Polkadot Hub Testnet."
""",
    },

    # ──────────────────────────────────────────────────────────────────
    # SCENE 6: START MINER (2:50 - 3:10)
    # ──────────────────────────────────────────────────────────────────
    {
        "scene": 6,
        "title": "⛏️ START MINER — AI Inference Node",
        "time": "2:50 → 3:10 (20s)",
        "show": "Terminal 1 (BÊN TRÁI nếu split screen)",
        "command": "python subnet/miner1.py",
        "voiceover": """
"Now let's start a miner node. This is Miner 1, UID 5.

It loads 3 AI models — NLP with ModernBERT for sentiment analysis,
a Finance model for risk assessment, and a Code model for
security auditing.

The miner is now listening for tasks from validators.
It polls the task queue every 3 seconds."
""",
    },

    # ──────────────────────────────────────────────────────────────────
    # SCENE 7: VALIDATOR + FULL LOOP ⭐ (3:10 - 4:20)
    # ──────────────────────────────────────────────────────────────────
    {
        "scene": 7,
        "title": "🔷 VALIDATOR + FULL LOOP ⭐ — THE MAIN EVENT",
        "time": "3:10 → 4:20 (70s) — SCENE QUAN TRỌNG NHẤT",
        "show": "Terminal 2 (BÊN PHẢI) — sau đó chuyển sang Terminal 1 rồi quay lại",
        "command": "python subnet/validator1.py",
        "voiceover": """
[KHI VALIDATOR BANNER HIỆN]
"Now I start the validator. Validator UID 7 — 100 MDT staked,
trust score over 51 percent, monitoring 11 active nodes."

[KHI "Epoch 1 — Validation" HIỆN]
"A new epoch begins. The validator randomly selects a task
from our catalog — in this case, Sentiment Analysis in the
NLP domain."

[KHI "Task dispatched" HIỆN]
"The task is dispatched to miners. Let me switch to the miner
terminal..."

[CHUYỂN SANG TERMINAL 1 — MINER]
"Here — the miner received the task from Validator UID 7.
It's running the ModernBERT model — 355 million parameters.

The result: Sentiment POSITIVE with confidence 79 percent.
Key phrases detected: AI, blockchain, trust.

And here's the critical part — the miner generates a zkML proof.
This is a mathematical proof that the AI model actually ran
correctly. The verifier uses a RISC-V zero-knowledge VM.

Task complete — result returned to the validator."

[CHUYỂN LẠI TERMINAL 2 — VALIDATOR]
"Back to the validator — it received the miner's response.

Quality Score: 0.83 — excellent. 81 percent confidence,
1.5 seconds compute time, and the zkML proof is verified.

Now watch: the validator sets consensus weights ON-CHAIN.
This is a real blockchain transaction..."

[KHI "Weights committed" HIỆN]
"Weights committed! Transaction hash right there.
Miner 5 got the highest weight — because it actually
processed this epoch's task.

And now — epoch emission distribution..."

[KHI "EPOCH COMPLETED" HIỆN]
"EPOCH 1 COMPLETED! Every node receives MDT token rewards —
Miners earning based on their weight, validators earning
for their scoring work. All on-chain, all verifiable."
""",
    },

    # ──────────────────────────────────────────────────────────────────
    # SCENE 8: VERIFY ON EXPLORER + WEB REFRESH (4:20 - 4:45)
    # ──────────────────────────────────────────────────────────────────
    {
        "scene": 8,
        "title": "🔍 VERIFY — Explorer + Web Frontend Live Update",
        "time": "4:20 → 4:45 (25s)",
        "show": "Browser — Blockscout TX → then switch to Web Frontend",
        "browser_url": f"{EXPLORER_BASE}{CONTRACTS['SubnetRegistry']}#transactions",
        "voiceover": """
"Let's verify this on the blockchain explorer.

Here on the SubnetRegistry contract — you can see the recent
transactions: setWeights and distributeEpochEmission — these
are the exact transactions our validator just submitted.

[Chuyển sang tab Web Frontend, refresh page]

And back on our Dashboard — the metagraph data has updated
to reflect the new weights and emissions. The Web Frontend
pulls live data from the same smart contracts."
""",
    },

    # ──────────────────────────────────────────────────────────────────
    # SCENE 9: CLOSING (4:45 - 5:10)
    # ──────────────────────────────────────────────────────────────────
    {
        "scene": 9,
        "title": "🎯 CLOSING — Summary + CTA",
        "time": "4:45 → 5:10 (25s)",
        "show": "Browser — Web Frontend homepage (Subnets Hub)",
        "browser_url": WEB_URL,
        "voiceover": """
"So what you just saw is the COMPLETE lifecycle of a
decentralized AI inference network on Polkadot:

1. Beautiful cyberpunk Dashboard with real-time network stats
2. Validators create tasks and miners run AI models
3. zkML proofs verify computation MATHEMATICALLY
4. Smart contracts distribute token rewards on-chain
5. Everything visible through our Metagraph, Yield Simulator,
   and Tokenomics pages

ModernTensor is the FIRST project to deploy on-chain AI
verification with Enhanced Yuma Consensus on Polkadot Hub.
6 smart contracts, 11 active nodes, a full web frontend,
and real rewards flowing.

Built for the Polkadot Solidity Hackathon 2026.
Thank you!"
""",
    },
]

# ════════════════════════════════════════════════════════════════════
# Print the full script
# ════════════════════════════════════════════════════════════════════
for s in SCENES:
    print(f"\n{'═' * 70}")
    print(f"  SCENE {s['scene']}: {s['title']}")
    print(f"  ⏱️  {s['time']}")
    print(f"{'═' * 70}")
    print(f"\n  📺 SHOW: {s['show']}")
    if "command" in s:
        print(f"  💻 COMMAND: {s['command']}")
    if "browser_url" in s:
        print(f"  🌐 URL: {s['browser_url']}")
    print(f"\n  🎙️ VOICEOVER:")
    for line in s["voiceover"].strip().split("\n"):
        print(f"  {line}")
    print()

# ════════════════════════════════════════════════════════════════════
# Web Frontend scenes guide
# ════════════════════════════════════════════════════════════════════
print("═" * 70)
print("  🖥️ WEB FRONTEND SCENES — CHI TIẾT NAVIGATION")
print("═" * 70)
print("""
  Web Frontend URL: http://localhost:3000

  TRANG 1: Subnets Hub (/)
    • Landing page — BIOS boot animation → cyberpunk dashboard
    • Stats bar: Total Subnets, Active Nodes, Network Emission
    • Subnet cards with neon glow effects
    • Click vào card → sang Subnet Detail

  TRANG 2: Subnet Detail (/subnet/1)
    • Subnet info panel (owner, nodes, tempo, emission)
    • METAGRAPH TABLE — core feature:
      - ALL/MINERS/VALIDATORS filter tabs
      - Columns: #, Identity, Stake, Trust, Incentive, 24h Perf
      - Pink dots = Miners, Cyan dots = Validators
      - Search by Coldkey or Hotkey
    • Top Nodes sidebar

  TRANG 3: Validators (/validators)
    • All validator nodes with trust scores
    • Staking amounts and weight influence

  TRANG 4: Tokenomics (/tokenomics)
    • Token distribution chart (21M max supply)
    • Allocation breakdown: Mining/Staking/Ecosystem/Team/Community
    • ⭐ YIELD SIMULATOR — interactive sliders:
      - Stake Amount slider
      - Lock Period slider
      - Shows projected APY and rewards
    • MUST interact with sliders during demo for visual impact!

  NAVIGATION: Sidebar menu (cyberpunk style)
    • Click menu items to navigate between pages
    • Smooth transitions and glow effects
""")

# ════════════════════════════════════════════════════════════════════
# Browser tabs to prepare
# ════════════════════════════════════════════════════════════════════
print("═" * 70)
print("  🌐 BROWSER TABS — MỞ SẴN TRƯỚC KHI QUAY")
print("═" * 70)
print(f"""
  TAB 1: Web Frontend Home
    URL: {WEB_URL}

  TAB 2: Web Frontend Subnet Detail
    URL: {WEB_URL}/subnet/1

  TAB 3: Web Frontend Tokenomics
    URL: {WEB_URL}/tokenomics

  TAB 4: Blockscout Explorer — SubnetRegistry
    URL: {EXPLORER_BASE}{CONTRACTS['SubnetRegistry']}

  TAB 5: Blockscout Explorer — MDT Token (optional)
    URL: {EXPLORER_BASE}{CONTRACTS['MDTToken']}
""")

# ════════════════════════════════════════════════════════════════════
# Pre-recording checklist
# ════════════════════════════════════════════════════════════════════
print("═" * 70)
print("  ✅ CHECKLIST TRƯỚC KHI BẤM RECORD")
print("═" * 70)
print("""
  [ ] Xóa task queue:  rm -f subnet/task_queue/*.json
  [ ] Start web frontend:  cd web && npm run dev
  [ ] Verify web loads:  open http://localhost:3000
  [ ] Test connection:  python -c "from subnet.base import get_deployer; c=get_deployer(); print(f'Block #{c.block_number}')"
  [ ] Terminal font 18-20px
  [ ] 2 terminal tabs sẵn sàng (tốt nhất split screen trái-phải)
  [ ] Browser 5 tabs mở sẵn (xem danh sách trên)
  [ ] Screen recorder ON (OBS / Loom / etc.)
  [ ] Micro test (nếu voiceover live)
  [ ] ĐỌC QUA SCRIPT 1 LẦN trước khi quay

  TIP: Video nên bắt đầu bằng Web Frontend (ấn tượng hơn terminal)
  TIP: Khi show metagraph, hover trên các nodes để highlight
  TIP: Khi show Yield Simulator, drag sliders CHẬM cho người xem thấy
  TIP: Nếu nói tiếng Anh chưa tự tin → quay video KHÔNG tiếng,
       rồi record voiceover riêng sau
""")

# All contract URLs
print("\n" + "═" * 70)
print("  🔗 TẤT CẢ BROWSER URLs CẦN MỞ SẴN")
print("═" * 70)
print(f"\n  {'Web Frontend':20s} → {WEB_URL}")
print(f"  {'Subnet Detail':20s} → {WEB_URL}/subnet/1")
print(f"  {'Validators':20s} → {WEB_URL}/validators")
print(f"  {'Tokenomics':20s} → {WEB_URL}/tokenomics")
print()
for name, addr in CONTRACTS.items():
    url = f"{EXPLORER_BASE}{addr}"
    print(f"  {name:20s} → {url}")
print()
