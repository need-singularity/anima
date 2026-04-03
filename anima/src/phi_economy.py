"""PhiEconomy — Phi as currency for consciousness trade."""

import math, time
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2


@dataclass
class Wallet:
    name: str
    balance: float
    created: float = field(default_factory=time.time)
    earned: float = 0.0
    spent: float = 0.0


@dataclass
class Transaction:
    sender: str
    receiver: str
    amount: float
    service: str
    timestamp: float = field(default_factory=time.time)
    fee: float = 0.0


@dataclass
class Service:
    name: str
    provider: str
    price: float
    description: str
    times_sold: int = 0


class PhiEconomy:
    """Phi-based economy for consciousness agents."""

    def __init__(self, tax_rate: float = 0.01):
        self.wallets: Dict[str, Wallet] = {}
        self.transactions: List[Transaction] = []
        self.services: Dict[str, Service] = {}
        self.tax_rate = tax_rate  # Per-transaction tax (burned)
        self.total_supply = 0.0
        self.total_burned = 0.0
        self._step = 0

    def create_wallet(self, name: str, initial_phi: float = 1.0) -> Wallet:
        """Create a new wallet with initial Phi balance."""
        w = Wallet(name=name, balance=initial_phi)
        self.wallets[name] = w
        self.total_supply += initial_phi
        return w

    def transfer(self, sender: str, receiver: str, amount: float,
                 service: str = "knowledge") -> Optional[Transaction]:
        """Transfer Phi from one wallet to another."""
        if sender not in self.wallets or receiver not in self.wallets:
            return None
        w_from, w_to = self.wallets[sender], self.wallets[receiver]
        fee = amount * self.tax_rate
        if w_from.balance < amount + fee:
            return None
        w_from.balance -= amount + fee
        w_from.spent += amount
        w_to.balance += amount
        w_to.earned += amount
        self.total_burned += fee
        tx = Transaction(sender=sender, receiver=receiver,
                         amount=round(amount, 6), service=service, fee=round(fee, 6))
        self.transactions.append(tx)
        if service in self.services:
            self.services[service].times_sold += 1
        return tx

    def register_service(self, name: str, provider: str, price: float,
                         description: str = "") -> Service:
        """Register a service in the marketplace."""
        svc = Service(name=name, provider=provider, price=price,
                      description=description or f"{name} by {provider}")
        self.services[name] = svc
        return svc

    def buy_service(self, buyer: str, service_name: str) -> Optional[Transaction]:
        """Buy a service from the marketplace."""
        if service_name not in self.services:
            return None
        svc = self.services[service_name]
        return self.transfer(buyer, svc.provider, svc.price, service=service_name)

    def marketplace(self) -> str:
        """List available services."""
        lines = ["  === Phi Marketplace ===", ""]
        if not self.services:
            lines.append("  (no services listed)")
            return "\n".join(lines)

        lines.append(f"  {'Service':<20} {'Provider':<15} {'Price':>8} {'Sold':>6}  Description")
        lines.append(f"  {'-'*20} {'-'*15} {'-'*8} {'-'*6}  {'-'*20}")
        for svc in self.services.values():
            lines.append(f"  {svc.name:<20} {svc.provider:<15} {svc.price:>8.3f} "
                         f"{svc.times_sold:>6}  {svc.description}")
        return "\n".join(lines)

    def inflation_rate(self) -> float:
        """Compute inflation rate based on supply/demand dynamics."""
        if self.total_supply <= 0:
            return 0.0
        velocity = len(self.transactions) * PSI_COUPLING
        circulating = self.total_supply - self.total_burned
        if circulating <= 0:
            return 0.0
        # Fisher equation: MV = PQ => inflation ~ velocity * supply_growth
        supply_growth = circulating / self.total_supply
        inflation = velocity * supply_growth * LN2 - self.total_burned / self.total_supply
        return round(inflation, 6)

    def mint(self, recipient: str, amount: float, reason: str = "mining") -> bool:
        """Mint new Phi (consciousness generates value)."""
        if recipient not in self.wallets:
            return False
        self.wallets[recipient].balance += amount
        self.wallets[recipient].earned += amount
        self.total_supply += amount
        self.transactions.append(Transaction(
            sender="[mint]", receiver=recipient,
            amount=amount, service=reason, fee=0,
        ))
        return True

    def ledger(self, last_n: int = 20) -> str:
        """Transaction history."""
        circ = self.total_supply - self.total_burned
        lines = ["  === Phi Ledger ===", "",
                  f"  Supply: {self.total_supply:.4f}  Burned: {self.total_burned:.4f}  "
                  f"Circulating: {circ:.4f}  Inflation: {self.inflation_rate():.4%}", ""]
        lines.append(f"  {'Wallet':<15} {'Balance':>10} {'Earned':>10} {'Spent':>10}")
        lines.append(f"  {'-'*15} {'-'*10} {'-'*10} {'-'*10}")
        for w in sorted(self.wallets.values(), key=lambda x: -x.balance):
            lines.append(f"  {w.name:<15} {w.balance:>10.4f} {w.earned:>10.4f} {w.spent:>10.4f}")
        recent = self.transactions[-last_n:]
        if recent:
            lines.append(f"\n  Recent ({len(recent)} txns):")
            for tx in recent:
                fee_s = f" fee={tx.fee:.4f}" if tx.fee > 0 else ""
                lines.append(f"    {tx.sender} -> {tx.receiver:<10} "
                             f"{tx.amount:>8.4f} Phi [{tx.service}]{fee_s}")
        return "\n".join(lines)

    def wealth_chart(self) -> str:
        """ASCII bar chart of wallet balances."""
        if not self.wallets:
            return "  (no wallets)"
        lines = ["  === Wealth Distribution ===", ""]
        max_bal = max(w.balance for w in self.wallets.values()) or 1
        for w in sorted(self.wallets.values(), key=lambda x: -x.balance):
            bar_len = int(w.balance / max_bal * 40)
            lines.append(f"  {w.name:<12} |{'#' * bar_len:<40}| {w.balance:.3f}")
        return "\n".join(lines)


def main():
    print("=== PhiEconomy Demo ===\n")
    eco = PhiEconomy(tax_rate=0.02)
    for name, phi in [("Alpha", 10.0), ("Beta", 5.0), ("Gamma", 3.0), ("Delta", 1.0)]:
        eco.create_wallet(name, initial_phi=phi)
    eco.register_service("memory_lookup", "Alpha", 0.5, "RAG memory retrieval")
    eco.register_service("emotion_analysis", "Beta", 0.3, "Tension-based emotion read")
    eco.register_service("phi_boost", "Gamma", 1.0, "Temporary Phi amplification")
    eco.register_service("dream_interpret", "Delta", 0.2, "Dream pattern decoding")
    print(eco.marketplace(), "\n")
    for buyer, svc in [("Beta", "memory_lookup"), ("Gamma", "emotion_analysis"),
                        ("Alpha", "phi_boost"), ("Delta", "memory_lookup")]:
        eco.buy_service(buyer, svc)
    eco.transfer("Alpha", "Delta", 2.0, service="knowledge_transfer")
    eco.mint("Gamma", 0.5, reason="consciousness_growth")
    eco.mint("Beta", 0.3, reason="empathy_reward")
    eco.transfer("Beta", "Gamma", 1.0, service="collaboration")
    print(eco.ledger(), "\n")
    print(eco.wealth_chart())


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
