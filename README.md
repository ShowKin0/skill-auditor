# Skill Auditor — 技能审计工具

审计已安装的 Claude Code 技能，检测重复、冲突、触发覆盖缺口和描述精度问题，并提供合并与改进能力。

## 概述

Skill Auditor 是一个元技能——它管理其他技能。当你觉得"技能太多了"、"有些功能重复了"、"中文触发不好使"时，用它来做一个全面的技能健康检查。

## 核心功能

| 功能             | 阈值              | 说明                                   |
| ---------------- | ----------------- | -------------------------------------- |
| **重复检测**     | ≥65% 相似度       | 找到功能几乎相同的技能对               |
| **冲突检测**     | 50-65% 相似度     | 找到语义重叠、可能选错的技能对         |
| **触发重叠**     | ≥40% 触发词相似度 | 找到同一句话可能同时触发的技能对       |
| **中文支持检查** | 无中文关键词      | 标记未支持中文触发的技能               |
| **描述精度评分** | <0.70 分          | 标记描述太啰嗦/太模糊/缺动作动词的技能 |
| **资源检查**     | —                 | 统计每个技能的脚本、参考文件和资源文件 |

## 审计流程

### Phase 1: 扫描与分析

运行分析脚本收集所有技能的元数据：

```bash
python ~/.claude/skills/skill-auditor/scripts/analyze.py
```

输出 JSON 报告包含：

- 所有技能的描述、概念提取、精度评分
- 成对比较（相似度 + 触发词相似度）
- 中文支持缺口
- 精度问题列表

### Phase 2: 逐项展示报告

按顺序展示，每项给出具体操作选项：

1. **概览** — 总数、重复对、冲突对、触发重叠、缺中文数、精度问题数
2. **重复对** (≥65%) → 合并 / 查看明细 / 跳过
3. **冲突对** (50-65%) → 分析原因 / 调整描述 / 修改内容 / 跳过
4. **触发重叠** (≥40%) → 合并 / 调整触发词 / 修改内容 / 跳过
5. **中文缺口** → 逐个加 / 批量加 / 修改内容 / 跳过
6. **精度问题** → 全部修复 / 选特定技能 / 修改内容 / 跳过

### Phase 3: 合并技能

- 展示两个技能的完整对比表格（名称、description、触发词、核心流程、资源、精度分数）
- 生成合并方案，用户确认后执行
- 自动备份原文件

### Phase 4: 修复触发缺口

- 添加中文触发关键词
- 精简或补充 description
- 展示 diff 后应用

## 评估机制

该技能自带 6 个评估用例（`evals/evals.json`），覆盖：

1. 完整审计报告生成
2. 特定技能对的合并分析
3. 中文触发关键词检查
4. 触发覆盖重叠分析
5. 描述质量全面检查
6. 重复技能确认与合并

## 操作安全

- **永不自动修改文件** — 每次修改前需用户确认
- **自动备份** — 修改前将被修改文件备份到 `references/backups/`
- **操作日志** — 每次操作记录到 `references/operation_log.json`，支持回滚

## 深度改进模式

当用户发现某个技能本身有问题（重复、精度差、触发重叠、缺中文等）并希望深入改进时，加载 Creator 方法论执行完整改进循环：

```
诊断 → 修改 SKILL.md → 创建/更新测试 → 运行评估(with_skill vs 旧版)
→ 展示对比结果 → 根据反馈迭代
```

## 技术架构

- **分析引擎**: `scripts/analyze.py` — YAML frontmatter 解析、语义归一化、Jaccard 相似度计算
- **核心算法**: 七维组合相似度（原始词 15% + 归一化概念 15% + 触发词 20% + 短语 15% + 正文 10% + 中文 10% + 名称 15%）
- **同义词归一化**: 将近义词映射到统一概念组（如 grill/interview → interrogate）
- **引用**: `references/creator-core.md` — skill-creator 方法论文档

## 安装

所有主流 AI 编码代理（Claude Code、Codex CLI、Gemini CLI、GitHub Copilot CLI、Cursor）均可使用。SKILL.md 启动时会**自动检测平台**并加载对应工具映射，无需手动配置。此技能无需额外依赖（分析脚本仅使用 Python 内置库）。

### Claude Code

```bash
git clone https://github.com/ShowKin0/skill-auditor.git ~/.claude/skills/skill-auditor
```

启动后输入"技能审计"或"检查一下技能"即可触发。

### Codex CLI

```bash
git clone https://github.com/ShowKin0/skill-auditor.git ~/.codex/skills/skill-auditor
```

Codex CLI 与 Claude Code 使用相同的 `SKILL.md` 格式，自动发现技能。

### Gemini CLI

```bash
git clone https://github.com/ShowKin0/skill-auditor.git ~/.gemini/skills/skill-auditor
```

Gemini CLI 同样兼容 `SKILL.md` 格式，还支持以下管理命令：

```bash
gemini skills list      # 查看已安装技能
gemini skills reload    # 重新加载技能列表
```

也可以使用 `~/.agents/skills/` 目录（Gemini 的别名目录，便于跨代理兼容）。

### Cursor

Cursor 通过 `.cursor-plugin/plugin.json` 加载技能。创建一个包装插件：

```bash
# 1. 放置技能目录
mkdir -p ~/.cursor/plugins/skill-auditor/skills
git clone https://github.com/ShowKin0/skill-auditor.git ~/.cursor/plugins/skill-auditor/skills/skill-auditor

# 2. 创建 plugin.json
cat > ~/.cursor/plugins/skill-auditor/plugin.json << 'EOF'
{
  "name": "skill-auditor",
  "description": "Audit installed skills, detect duplicates and conflicts",
  "skills": "./skills/"
}
EOF
```

### GitHub Copilot CLI

```bash
git clone https://github.com/ShowKin0/skill-auditor.git ~/.config/github-copilot/plugins/skill-auditor/skills/skill-auditor
```

在对应 `plugin.json` 中配置 `skills` 字段指向技能目录即可。

### 前置依赖

- Python 3.8+（用于运行分析脚本 `scripts/analyze.py`）
- 分析脚本仅使用 Python 内置标准库，无需额外 pip 安装
