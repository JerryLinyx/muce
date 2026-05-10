# CLAUDE.md

A-share research / backtesting toolkit (Python, `uv`-managed). Code in `src/`，docs in `docs/`，tests in `tests/`。深入资料见 [docs/README.md](docs/README.md)。

## 项目本地 Skills（重要）

本仓库在 `.claude/skills/` 下放了**项目专属 skill**，不会出现在 session 启动时的全局 skills 列表里。**遇到对应触发场景时必须主动加载并使用**：

| Skill | 路径 | 何时触发 |
|---|---|---|
| `neat-freak` | [.claude/skills/neat-freak/SKILL.md](.claude/skills/neat-freak/SKILL.md) | 会话收尾、文档/记忆同步、用户说"整理一下 / 同步一下 / 收尾 / tidy up / sync up / 这个阶段做完了 / 新人能直接上手"等 |
| `devlog-maintainer` | （全局 skill，通过 `Skill` 工具加载） | bug 修复/需求交付/review 验证/版本封存后，维护 `docs/devlog/` 下的 records/current/appendix/archive/CHANGELOG |

加载方式：直接 `Read` 对应 SKILL.md（项目本地 skill 不能用 `Skill` 工具调用），全局 skill 用 `Skill` 工具加载，按其中流程执行。

新增项目本地 skill 时，**同步在这张表里登记一行**，否则下次会话又会"看不见"。

## 常用命令

```bash
uv sync --extra test             # 装依赖（含测试）
uv sync --extra all              # 全部 extras
uv run pytest                    # 跑测试
uv run quant-data download ...   # 拉行情数据
uv run quant-backtest validate ...  # backtrader 验证
uv run quant-backtest sweep ...     # vectorbt 参数扫描
uv run quant-api                 # 启动只读 API
```

完整 CLI 用法见 [README.md](README.md)（英文）与 [README-CN.md](README-CN.md)（中文），深入资料见 [docs/README.md](docs/README.md)。
