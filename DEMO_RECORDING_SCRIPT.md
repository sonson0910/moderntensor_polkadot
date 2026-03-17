# 🎬 ModernTensor — Demo Recording Script (~5 minutes)

> **Polkadot Solidity Hackathon 2026** | English voiceover | 9 scenes

---

## ✅ Checklist Before Recording

```bash
# 1. Clean task queue
rm -f subnet/task_queue/*.json

# 2. Start web frontend
cd web && npm run dev          # → http://localhost:3000

# 3. Test blockchain connection
python -c "from subnet.base import get_deployer; c=get_deployer(); print(f'Block #{c.block_number}')"
```

**Browser — open 4 tabs:**

| Tab | URL |
|-----|-----|
| Subnets Hub | `http://localhost:3000` |
| Subnet Detail | `http://localhost:3000/subnet/1` |
| Tokenomics | `http://localhost:3000/tokenomics` |
| Blockscout | `https://blockscout-westend-hub.polkadot.io/address/0xE11F3F86B69578cAF3Db5Be80111B8484c8B6115` |

**Terminal:** 2 tabs (split screen left/right), font size 18–20px

**Screen recorder:** OBS / Loom / QuickTime — 1920×1080

---

## Scene-by-Scene

---

### Scene 1 — 🎯 Hook + Subnets Hub `0:00 → 0:40` (40s)

**Show:** Browser → `http://localhost:3000`

**Actions:**
1. Page loads → BIOS boot animation plays automatically
2. Dashboard appears: cyberpunk neon theme, glassmorphism cards
3. Point out the stats bar: **Total Subnets**, **Active Nodes (11)**, **Network Emission**
4. Show the subnet cards glowing with neon borders

**Voiceover:**

> "Hi everyone. I'm [Your Name], and this is ModernTensor.
>
> Imagine a world where ANYONE with a GPU can sell AI compute — and every single result is MATHEMATICALLY VERIFIED on-chain.
>
> ModernTensor is a decentralized AI inference network deployed on Polkadot Hub via pallet-revive EVM.
>
> As you can see, our Dashboard shows the live network stats: 11 Active Nodes, 4 subnets, emissions flowing in real time. This is our cyberpunk-themed control center for the whole network.
>
> Let me walk you through the full system — live on testnet."

---

### Scene 2 — 🧠 Subnet Detail + Metagraph `0:40 → 1:20` (40s)

**Show:** Click into Subnet 1 card → `http://localhost:3000/subnet/1`

**Actions:**
1. Click on Subnet 1 card from the hub page
2. Subnet info panel loads: owner address, creation block, nodes, tempo, emission
3. Scroll down to the **METAGRAPH** table
4. Show all 11 node rows: UID, Identity, Stake, Trust, Incentive, 24h performance sparklines
5. Click filter tabs: **ALL** → **MINERS** (pink dots) → **VALIDATORS** (cyan dots)
6. Hover over a node row to highlight it
7. Point out the **Top Nodes** sidebar on the right

**Voiceover:**

> "Let me click into Subnet 1 — our flagship AI subnet.
>
> Here's the Subnet Detail page — owner address, creation block, registered nodes, tempo, and emission parameters.
>
> Scroll down to the METAGRAPH — this is the heart of our network topology. It shows ALL 11 registered nodes, each with their UID, identity, stake, trust score, incentive, and 24-hour performance graph.
>
> You can filter by Miners or Validators. Pink dots are Miners, cyan dots are Validators. The Top Nodes sidebar shows the highest-performing participants.
>
> All of this data is pulled LIVE from our SubnetRegistry smart contract on Polkadot Hub."

---

### Scene 3 — ✅ Validators `1:20 → 1:50` (30s)

**Show:** Click "Validators" in sidebar → `http://localhost:3000/validators`

**Actions:**
1. Click **Validators** in the left sidebar navigation
2. Show validator cards with trust scores, stake amounts, activity
3. Hover over cards to show glassmorphic highlight effects

**Voiceover:**

> "Now let's look at the Validators page.
>
> This shows all registered validators with their stake, trust scores, and recent validation activity.
>
> Validators need a minimum trust score to set consensus weights, and their staking amount determines their influence. Bad actors lose stake, good validators earn more.
>
> The glassmorphic cards show real-time data from the blockchain."

---

### Scene 4 — 💎 Tokenomics + Yield Simulator `1:50 → 2:20` (30s)

**Show:** Click "Tokenomics" in sidebar → `http://localhost:3000/tokenomics`

**Actions:**
1. Click **Tokenomics** in the left sidebar
2. Show the token distribution chart — 21M MDT max supply pie chart
3. Point out allocation categories: Mining 45%, Staking, Ecosystem, Team, Community
4. Scroll down to the **Yield Simulator**
5. ⭐ **IMPORTANT:** Drag the **Stake Amount** slider slowly (left → right)
6. Drag the **Lock Period** slider slowly — watch APY numbers change
7. Pause so viewers can read the projected returns

**Voiceover:**

> "This is our Tokenomics page — showing the full MDT token economy.
>
> The distribution chart shows how the 21 million MDT max supply is allocated: mining rewards, staking, ecosystem grants, team vesting, and community pool.
>
> And here's our Yield Simulator — adjust the stake amount, lock period, and network parameters to see projected returns.
>
> As you can see, longer lock periods and higher stake give better APY — this incentivizes long-term network commitment."

---

### Scene 5 — 🌐 Blockscout Explorer `2:20 → 2:50` (30s)

**Show:** Switch to Blockscout browser tab → SubnetRegistry contract

**Actions:**
1. Switch to Blockscout tab showing SubnetRegistry at `0xE11F3F86B69578cAF3Db5Be80111B8484c8B6115`
2. Show the contract overview: code verified, transactions, balance
3. Optionally scroll through recent transactions

**Voiceover:**

> "Now let me switch to Blockscout — the Polkadot Hub Testnet explorer.
>
> You can see our SubnetRegistry contract deployed at this address. We have 6 core smart contracts live on-chain:
> - MDT Token — our ERC-20 with 21 million max supply
> - Staking and Vesting contracts
> - A ZkML Verifier — for on-chain proof verification
> - An AI Oracle — for request and fulfillment
> - And this SubnetRegistry — which implements Enhanced Yuma Consensus directly in Solidity.
>
> All deployed, all verifiable, all on Polkadot Hub Testnet."

**Contract addresses (for reference):**

| Contract | Address |
|----------|---------|
| MDTToken | `0x5aC2455272378Be57d985a156C638f0E35EE61f4` |
| MDTVesting | `0x482ec97FBc840bFD10bA37eA76aFD285394B5A66` |
| MDTStaking | `0x8c4E7D144783315E8783aE7c562fB19dD4Ad22F8` |
| ZkMLVerifier | `0x8C46Cc7d759AAB0158770bfD8c8BB4681ae03696` |
| AIOracle | `0x0699A9a79f9007C523bB8AceB80870aB6cbdd052` |
| SubnetRegistry | `0xE11F3F86B69578cAF3Db5Be80111B8484c8B6115` |

---

### Scene 6 — ⛏️ Start Miner `2:50 → 3:10` (20s)

**Show:** Terminal 1 (LEFT side)

**Command:**

```bash
python subnet/miner1.py
```

**Actions:**
1. Type the command, press Enter
2. Wait for the banner: Miner UID 5, hotkey, stake, trust
3. Show "Loading 3 AI models: NLP, Finance, Code"
4. Show "Listening for tasks... polling every 3s"

**Voiceover:**

> "Now let's start a miner node. This is Miner 1, UID 5.
>
> It loads 3 AI models — NLP with ModernBERT for sentiment analysis, a Finance model for risk assessment, and a Code model for security auditing.
>
> The miner is now listening for tasks from validators. It polls the task queue every 3 seconds."

---

### Scene 7 — 🔷 Validator Loop ⭐ `3:10 → 4:20` (70s) — **MAIN EVENT**

**Show:** Terminal 2 (RIGHT side) → switch back and forth with Terminal 1

**Command:**

```bash
python subnet/validator1.py
```

**Actions & Timing:**

| Timestamp | What Happens | What to Say |
|-----------|-------------|-------------|
| +0s | Validator banner appears | "Validator UID 7 — 100 MDT staked, trust 51%, monitoring 11 nodes" |
| +5s | "Epoch 1 — Validation" | "A new epoch begins — random task selected: Sentiment Analysis" |
| +8s | "Task dispatched" | "Task dispatched to miners. Let me switch to the miner terminal..." |
| +10s | **Switch Terminal 1** | "Here — the miner received the task from Validator UID 7" |
| +15s | Miner processes | "Running ModernBERT — 355M parameters. Result: POSITIVE, confidence 79%" |
| +20s | zkML proof generated | "The miner generates a zkML proof — mathematical proof the model ran correctly" |
| +25s | Task complete | "Task complete — result returned to the validator" |
| +30s | **Switch Terminal 2** | "Back to the validator — Quality Score: 0.83, excellent" |
| +40s | Weights committed | "Watch — the validator sets consensus weights ON-CHAIN. Transaction hash right there" |
| +50s | Emission distribution | "Miner 5 got the highest weight — because it processed this epoch's task" |
| +60s | "EPOCH COMPLETED" | "EPOCH 1 COMPLETED! Every node receives MDT token rewards — all on-chain" |

**Voiceover:** (follow the table above — this is the longest and most important scene)

---

### Scene 8 — 🔍 Verify on Explorer + Web Refresh `4:20 → 4:45` (25s)

**Show:** Browser → Blockscout TX tab → then Web Frontend

**Actions:**
1. Switch to Blockscout tab
2. Click "Transactions" tab on SubnetRegistry
3. Show `setWeights` and `distributeEpochEmission` transactions
4. Switch to Web Frontend tab (`localhost:3000/subnet/1`)
5. Refresh the page — show updated metagraph data

**Voiceover:**

> "Let's verify on the blockchain explorer.
>
> Here on the SubnetRegistry contract — you can see the recent transactions: setWeights and distributeEpochEmission — these are the exact transactions our validator just submitted.
>
> And back on our Dashboard — the metagraph data has updated to reflect the new weights and emissions. The Web Frontend pulls live data from the same smart contracts."

---

### Scene 9 — 🎯 Closing `4:45 → 5:10` (25s)

**Show:** Browser → Web Frontend homepage (`http://localhost:3000`)

**Actions:**
1. Navigate back to Subnets Hub (homepage)
2. Let the dashboard be visible as you deliver the closing

**Voiceover:**

> "So what you just saw is the COMPLETE lifecycle of a decentralized AI inference network on Polkadot:
>
> 1. Beautiful cyberpunk Dashboard with real-time network stats
> 2. Validators create tasks and miners run AI models
> 3. zkML proofs verify computation MATHEMATICALLY
> 4. Smart contracts distribute token rewards on-chain
> 5. Everything visible through our Metagraph, Yield Simulator, and Tokenomics pages
>
> ModernTensor is the FIRST project to deploy on-chain AI verification with Enhanced Yuma Consensus on Polkadot Hub. 6 smart contracts, 11 active nodes, a full web frontend, and real rewards flowing.
>
> Built for the Polkadot Solidity Hackathon 2026. Thank you!"

---

## 💡 Tips for Recording

- **Start with web frontend** — it's visually impressive, hooks the viewer immediately
- **Drag sliders SLOWLY** on Yield Simulator — let viewers see the numbers change
- **Hover on metagraph rows** — triggers highlight effects
- **Switch terminals cleanly** — don't rush, give 1–2 seconds for the viewer to reorient
- **If English voiceover feels stiff** — record video first (no audio), then record voiceover separately
- **Total target: exactly 5 minutes** — Scene 7 (Validator Loop) is the longest at 70s, don't rush it
