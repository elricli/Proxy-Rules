# AGENTS.md

给在本仓库工作的 agent 的操作手册。README.md 面向使用者的订阅与引用；本文件面向维护仓库的 agent。

## 是什么

自维护分流规则：每周日 03:00 UTC 从 [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script) 同步上游 → 合并 overrides → 去重排序 → 兜底减法 → 按客户端分目录导出（`quantumultx/` 给 QX，`clash/` 给 Clash/OpenClash）。

## 布局

```
quantumultx/             QX 格式生成物（21 个组）——生成物，不要手改
clash/<Group>.list       Clash classical 生成物，一组一文件（21 个）——生成物，不要手改
clash/verge-merge.yaml   Clash Verge Rev「全局扩展覆写配置」粘贴段——生成物
clash/openclash-module.ini  OpenClash 覆写模块粘贴段——生成物
overrides/                维护者补充域名的唯一手工入口
scripts/sync.py           阶段 1：拉上游 → 合并 override → 去重 → 排序 → 减法 → 生成 quantumultx/（需联网）
scripts/export_clash.py   阶段 2：quantumultx/*.list → clash/ 组文件 + 两份粘贴片段（离线，不联网）
.github/workflows/sync.yml 每周日 03:00 UTC 跑两个阶段，有变化才提交
```

## 不变量

1. **生成物不要手改**——要改就改 `overrides/<组名>.list` 或 `scripts/*.py`，然后重跑 `python3 scripts/sync.py && python3 scripts/export_clash.py`。
2. **失败即中止**：sync.py 任一上游拉取失败 → 整体退出 1，绝不提交缺料的列表。重构时保留此语义。
3. **优先级 = 减法**：`策略组 > Proxy.list > Direct > 配置 final`。兜底列表生成时删掉一切被更高优先级列表收编的规则（父后缀覆盖 / 关键字包含 / IP 段包含 / 其余类型值相同；细则见 sync.py 的 `Claims`）。目的：上游新增更长后缀也抢不走策略组流量（blackmatrix7 Proxy.list 曾劫持 `chat.openai.com` 的教训）。
4. **export 清单不变量**：`quantumultx/` 每个组必须登记进 export_clash.py 的 `ORDER` + `POLICY`，缺了/多了导出直接失败。`ORDER` 顺序即粘贴片段里 `RULE-SET` 的优先级（first-match-wins，具体在前，兜底在后）。`SKIP` = 该组完全不导出（组文件 + 粘贴片段里的行一起消失）。两份粘贴片段（`verge-merge.yaml` / `openclash-module.ini`）**永远由脚本生成，不要手写/手改**——改 `POLICY`/`ORDER` 后重跑即同步。
5. **POLICY 组名 = 用户三台设备配置里的策略组名**——现在直接出现在粘贴片段的 `RULE-SET` 行上（用户会整段粘贴进配置），要改先跟用户确认，改错会断分流。
6. **IP 规则统一带 `no-resolve`**（export_clash.py 已统一处理）。
7. **体积红线**：jsDelivr 单文件上限 20MB，`Advertising.list` 已 11MB，别再增大生成物。
8. **mihomo 忽略 classical 文件内嵌的策略列**（源码验证：`ParseRulePayload(rule, false)` 第三列按参数解析，`rule_set.go` 的 `Match` 返回 `rs.adapter`，tunnel 按 `RULE-SET` 行策略选路）——**严禁"单文件多策略"设计**（旧 `Global.list` 就是这个错误，已删）。一策略组一文件。粘贴片段的 `RULE-SET` 行必然带中文/Emoji 组名：OpenClash 部分环境会损坏 `[YAML]` 段的中文/Emoji（[#5049](https://github.com/vernesong/OpenClash/discussions/5049)），无法规避（组名必须真实存在），模块头部注释已写明遇损坏时改用 `[Overwrite]` ruby 方案的退路。

## 常见任务

- **加域名**：`overrides/<组名>.list` 加一行 `HOST-SUFFIX,example.com,组名` → 重跑两个脚本 → 提交（两种格式一起提交）。
- **新策略组**：sync.py `LISTS` 登记上游 → export_clash.py `ORDER`（排位 = 优先级）+ `POLICY` 登记映射 → README 表格加一行 → 重跑。
- **提交信息**：沿用 conventional 风格前缀（`feat:` / `ci:` / `refactor:` / `sync:`）。

## 环境坑

- 本机直连 `github.com` / `api.github.com` 会被 SNI 重置（机场出口抖动，QX TUN 形态），git push 失败重试几次即可；`cdn.jsdelivr.net` 通常直连可达。
- GitHub 只重定向**仓库**改名，不重定向目录/文件改名——`quantumultx/` 的文件名就是三台设备 QX 的订阅 URL，改名必 404，动了要同步更新 Elric-Main.conf 并让用户重新导入。
- 周期任务在 GitHub Actions（周日 03:00 UTC）；本地手动触发用 workflow_dispatch，或直接跑脚本。
- **Clash Verge Rev 全局扩展覆写配置是纯 YAML 深合并**：`rule-providers` 深合并，`rules` **整体替换**订阅规则（所以片段必须带 `MATCH` 兜底）；网上旧教程的 `prepend-rules`/`append-rules` 在当前源码（`enhance/merge.rs`）里**不存在**。OpenClash 才是 `[YAML]`+`+` 前缀的 INI 覆写模块格式，两者别混——「全局扩展覆写配置」是 Verge Rev 的编辑器名，OpenClash 对应功能叫「覆写模块」（运行状态页顶部按钮）。
