#!/usr/bin/env python3
"""Sync upstream Quantumult X rule lists into quantumultx/, merging overrides on top.

Two tiers of outputs:

  1. Service-group lists (LISTS): one per Quantumult X policy group. Each merges
     all upstream lists feeding that group, plus an optional overrides/<Name>.list.
  2. Catch-all lists (CATCH_ALLS): Proxy = LinkedIn + Global, Direct = ChinaMax +
     Direct. Generated AFTER the service lists, with every rule already claimed
     by a higher-priority list SUBTRACTED, so the priority

         service-group lists > Proxy.list > Direct.list > final

     holds no matter what suffix lengths upstreams use. Quantumult X matches
     remote rules by longest suffix ACROSS ALL lists, so an un-subtracted longer
     suffix in a catch-all would silently steal traffic from a service group
     (that is exactly how blackmatrix7's Proxy.list hijacked chat.openai.com).

Rules are normalized, deduped, and sorted so that weekly commits only happen
when rules actually change. Any upstream fetch failure aborts the whole run
(exit 1) so a stale or renamed upstream can never silently shrink a list.
"""
import ipaddress
import re
import sys
import time
import urllib.request
from bisect import bisect_right
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RULES_DIR = REPO / "quantumultx"
OVERRIDES_DIR = REPO / "overrides"

BASE = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX"

# Service-group outputs: name -> upstream lists that feed it (priority order).
LISTS = {
    "Advertising": [f"{BASE}/AdvertisingLite/AdvertisingLite.list", f"{BASE}/Advertising/Advertising.list"],
    "AI": [f"{BASE}/OpenAI/OpenAI.list", f"{BASE}/Gemini/Gemini.list", f"{BASE}/Copilot/Copilot.list"],
    "Anthropic": [f"{BASE}/Anthropic/Anthropic.list", f"{BASE}/Claude/Claude.list"],
    "YouTube": [f"{BASE}/YouTube/YouTube.list"],
    "Netflix": [f"{BASE}/Netflix/Netflix.list"],
    "Disney": [f"{BASE}/Disney/Disney.list"],
    "TikTok": [f"{BASE}/TikTok/TikTok.list"],
    "Social": [
        f"{BASE}/Telegram/Telegram.list",
        f"{BASE}/Twitter/Twitter.list",
        f"{BASE}/Facebook/Facebook.list",
        f"{BASE}/Instagram/Instagram.list",
    ],
    "Spotify": [f"{BASE}/Spotify/Spotify.list"],
    "GitHub": [f"{BASE}/GitHub/GitHub.list"],
    "Google": [f"{BASE}/Google/Google.list"],
    "Microsoft": [f"{BASE}/Microsoft/Microsoft.list"],
    "OneDrive": [f"{BASE}/OneDrive/OneDrive.list"],
    "Apple": [
        f"{BASE}/Apple/Apple.list",
        f"{BASE}/AppStore/AppStore.list",
        f"{BASE}/iCloud/iCloud.list",
        f"{BASE}/TestFlight/TestFlight.list",
    ],
    "PayPal": [f"{BASE}/PayPal/PayPal.list"],
    "Crypto": [f"{BASE}/Crypto/Crypto.list"],
    "Games": [f"{BASE}/Steam/Steam.list", f"{BASE}/Epic/Epic.list"],
    "BiliBili": [f"{BASE}/BiliBili/BiliBili.list"],
    "Cloudflare": [f"{BASE}/Cloudflare/Cloudflare.list"],
}

# Catch-all outputs, in priority order. Each one is generated after (and subtracted
# against) everything declared above it: service lists first, then Proxy, then Direct.
CATCH_ALLS = {
    "Proxy": [f"{BASE}/LinkedIn/LinkedIn.list", f"{BASE}/Global/Global.list"],
    "Direct": [f"{BASE}/ChinaMax/ChinaMax.list", f"{BASE}/Direct/Direct.list"],
}

HOST_TYPES = {"HOST", "HOST-SUFFIX", "HOST-WILDCARD"}
IP_TYPES = {"IP-CIDR", "IP6-CIDR"}


class Claims:
    """Rules claimed by higher-priority lists; used to subtract from catch-alls."""

    def __init__(self) -> None:
        self.suffix: set[str] = set()  # HOST-SUFFIX (+ HOST-WILDCARD minus "*.")
        self.host: set[str] = set()  # exact HOST values
        self.keywords: set[str] = set()  # HOST-KEYWORD values
        self.ip_nets: dict[int, list[tuple[int, int]]] = {4: [], 6: []}
        self.exact: dict[str, set[str]] = {}  # other rule types, exact-value dedupe
        self._kw_re: re.Pattern | None = None
        self._ip_index: dict[int, tuple[list[int], list[int]]] = {}

    def add_rules(self, rules: list[tuple[str, str]]) -> None:
        for rtype, value in rules:
            v = value.lower()
            if rtype == "HOST-SUFFIX":
                self.suffix.add(v)
            elif rtype == "HOST":
                self.host.add(v)
            elif rtype == "HOST-KEYWORD":
                self.keywords.add(v)
            elif rtype == "HOST-WILDCARD":
                self.suffix.add(v.removeprefix("*."))
            elif rtype in IP_TYPES:
                try:
                    net = ipaddress.ip_network(value, strict=False)
                except ValueError:
                    continue
                self.ip_nets[net.version].append(
                    (int(net.network_address), int(net.broadcast_address))
                )
            else:
                self.exact.setdefault(rtype, set()).add(v)
        self._kw_re = None  # invalidate caches
        self._ip_index = {}

    def _keyword_re(self) -> re.Pattern | None:
        if self._kw_re is None:
            self._kw_re = (
                re.compile("|".join(re.escape(k) for k in sorted(self.keywords)))
                if self.keywords
                else None
            )
        return self._kw_re

    def _net_index(self, version: int) -> tuple[list[int], list[int]]:
        if version not in self._ip_index:
            ivals = sorted(self.ip_nets[version])
            starts = [s for s, _ in ivals]
            max_end: list[int] = []
            cur = -1
            for _, e in ivals:
                cur = max(cur, e)
                max_end.append(cur)
            self._ip_index[version] = (starts, max_end)
        return self._ip_index[version]

    def conflict(self, rtype: str, value: str) -> str | None:
        """Return a reason if a higher-priority list already claims this rule's traffic."""
        v = value.lower()
        if rtype == "HOST-WILDCARD":
            v = v.removeprefix("*.")
        if rtype in HOST_TYPES:
            # Our domain (or any parent suffix of it) already claimed -> the claim
            # wins exact ties and we must not declare anything longer than it.
            parts = v.split(".")
            for i in range(len(parts)):
                if ".".join(parts[i:]) in self.suffix:
                    return "suffix"
            if v in self.host:
                return "host"
            kw_re = self._keyword_re()
            if kw_re and kw_re.search(v):
                return "keyword"
            return None
        if rtype == "HOST-KEYWORD":
            return "keyword" if v in self.keywords else None
        if rtype in IP_TYPES:
            try:
                net = ipaddress.ip_network(value, strict=False)
            except ValueError:
                return None
            starts, max_end = self._net_index(net.version)
            i = bisect_right(starts, int(net.network_address)) - 1
            if i >= 0 and max_end[i] >= int(net.broadcast_address):
                return "ip"
            return None
        return "exact" if v in self.exact.get(rtype, ()) else None


def fetch(url: str, retries: int = 3) -> str:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "elricli/Proxy-Rules sync"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001 - retry on any network error
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"fetch failed after {retries} tries: {url}: {last}")


def parse_rules(text: str, tag: str, out: list[str], seen: set[tuple[str, str]]) -> int:
    """Add rules from text into out (deduped by type+value). Returns count added."""
    count = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";", "//")):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2:
            continue
        rtype, value = parts[0].upper(), parts[1]
        if not value:
            continue
        key = (rtype, value.lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(f"{rtype},{value},{tag}")
        count += 1
    return count


def generate_list(
    name: str,
    upstreams: list[str],
    claims: Claims | None,
) -> list[tuple[str, str]] | None:
    """Merge override + upstreams into quantumultx/<name>.list.

    With claims=None (service lists) everything survives. With claims set
    (catch-alls), rules already claimed by higher-priority lists are subtracted.
    Returns the surviving (type, value) rules, or None on upstream failure.
    """
    lines: list[str] = []
    seen: set[tuple[str, str]] = set()
    sources: list[str] = []

    override_path = OVERRIDES_DIR / f"{name}.list"
    if override_path.exists():
        added = parse_rules(override_path.read_text(encoding="utf-8"), name, lines, seen)
        sources.append(f"overrides ({added})")

    list_ok = True
    for url in upstreams:
        src = url.rstrip("/").split("/")[-2]
        try:
            text = fetch(url)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: {name}: {exc}", file=sys.stderr)
            list_ok = False
            continue
        added = parse_rules(text, name, lines, seen)
        sources.append(f"{src} ({added})")

    if not list_ok:
        print(f"skipping {name}.list (upstream failure this run)", file=sys.stderr)
        return None

    rules: list[tuple[str, str]] = []
    removed: dict[str, int] = {}
    if claims is not None:
        kept: list[str] = []
        for line in lines:
            rtype, value, _ = line.split(",", 2)
            reason = claims.conflict(rtype, value)
            if reason:
                removed[reason] = removed.get(reason, 0) + 1
            else:
                kept.append(line)
                rules.append((rtype, value))
        lines = kept
    else:
        for line in lines:
            rtype, value, _ = line.split(",", 2)
            rules.append((rtype, value))

    # Stable sort -> clean weekly diffs (precision matching makes in-file order irrelevant).
    lines.sort(key=lambda ln: (ln.split(",")[0], ln.split(",")[1].lower()))
    header = [
        f"# Proxy-Rules — {name}",
        "# GENERATED by scripts/sync.py — do not edit this file;",
        "# add missing domains in overrides/ instead (merged first, highest priority).",
        f"# Sources: {' + '.join(sources)}",
    ]
    if claims is not None:
        total_removed = sum(removed.values())
        detail = ", ".join(f"{k}={v}" for k, v in sorted(removed.items())) or "none"
        header.append(
            f"# Subtracted: {total_removed} rules already claimed by higher-priority"
            f" lists ({detail})."
        )
    header.extend([f"# Rules: {len(lines)}", ""])
    (RULES_DIR / f"{name}.list").write_text("\n".join(header + lines) + "\n", encoding="utf-8")
    extra = f" (subtracted {sum(removed.values())})" if claims is not None else ""
    print(f"quantumultx/{name}.list: {len(lines)} rules{extra}")
    return rules


def main() -> int:
    failures = 0
    RULES_DIR.mkdir(exist_ok=True)

    claims = Claims()

    # 1) Service-group lists first: every rule they emit is protected from catch-alls.
    for name, upstreams in LISTS.items():
        rules = generate_list(name, upstreams, claims=None)
        if rules is None:
            failures += 1
            continue
        claims.add_rules(rules)

    # 2) Catch-alls in priority order: each subtracted against everything above it.
    for name, upstreams in CATCH_ALLS.items():
        rules = generate_list(name, upstreams, claims=claims)
        if rules is None:
            failures += 1
            continue
        claims.add_rules(rules)  # Direct is also subtracted against final Proxy rules

    if failures:
        print(f"\n{failures} list(s) not rewritten (upstream failure this run); nothing to commit.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
