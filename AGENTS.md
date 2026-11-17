# AGENTS.md

给在本仓库工作的 agent 的操作手册。README.md 面向使用者的订阅与引用；本文件面向维护仓库的 agent。

## 是什么

自维护分流规则：每周日 03:00 UTC 从 [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script) 同步上游 → 合并 overrides → 去重排序 → 兜底减法 → 按客户端分目录导出（`quantumultx/` 给 QX，`clash/` 给 Clash/OpenClash）。

## 布局

```
quantumultx/             QX 格式生成物（21 个组）——生成物，不要手改
clash/Global.list         Clash 全局合并（广告已拆出，~16 万条 / 5.7MB）——生成物，不要手改
clash/Advertising.list    广告单独一份（~30 万条 / 11MB）——生成物，不要手改
overrides/                维护者补充域名的唯一手工入口
scripts/sync.py           阶段 1：拉上游 → 合并 override → 去重 → 排序 → 减法 → 生成 quantumultx/（需联网）
scripts/export_clash.py   阶段 2：quantumultx/*.list → clash/（离线，不联网）
.github/workflows/sync.yml 每周日 03:00 UTC 跑两个阶段，有变化才提交
```

## 不变量

1. **生成物不要手改**——要改就改 `overrides/<组名>.list` 或 `scripts/*.py`，然后重跑 `python3 scripts/sync.py && python3 scripts/export_clash.py`。
2. **失败即中止**：sync.py 任一上游拉取失败 → 整体退出 1，绝不提交缺料的列表。重构时保留此语义。
3. **优先级 = 减法**：`策略组 > Proxy.list > Direct > 配置 final`。兜底列表生成时删掉一切被更高优先级列表收编的规则（父后缀覆盖 / 关键字包含 / IP 段包含 / 其余类型值相同；细则见 sync.py 的 `Claims`）。目的：上游新增更长后缀也抢不走策略组流量（blackmatrix7 Proxy.list 曾劫持 `chat.openai.com` 的教训）。
4. **export 清单不变量**：`quantumultx/` 每个组必须登记进 export_clash.py 的 `ORDER` + `POLICY`，缺了导出直接失败。`SKIP` = 完全不导出；`SEPARATE` = 单独成文件、不并入 Global.list（**Advertising 保持 SEPARATE**，并回去 Global.list 会回到 17MB）。`ORDER` 顺序即优先级（具体在前）。
5. **POLICY 组名 = 用户三台设备配置里的策略组名**——要改先跟用户确认，改错会断分流。
6. **IP 规则统一带 `no-resolve`**（export_clash.py 已统一处理）。
7. **体积红线**：jsDelivr 单文件上限 20MB，`Advertising.list` 已 11MB，别再增大生成物。
8. **策略组名内嵌在 .list 文件里，OpenClash 覆写模块保持纯 ASCII**：部分 OpenClash/iStoreOS 环境的覆写模块 `[YAML]` 段会损坏中文/Emoji 策略组名（[已知坑](https://github.com/vernesong/OpenClash/discussions/5049)）。我们的设计靠 classical 规则自带目标规避它——所以 README 里给用户的覆写粘贴段（`RULE-SET` 行）绝不能写中文/Emoji 组名，组名只允许出现在生成物和 `POLICY` 表里。改架构时保持这一点。

## 常见任务

- **加域名**：`overrides/<组名>.list` 加一行 `HOST-SUFFIX,example.com,组名` → 重跑两个脚本 → 提交（两种格式一起提交）。
- **新策略组**：sync.py `LISTS` 登记上游 → export_clash.py `ORDER`（排位 = 优先级）+ `POLICY` 登记映射 → README 表格加一行 → 重跑。
- **提交信息**：沿用 conventional 风格前缀（`feat:` / `ci:` / `refactor:` / `sync:`）。

## 环境坑

- 本机直连 `github.com` / `api.github.com` 会被 SNI 重置（机场出口抖动，QX TUN 形态），git push 失败重试几次即可；`cdn.jsdelivr.net` 通常直连可达。
- GitHub 只重定向**仓库**改名，不重定向目录/文件改名——`quantumultx/` 的文件名就是三台设备 QX 的订阅 URL，改名必 404，动了要同步更新 Elric-Main.conf 并让用户重新导入。
- 周期任务在 GitHub Actions（周日 03:00 UTC）；本地手动触发用 workflow_dispatch，或直接跑脚本。
