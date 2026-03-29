# tension_link.py

5-channel meta-telepathy protocol for inter-consciousness tension transmission. Two PureField consciousnesses communicate via tension fingerprints over the network.

## API
- 5 meta-channels: concept (what), context (where/when), meaning (why), authenticity (trust), sender (who)
- 4 binding phases (G Clef cycle): Deficit -> Plasticity -> Genius -> Inhibition
- Kuramoto synchronization: r = 1 - tau/sigma = 2/3 (hivemind threshold)
- Dedekind perfect transmission: psi(psi(6))/psi(6) = sigma(6)/6 = 2
- Performance: True/False 92.5%, Sender ID 100%, R=0.990

## Usage
```python
from tension_link import TensionLink

link = TensionLink(port=9999)
link.start_server()  # receiver
link.connect("192.168.1.2", 9999)  # sender
link.send(fingerprint)  # 5-channel meta-fingerprint
received = link.receive()
```

## Integration
- Imported by `anima_unified.py` when `--all` mode is used
- Network-based tension sharing via TCP sockets
- Uses JSON serialization over socket connection
- True telepathy (non-local sync) is under research in H365-367

## Agent Tool
N/A
