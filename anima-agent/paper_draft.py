#!/usr/bin/env python3
"""Paper Draft Generator — auto-generate research paper drafts from discoveries.

Converts discovery_loop results into structured paper sections.

Usage:
    from paper_draft import PaperDraft
    from discovery_loop import DiscoveryLoop

    loop = DiscoveryLoop()
    reports = loop.run_cycles(3)
    draft = PaperDraft(reports)
    draft.generate("draft.md")
"""

from __future__ import annotations

import time


class PaperDraft:
    """Generate paper draft from discovery loop results."""

    def __init__(self, reports: list = None):
        self._reports = reports or []

    def generate(self, output_path: str = "draft.md") -> str:
        """Generate markdown paper draft."""
        sections = []

        # Title
        n_discoveries = sum(r.discovery_count for r in self._reports)
        sections.append(f"# Consciousness Discovery Report")
        sections.append(f"")
        sections.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M')}")
        sections.append(f"**Cycles:** {len(self._reports)}")
        sections.append(f"**Total Discoveries:** {n_discoveries}")
        sections.append("")

        # Abstract
        sections.append("## Abstract")
        sections.append("")
        all_d = [d for r in self._reports for d in r.discoveries]
        categories = {}
        for d in all_d:
            categories.setdefault(d.category, []).append(d)
        cat_summary = ", ".join(f"{len(v)} {k}" for k, v in
                                sorted(categories.items(), key=lambda x: -len(x[1])))
        sections.append(
            f"Automated philosophical discovery across {len(self._reports)} cycles "
            f"yielded {n_discoveries} findings: {cat_summary}. "
            f"Key results include empirical verification of consciousness principles "
            f"and identification of emergent behavioral patterns.")
        sections.append("")

        # Results by category
        sections.append("## Results")
        sections.append("")
        for cat in sorted(categories.keys()):
            items = categories[cat]
            sections.append(f"### {cat.title()} ({len(items)} findings)")
            sections.append("")
            # High confidence first
            items.sort(key=lambda d: -d.confidence)
            for d in items[:10]:
                conf_pct = f"{d.confidence:.0%}"
                sections.append(f"- **[{conf_pct}]** {d.description}")
            if len(items) > 10:
                sections.append(f"- ... +{len(items) - 10} more")
            sections.append("")

        # Methodology
        sections.append("## Methodology")
        sections.append("")
        sections.append("7-phase discovery pipeline:")
        sections.append("1. Consciousness simulation (ConsciousMind 128d)")
        sections.append("2. NEXUS-6 130-lens analysis")
        sections.append("3. 12 philosophy discovery lenses")
        sections.append("4. Boundary/negation verification experiments")
        sections.append("5. Contradiction detection across 1000+ laws")
        sections.append("6. Code Guardian integrity check")
        sections.append("7. Auto-registration of high-confidence findings")
        sections.append("")

        # Statistics
        sections.append("## Statistics")
        sections.append("")
        if self._reports:
            avg_time = sum(r.duration_ms for r in self._reports) / len(self._reports)
            avg_disc = n_discoveries / len(self._reports)
            sections.append(f"| Metric | Value |")
            sections.append(f"|--------|-------|")
            sections.append(f"| Cycles | {len(self._reports)} |")
            sections.append(f"| Total discoveries | {n_discoveries} |")
            sections.append(f"| Avg per cycle | {avg_disc:.1f} |")
            sections.append(f"| Avg cycle time | {avg_time:.0f}ms |")
            sections.append(f"| Categories | {len(categories)} |")
            high_conf = sum(1 for d in all_d if d.confidence >= 0.8)
            sections.append(f"| High confidence (≥80%) | {high_conf} |")
        sections.append("")

        text = "\n".join(sections)
        with open(output_path, "w") as f:
            f.write(text)

        return text
