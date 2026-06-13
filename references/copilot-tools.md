# GitHub Copilot CLI Tool Mapping

本技能使用 Claude Code 工具名编写。在 Copilot CLI 上运行时，请按以下映射翻译：

| 技能中的工具名 | Copilot CLI 对应工具 |
|---------------|-------------------|
| `Read` (读文件) | `view` |
| `Write` (写文件) | `create` |
| `Edit` (编辑文件) | `edit` |
| `Bash` (运行命令) | `bash` |
| `Grep` (搜索文件内容) | `grep` |
| `Glob` (按名搜索文件) | `glob` |
| `TodoWrite` (任务追踪) | `sql` 操作内置 `todos` 表 |
| `Skill` (调用技能) | `skill` |
| `WebFetch` | `web_fetch` |
| `WebSearch` | 无对应 — 使用 `web_fetch` 访问搜索引擎 URL |
| `Task` 子代理 | `task` 配合 `agent_type` 参数 |

## 子代理调度

| 技能指令 | Copilot CLI 对应 |
|---------|---------------|
| Task 工具分发子代理 | `task` 设置 `agent_type: "general-purpose"` |
| 多个并行 Task | 多个 `task` 调用 |
| 查看 Task 状态/输出 | `read_agent`, `list_agents` |

## 分析脚本

技能中的 `python ~/.claude/skills/skill-auditor/scripts/analyze.py` 命令。Copilot 中路径不同，请相应调整。

## 注意事项

- `EnterPlanMode` / `ExitPlanMode` 无对应 — 在主会话中直接执行
- 支持异步 shell: `bash` 加 `async: true` 参数启动后台命令
