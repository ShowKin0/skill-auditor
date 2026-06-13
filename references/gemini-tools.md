# Gemini CLI Tool Mapping

本技能使用 Claude Code 工具名编写。在 Gemini CLI 上运行时，请按以下映射翻译：

| 技能中的工具名 | Gemini CLI 对应工具 |
|---------------|-------------------|
| `Read` (读文件) | `read_file` |
| `Write` (写文件) | `write_file` |
| `Edit` (编辑文件) | `replace` |
| `Bash` (运行命令) | `run_shell_command` |
| `Grep` (搜索文件内容) | `grep_search` |
| `Glob` (按名搜索文件) | `glob` |
| `TodoWrite` (任务追踪) | `write_todos` |
| `Skill` (调用技能) | `activate_skill` |
| `WebSearch` | `google_web_search` |
| `WebFetch` | `web_fetch` |

## 子代理调度

当技能要求使用 Task 工具分发子代理时，使用 `@generalist`：

| 技能指令 | Gemini CLI 对应 |
|---------|---------------|
| Task 工具分发子代理 | `@generalist` 附带完整 prompt |
| 多个并行 Task | 在同一个 prompt 中请求多个并行 `@agent` 调用 |

## 分析脚本

技能中的 `python ~/.claude/skills/skill-auditor/scripts/analyze.py` 命令。Gemini 中安装路径为 `~/.gemini/skills/skill-auditor/`，请相应调整路径：

```bash
python ~/.gemini/skills/skill-auditor/scripts/analyze.py
```
