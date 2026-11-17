# Proxy-Rules

自维护的分流规则列表，**一个策略组一个文件，另加 proxy/direct 两个减法兜底**，每周日自动从上游（[blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)）同步合并，并叠加自己补充的域名。同一份规则导出两种格式：

- **Quantumult X**：`quantumultx/*.list`，一个策略组一个文件
- **Clash / OpenClash（mihomo 内核）**：`clash/<组名>.list` 一组一个文件，外加两份即贴片段（`clash/verge-merge.yaml`、`clash/openclash-module.ini`，脚本随周更自动生成）

根目录按客户端分目录：OpenClash 与 Clash 同为 mihomo 内核、classical 格式完全通用，共用 `clash/` 一个目录；后续支持其他客户端（如 Surge）时新增目录即可。

维护者的操作手册（布局、生成流程、不变量、常见任务、环境坑）见 [AGENTS.md](AGENTS.md)；本 README 只面向使用者。

## 为什么要自维护

第三方大杂烩列表之间会互相抢流量：Quantumult X 默认开启「分流匹配优化」后，跨远程列表按**后缀精度**匹配（更长的后缀赢），列表作者的规则精度你控制不了。自维护后，每个域名的后缀长度、合并来源、更新节奏都由自己决定。

## 组列表

| 文件 | 对应策略组 | 上游来源 |
|---|---|---|
| `quantumultx/Advertising.list` | 🛑 广告拦截 | AdvertisingLite + Advertising |
| `quantumultx/AI.list` | 🤖 AI | OpenAI + Gemini + Copilot + overrides |
| `quantumultx/Anthropic.list` | 🅐 Anthropic | Anthropic + Claude + overrides |
| `quantumultx/YouTube.list` | YouTube | YouTube |
| `quantumultx/Netflix.list` | 🎬 Netflix | Netflix |
| `quantumultx/Disney.list` | 🎞 Disney+ | Disney |
| `quantumultx/TikTok.list` | 🎵 TikTok | TikTok |
| `quantumultx/Social.list` | 💬 社交通讯 | Telegram + Twitter + Facebook + Instagram |
| `quantumultx/Spotify.list` | 🎧 Spotify | Spotify |
| `quantumultx/GitHub.list` | 🧑‍💻 GitHub | GitHub |
| `quantumultx/Google.list` | 🧩 Google | Google |
| `quantumultx/Microsoft.list` | Ⓜ️ Microsoft | Microsoft |
| `quantumultx/OneDrive.list` | ☁️ OneDrive | OneDrive |
| `quantumultx/Apple.list` | 🍎 Apple | Apple（AppStore/iCloud/TestFlight 已并入去重） |
| `quantumultx/PayPal.list` | 💳 PayPal | PayPal |
| `quantumultx/Crypto.list` | 🪙 加密货币 | Crypto + overrides |
| `quantumultx/Games.list` | 🎮 游戏平台 | Steam + Epic |
| `quantumultx/BiliBili.list` | 📺 BiliBili | BiliBili |
| `quantumultx/Cloudflare.list` | 🌐 Cloudflare | Cloudflare |
| `quantumultx/Proxy.list` | proxy（兜底代理） | LinkedIn + Global，**减去上层已收编的规则** |
| `quantumultx/Direct.list` | direct（兜底直连） | ChinaMax + Direct，**减去上层已收编的规则** |

## 优先级与减法

Quantumult X 跨远程列表按**后缀精度**匹配（更长的后缀赢），列表声明顺序不保证优先级。
本仓库在生成时用减法强制实现这个优先级：

```
策略组列表（AI、Google、Apple…） > Proxy.list > Direct.list > 配置里的 final
```

`Proxy.list` / `Direct.list` 生成时，任何已被更高优先级列表收编的规则会被自动删除（父后缀覆盖、关键字包含、IP 段包含等，细则见 `scripts/sync.py` 与 [AGENTS.md](AGENTS.md)）。

所以即使上游（如 Global）未来新增更长的后缀，也抢不走策略组列表的流量——这正是
blackmatrix7 Proxy.list 曾经劫持 `chat.openai.com` 的原因，现在这个类别的问题在生成阶段就被消灭。

## 用法 — Quantumult X

`[filter_remote]` 中引用（`force-policy` 指向自己配置里的策略组名）：

```ini
https://raw.githubusercontent.com/elricli/Proxy-Rules/main/quantumultx/AI.list, tag=AI, force-policy=🤖 AI, update-interval=86400, opt-parser=false, enabled=true
https://raw.githubusercontent.com/elricli/Proxy-Rules/main/quantumultx/Anthropic.list, tag=Anthropic, force-policy=🅐 Anthropic, update-interval=86400, opt-parser=false, enabled=true
```

兜底列表放最后（策略组 → Proxy → Direct → final）：

```ini
https://raw.githubusercontent.com/elricli/Proxy-Rules/main/quantumultx/Proxy.list, tag=Proxy, force-policy=proxy, update-interval=86400, opt-parser=false, enabled=true
https://raw.githubusercontent.com/elricli/Proxy-Rules/main/quantumultx/Direct.list, tag=Direct, force-policy=direct, update-interval=86400, opt-parser=false, enabled=true
```

其余列表同理。直连 raw.githubusercontent.com 不稳时可换 jsdelivr 镜像：

```ini
https://cdn.jsdelivr.net/gh/elricli/Proxy-Rules@main/quantumultx/AI.list, tag=AI, force-policy=🤖 AI, update-interval=86400, opt-parser=false, enabled=true
```

## 用法 — Clash / OpenClash（mihomo 内核）

需要 mihomo 内核。**关键语义（源码验证）**：mihomo **忽略** classical 规则文件里第三列的策略——`ParseRulePayload(rule, false)` 把第三列按规则参数解析，tunnel 按 `RULE-SET` 行自己的策略选路。所以**一个策略组一个 provider 文件**；下面的粘贴片段由脚本随周更自动生成，组名与顺序永远和生成物同步。

`RULE-SET` 顺序即优先级（first-match-wins）：`广告 REJECT → 服务组（具体在前）→ Proxy → Direct`，与 QX 侧的减法优先级一致。

### 方式一：Clash Verge Rev「全局扩展覆写配置」

订阅页 → 更多/全局 →「全局扩展覆写配置」编辑器，粘贴 [`clash/verge-merge.yaml`](clash/verge-merge.yaml) 全文：

- `rule-providers` 深合并进配置；`rules` **整体替换**订阅的规则（片段末行带 `MATCH` 兜底），即完整接管分流
- 片段里的策略组名（🤖 AI、🅐 Anthropic…）必须和你配置里的 proxy-groups 逐字符一致——不同就改 `scripts/export_clash.py` 的 `POLICY` 表重跑
- 注意：网上旧教程的 `prepend-rules` / `append-rules` 在当前 Verge Rev 源码里**不存在**（`enhance/merge.rs` 只有深合并），勿用

### 方式二：OpenClash 覆写模块

运行状态页顶部「覆写模块」按钮 → 添加新模块（本地模块，匹配配置文件填 `all`）→ 编辑器粘贴 [`clash/openclash-module.ini`](clash/openclash-module.ini) → 打开模块开关 → **重启插件**（`reload` 不会重跑覆写）：

- `[YAML]` 段必需；`+rule-providers` 合并 provider，`+rules` 把 `RULE-SET` 行**前置**到订阅规则之前——没覆盖到的流量落回订阅规则兜底
- 部分环境会损坏 `[YAML]` 段里的中文/Emoji 组名（现象：`proxy not found` / `????`），遇此按[官方讨论 #5049](https://github.com/vernesong/OpenClash/discussions/5049)改用 `[Overwrite]` 段 ruby 方案
- provider URL 用 jsDelivr 镜像（路由器直连可达）

### 组文件与裁剪

- `clash/` 下一个组一个文件，组列表与 quantumultx/ 完全一致（见上表）；不需要的组不引对应的 `RULE-SET` 行即可
- Advertising 一家 ~30 万条 / 11MB，低端路由器吃紧时在 `scripts/export_clash.py` 的 `SKIP` 里加组名重跑，该组（含粘贴片段里的行）完全不导出
- jsDelivr 单文件上限 20MB（`Advertising.list` 11MB 未超但别再大）；能直连 GitHub 的场景可把片段 URL 换成 `https://raw.githubusercontent.com/elricli/Proxy-Rules/main/clash/<Group>.list`

## 加域名

在 `overrides/<名称>.list` 里加一行（格式：`规则类型,值,名称`，`#` 开头是注释），提交即可。可以手动跑 `python3 scripts/sync.py && python3 scripts/export_clash.py` 立即重新生成，也可以等每周日的自动同步：

```ini
HOST-SUFFIX,example.com,AI
```

注意：`overrides/` 合并时排在最前。兜底列表（Proxy/Direct）已被减法挡住，不会再抢策略组的域名；
但两个策略组列表之间（如 Google 与 YouTube）仍按后缀精度解析，同域名重复声明时在配置里先声明的赢。

## 同步机制

- 每周日 03:00 UTC（北京时间周日 11:00）GitHub Actions 自动运行，也支持手动触发：`sync.py` 同步 `quantumultx/` → `export_clash.py` 导出 `clash/`
- 上游拉取失败会**整体中止**（退出码 1），绝不提交缺料的列表
- 规则排序去重后写入，无变化不产生空提交
