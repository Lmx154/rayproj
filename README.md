# rayproj — VirtualBox Ray Mini-Cluster (Ubuntu Server + uv)

Small distributed computing demo for a Computer Networks final project.
This repo runs a **Ray-based distributed log analytics workload** across a **3-node virtual cluster**.

## What this demonstrates

* Virtual LAN setup with static IPs
* Hostname-based node communication
* A simple Ray cluster (head + workers)
* A non-GUI distributed workload that produces a final artifact:

  * `final_wordcount.json`

---

## Cluster Topology

**VMs (Ubuntu Server):**

* `head` — Ray coordinator (no compute contribution)
* `worker1` — compute node
* `worker2` — compute node

**Internal cluster subnet:**

* `192.168.56.0/24`

**Static IPs:**

* `head` → `192.168.56.9`
* `worker2` → `192.168.56.10`
* `worker1` → `192.168.56.11`

---

## VirtualBox Network Setup

Each VM uses **two NICs**:

**Adapter 1**

* Attached to: **Internal Network**
* Name: `cluster-net`

**Adapter 2**

* Attached to: **NAT**

This keeps cluster networking stable while allowing internet access for installs.

---

## Hostname Resolution

Ensure each VM has the same `/etc/hosts` entries (example):

```txt
127.0.0.1 localhost
127.0.1.1 <this-vm-hostname>

192.168.56.9  head
192.168.56.11 worker1
192.168.56.10 worker2
```

Test:

```bash
ping -c 2 head
ping -c 2 worker1
ping -c 2 worker2
```

---

## Install uv

Run on **each VM**:

```bash
sudo apt update
sudo apt install -y curl
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
uv --version
```

---

## IMPORTANT: Pin Python to Avoid Ray Version Mismatches

Ray requires consistent Python versions across nodes.
This project uses **Python 3.12.3**.

On **each VM** inside the repo directory:

```bash
cd ~/rayproj
uv python pin 3.12.3
uv python install 3.12.3
uv sync
```
---

## Start the Ray Cluster

### Head node

```bash
cd ~/rayproj
uv run ray stop || true
uv run ray start --head --num-cpus=0 --port=6379 --node-ip-address=192.168.56.9
```

### Worker nodes

Run on **worker1**:

```bash
cd ~/rayproj
uv run ray stop || true
uv run ray start --address=192.168.56.9:6379
```

Run on **worker2**:

```bash
cd ~/rayproj
uv run ray stop || true
uv run ray start --address=192.168.56.9:6379
```

---

## Verify Cluster Health

On **head**:

```bash
cd ~/rayproj
uv run ray status
```

Expected:

* 3 active nodes
* Total CPU reflects workers (head is coordinator-only)

---

## Run the Distributed Workload

On **head**:

```bash
cd ~/rayproj
uv run python main.py --generate --lines 80000 --chunk-size 400 --top 20
```

Output:

* `telemetry_logs.txt`
* `final_wordcount.json`

Confirm:

```bash
ls -l final_wordcount.json
```

---

## Cleanup

Stop Ray on any node:

```bash
cd ~/rayproj
uv run ray stop
```

---
