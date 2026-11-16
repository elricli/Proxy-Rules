# Proxy-Rules

自维护的分流规则列表，**一个策略组一个文件，另加 proxy/direct 两个减法兜底**，每周日自动从上游（[blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)）同步合并，并叠加自己补充的域名。同一份规则导出两种格式：

- **Quantult X**：`rules/*.list`，一个策略组一个文件
- **Clash / OpenClash（mihomo 内核）**：`clash/Global.list`，一份合并的全局规则，classical rule-provider 直接远端引用

## 为什么要自维护

第三方大杂烩列表之间会互相抢流量：Quantult X 默认开启「分流匹配优化」后，跨远程列表按**后缀精度**匹配（更长的后缀赢），列表作者的规则精度你控制不了。自维护后，每个域名的后缀长度、合并来源、更新节奏都由自己决定。

## 结构

```
rules/                  QX 格式生成的最终列表 ← QX 订阅这些（不要手改）
clash/Global.list       合并后的 Clash 全局规则 ← OpenClash rule-provider 引用（不要手改）
overrides/              自己补充的域名，合并时优先生效（在这里加域名）
scripts/sync.py         同步脚本：拉上游 → 合并 override → 去重 → 排序 → 兜底列表做减法 → 生成 rules/
scripts/export_clash.py 转换脚本：rules/*.list → clash/Global.list（离线，不联网）
.github/                每周日 03:00 UTC 自动跑一次同步 + 导出，有变化才提交
```

| 文件 | 对应策略组 | 上游来源 |
|---|---|---|
| `rules/Advertising.list` | 🛑 广告拦截 | AdvertisingLite + Advertising |
| `rules/AI.list` | 🤖 AI | OpenAI + Gemini + Copilot + overrides |
| `rules/Anthropic.list` | 🅐 Anthropic | Anthropic + Claude + overrides |
| `rules/YouTube.list` | YouTube | YouTube |
| `rules/Netflix.list` | 🎬 Netflix | Netflix |
| `rules/Disney.list` | 🎞 Disney+ | Disney |
| `rules/TikTok.list` | 🎵 TikTok | TikTok |
| `rules/Social.list` | 💬 社交通讯 | Telegram + Twitter + Facebook + Instagram |
| `rules/Spotify.list` | 🎧 Spotify | Spotify |
| `rules/GitHub.list` | 🧑‍💻 GitHub | GitHub |
| `rules/Google.list` | 🧩 Google | Google |
| `rules/Microsoft.list` | Ⓜ️ Microsoft | Microsoft |
| `rules/OneDrive.list` | ☁️ OneDrive | OneDrive |
| `rules/Apple.list` | 🍎 Apple | Apple（AppStore/iCloud/TestFlight 已并入去重） |
| `rules/PayPal.list` | 💳 PayPal | PayPal |
| `rules/Crypto.list` | 🪙 加密货币 | Crypto + overrides |
| `rules/Games.list` | 🎮 游戏平台 | Steam + Epic |
| `rules/BiliBili.list` | 📺 BiliBili | BiliBili |
| `rules/Cloudflare.list` | 🌐 Cloudflare | Cloudflare |
| `rules/Proxy.list` | proxy（兜底代理） | LinkedIn + Global，**减去上层已收编的规则** |
| `rules/Direct.list` | direct（兜底直连） | ChinaMax + Direct，**减去上层已收编的规则** |

## 优先级与减法

Quantult X 跨远程列表按**后缀精度**匹配（更长的后缀赢），列表声明顺序不保证优先级。
本仓库在生成时用减法强制实现这个优先级：

```
策略组列表（AI、Google、Apple…） > Proxy.list > Direct.list > 配置里的 final
```

`Proxy.list` / `Direct.list` 生成时，任何已被更高优先级列表收编的规则会被自动删除：

- 后缀 / HOST / 通配规则：域名本身或其任意**父后缀**出现在上层列表 → 删（等长对冲不了更长的后缀，直接不留）
- 后缀 / HOST / 通配规则：域名**包含上层列表声明的关键字** → 删
- 关键字规则：与上层列表的关键字完全相同 → 删
- IP 段：整段落在上层列表已收编的网段之内 → 删
- 其余类型（USER-AGENT、IP-ASN 等）：与上层完全相同 → 删

所以即使上游（如 Global）未来新增更长的后缀，也抢不走策略组列表的流量——这正是
blackmatrix7 Proxy.list 曾经劫持 `chat.openai.com` 的原因，现在这个类别的问题在生成阶段就被消灭。

## 用法 — Quantumult X

`[filter_remote]` 中引用（`force-policy` 指向自己配置里的策略组名）：

```ini
https://raw.githubusercontent.com/elricli/Proxy-Rules/main/rules/AI.list, tag=AI, force-policy=🤖 AI, update-interval=86400, opt-parser=false, enabled=true
https://raw.githubusercontent.com/elricli/Proxy-Rules/main/rules/Anthropic.list, tag=Anthropic, force-policy=🅐 Anthropic, update-interval=86400, opt-parser=false, enabled=true
```

兜底列表放最后（策略组 → Proxy → Direct → final）：

```ini
https://raw.githubusercontent.com/elricli/Proxy-Rules/main/rules/Proxy.list, tag=Proxy, force-policy=proxy, update-interval=86400, opt-parser=false, enabled=true
https://raw.githubusercontent.com/elricli/Proxy-Rules/main/rules/Direct.list, tag=Direct, force-policy=direct, update-interval=86400, opt-parser=false, enabled=true
```

其余列表同理。直连 raw.githubusercontent.com 不稳时可换 jsdelivr 镜像：

```ini
https://cdn.jsdelivr.net/gh/elricli/Proxy-Rules@main/rules/AI.list, tag=AI, force-policy=🤖 AI, update-interval=86400, opt-parser=false, enabled=true
```

## 用法 — OpenClash / Clash（mihomo）

`rule-providers` 里远端引用一份合并文件即可（需要 mihomo 内核，OpenClash 默认内核即是）：

```yaml
rule-providers:
  proxy-rules:
    type: http
    behavior: classical
    format: text
    url: https://raw.githubusercontent.com/elricli/Proxy-Rules/main/clash/Global.list
    interval: 86400
    path: ./ruleset/proxy-rules.list

rules:
  - RULE-SET,proxy-rules,DIRECT   # 占位：文件里每条规则自带策略目标
  - MATCH,🚀 节点选择
```

说明：

- 文件内每条规则自带策略目标：广告 → `REJECT`、国内 → `DIRECT`、其余 → 策略组名。**组名必须和你配置里的 proxy-groups 一致**，不一致就改 `scripts/export_clash.py` 里的 `POLICY` 表重跑。
- 顺序即优先级（first-match-wins）：`REJECT → 服务组（具体在前）→ Proxy → Direct`，与 QX 侧的减法优先级一致，跨组重复域名已在导出时去重（先出现的赢）。
- 全量约 46 万条 / 17MB（Advertising 一家占 30 万条）。低端路由器内存吃紧时，在 `scripts/export_clash.py` 的 `SKIP` 里加上 `"Advertising"` 重跑即可裁掉大头。
- 直连 raw.githubusercontent.com 不稳时可换 jsdelivr 镜像（注意 jsDelivr 单文件上限 20MB，本文件已逼近）：
  `https://cdn.jsdelivr.net/gh/elricli/Proxy-Rules@main/clash/Global.list`

## 加域名

在 `overrides/<名称>.list` 里加一行（格式：`规则类型,值,名称`，`#` 开头是注释），提交即可。可以手动跑 `python3 scripts/sync.py && python3 scripts/export_clash.py` 立即重新生成，也可以等每周日的自动同步：

```ini
HOST-SUFFIX,example.com,AI
```

注意：`overrides/` 合并时排在最前。兜底列表（Proxy/Direct）已被减法挡住，不会再抢策略组的域名；
但两个策略组列表之间（如 Google 与 YouTube）仍按后缀精度解析，同域名重复声明时在配置里先声明的赢。

## 同步机制

- 每周日 03:00 UTC（北京时间周日 11:00）GitHub Actions 自动运行，也支持手动触发：`sync.py` 同步 `rules/` → `export_clash.py` 导出 `clash/Global.list`
- 上游拉取失败会**整体中止**（退出码 1），绝不提交缺料的列表
- 规则排序去重后写入，无变化不产生空提交
