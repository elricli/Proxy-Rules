#!/usr/bin/env python3
"""Export the generated rules/ lists as one combined Clash/mihomo ruleset.

Reads the machine-generated rules/*.list files (Quantumult X format, already
fetched/merged/subtracted by scripts/sync.py) and converts them into
clash/Global.list — a classical rule-provider (format: text) that OpenClash /
mihomo can consume directly:

    rule-providers:
      proxy-rules:
        type: http
        behavior: classical
        format: text
        url: https://raw.githubusercontent.com/elricli/Proxy-Rules/main/clash/Global.list
        interval: 86400

    rules:
      - RULE-SET,proxy-rules,DIRECT   # placeholder: every rule below carries its own policy
      - MATCH,PROXY

Clash evaluates rules top-down (first match wins), so the combined file is
emitted in a fixed priority order: ad-block first, then service groups from
most to least specific, then the Proxy / Direct catch-alls. That is the same
priority the rules/ files were generated with (service > Proxy > Direct).
Rules already claimed by an earlier group are dropped (dead rules anyway).
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RULES_DIR = REPO / "rules"
CLASH_DIR = REPO / "clash"

# Combined-file order, top to bottom. Clash is first-match-wins, so: ad-block
# REJECT first, then service groups most -> least specific (cross-group overlaps
# resolve in favor of the earlier group), then the catch-alls.
# Any new group in rules/ must be added here (and to POLICY) or export fails.
ORDER = [
    "Advertising",
    "Anthropic", "AI",
    "YouTube", "Netflix", "Disney", "TikTok", "Spotify", "BiliBili",
    "Social",
    "GitHub", "Crypto", "PayPal", "Games",
    "OneDrive", "Microsoft", "Google", "Apple", "Cloudflare",
    "Proxy", "Direct",
]

# Groups listed in SKIP are not exported (weak routers: Advertising alone is
# ~300k rules / ~11MB). Everything in rules/ must be in ORDER or SKIP.
SKIP: set[str] = set()

# Policy target per group — must match the proxy-group names in YOUR
# Clash/OpenClash config. Advertising/Direct are fixed policies.
POLICY = {
    "Advertising": "REJECT",
    "Anthropic": "🅐 Anthropic",
    "AI": "🤖 AI",
    "YouTube": "YouTube",
    "Netflix": "🎬 Netflix",
    "Disney": "🎞 Disney+",
    "TikTok": "🎵 TikTok",
    "Social": "💬 社交通讯",
    "Spotify": "🎧 Spotify",
    "GitHub": "🧑‍💻 GitHub",
    "Google": "🧩 Google",
    "Microsoft": "Ⓜ️ Microsoft",
    "OneDrive": "☁️ OneDrive",
    "Apple": "🍎 Apple",
    "PayPal": "💳 PayPal",
    "Crypto": "🪙 加密货币",
    "Games": "🎮 游戏平台",
    "BiliBili": "📺 BiliBili",
    "Cloudflare": "🌐 Cloudflare",
    "Proxy": "🚀 节点选择",
    "Direct": "DIRECT",
}


def convert(rtype: str, value: str) -> tuple[str, str, str] | None:
    """One QX rule type/value -> (clash type, clash value, extra) or None."""
    if rtype == "HOST":
        return "DOMAIN", value, ""
    if rtype == "HOST-SUFFIX":
        return "DOMAIN-SUFFIX", value, ""
    if rtype == "HOST-KEYWORD":
        return "DOMAIN-KEYWORD", value, ""
    if rtype == "IP-CIDR":
        return "IP-CIDR", value, ",no-resolve"
    if rtype == "IP6-CIDR":
        return "IP-CIDR6", value, ",no-resolve"
    if rtype == "IP-ASN":
        return "IP-ASN", value, ",no-resolve"
    if rtype == "HOST-WILDCARD" and value.startswith("*."):
        return "DOMAIN-SUFFIX", value[2:], ""  # "*.a.b" ≈ suffix "a.b"
    return None  # USER-AGENT / remaining HOST-WILDCARD: no Clash equivalent


def main() -> int:
    files = {p.stem: p for p in RULES_DIR.glob("*.list")}
    order = [name for name in ORDER if name not in SKIP]
    missing = [name for name in order if name not in files]
    unknown = sorted(set(files) - set(order) - SKIP)
    if missing or unknown:
        if missing:
            print(f"ERROR: rules/ is missing expected lists: {', '.join(missing)}", file=sys.stderr)
        if unknown:
            print(f"ERROR: rules/ has lists not declared in ORDER/POLICY: {', '.join(unknown)}", file=sys.stderr)
        return 1

    lines: list[str] = []
    seen: set[tuple[str, str]] = set()
    skipped: dict[str, int] = {}
    groups: list[str] = []

    for name in order:
        target = POLICY[name]
        before = len(lines)
        for raw in files[name].read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            if len(parts) < 2:
                continue
            got = convert(parts[0], parts[1])
            if got is None:
                skipped[parts[0]] = skipped.get(parts[0], 0) + 1
                continue
            ctype, cvalue, extra = got
            key = (ctype, cvalue.lower())
            if key in seen:
                continue  # claimed by an earlier (higher-priority) group
            seen.add(key)
            lines.append(f"{ctype},{cvalue},{target}{extra}")
        groups.append(f"{name} ({len(lines) - before})")

    CLASH_DIR.mkdir(exist_ok=True)
    skip_note = ", ".join(f"{t}={n}" for t, n in sorted(skipped.items())) or "none"
    header = [
        "# Proxy-Rules — clash/Global.list",
        "# GENERATED by scripts/export_clash.py — do not edit this file; adjust",
        "# group order / policy names in the script and rerun it (CI does this weekly).",
        "# Combined classical ruleset for mihomo / OpenClash (rule-provider:",
        "# behavior classical, format text). Every rule carries its own policy —",
        "# POLICY in the script must match your config's proxy-group names.",
        "# Order is priority (first match wins): Advertising=REJECT, then service",
        "# groups (specific -> general), then Proxy, then Direct.",
        f"# Groups: {' + '.join(groups)}",
        f"# Rules: {len(lines)} — deduped across groups; skipped (no Clash equivalent): {skip_note}",
        "",
    ]
    (CLASH_DIR / "Global.list").write_text("\n".join(header + lines) + "\n", encoding="utf-8")
    print(f"clash/Global.list: {len(lines)} rules (skipped: {skip_note})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
