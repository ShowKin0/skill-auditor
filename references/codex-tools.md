# Codex CLI Tool Mapping

本技能使用 Claude Code 工具名编写。在 Codex CLI 上运行时，请按以下映射翻译：

| 技能中的工具名 | Codex CLI 对应工具 |
|---------------|-------------------|
| `Read` (读文件) | 使用原生文件读取工具 |
| `Write` (写文件) | 使用原生文件写入工具 |
| `Edit` (编辑文件) | 使用原生文件编辑工具 |
| `Bash` (运行命令) | 使用原生 shell 工具 |
| `Grep` (搜索文件内容) | 使用原生搜索工具 |
| `Glob` (按名搜索文件) | 使用原生文件搜索工具 |
| `TodoWrite` (任务追踪) | `update_plan` |
| `Skill` (调用技能) | 技能已原生加载，直接执行指令 |

## 子代理调度

当技能要求使用 Task 工具分发子代理时：

| 技能指令 | Codex CLI 对应 |
|---------|---------------|
| Task 工具分发子代理 | `spawn_agent` |
| 等待子代理结果 | `wait_agent` |
| 关闭子代理释放槽位 | `close_agent` |
| 多个并行 Task | 多个并行 `spawn_agent` 调用 |

需要启用多代理功能：在 `~/.codex/config.toml` 中添加：

```toml
[features]
multi_agent = true
```

## 分析脚本

技能中的 `python ~/.claude/skills/skill-auditor/scripts/analyze.py` 命令。Codex 中技能安装路径为 `~/.codex/skills/skill-auditor/`，请相应调整路径：

```bash
python ~/.codex/skills/skill-auditor/scripts/analyze.py
```
