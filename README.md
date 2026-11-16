# QuantumultX-List

自维护的 Quantumult X 分流规则列表，**一个策略组一个文件**，每周一自动从上游（[blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)）同步合并，并叠加自己补充的域名。

## 为什么要自维护

第三方大杂烩列表之间会互相抢流量：Quantult X 默认开启「分流匹配优化」后，跨远程列表按**后缀精度**匹配（更长的后缀赢），列表作者的规则精度你控制不了。自维护后，每个域名的后缀长度、合并来源、更新节奏都由自己决定。

## 结构

```
rules/            生成的最终列表 ← QX 订阅这些（不要手改）
overrides/        自己补充的域名，合并时优先生效（在这里加域名）
scripts/sync.py   同步脚本：拉上游 → 合并 override → 去重 → 排序 → 生成 rules/
.github/          每周一 03:00 UTC 自动跑一次同步，有变化才提交
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

## 用法

`[filter_remote]` 中引用（`force-policy` 指向自己配置里的策略组名）：

```ini
https://raw.githubusercontent.com/elricli/QuantumultX-List/main/rules/AI.list, tag=AI, force-policy=🤖 AI, update-interval=86400, opt-parser=false, enabled=true
https://raw.githubusercontent.com/elricli/QuantumultX-List/main/rules/Anthropic.list, tag=Anthropic, force-policy=🅐 Anthropic, update-interval=86400, opt-parser=false, enabled=true
```

其余列表同理。直连 raw.githubusercontent.com 不稳时可换 jsdelivr 镜像：

```ini
https://cdn.jsdelivr.net/gh/elricli/QuantumultX-List@main/rules/AI.list, tag=AI, force-policy=🤖 AI, update-interval=86400, opt-parser=false, enabled=true
```

## 加域名

在 `overrides/<名称>.list` 里加一行（格式：`规则类型,值,名称`，`#` 开头是注释），提交即可。可以手动跑 `python3 scripts/sync.py` 立即重新生成，也可以等每周一的自动同步：

```ini
HOST-SUFFIX,example.com,AI
```

注意：`overrides/` 合并时排在最前，但跨列表冲突仍按后缀精度解析——被上游更长的后缀抢走时，需要在 overrides 里用**等长后缀**对冲。

## 同步机制

- 每周一 03:00 UTC（北京时间周一 11:00）GitHub Actions 自动运行，也支持手动触发
- 上游拉取失败会**整体中止**（退出码 1），绝不提交缺料的列表
- 规则排序去重后写入，无变化不产生空提交
