---
name: skill-auditor
description: >
  Use when user asks to audit installed skills, detect skill duplicates,
  merge similar skills, check trigger overlaps, find Chinese support gaps,
  improve description precision, or fix trigger keyword issues.
  Runs pairwise analysis with configurable thresholds (duplicates ≥65%,
  conflicts ≥50%, trigger overlaps ≥40%). Flags missing trigger keywords
  and checks precision. Merges on approval — picks which to keep, folds
  the other in. Generates structured reports, asks before making changes.
  Also triggers on: skill cleanup, skill maintenance, organize skills,
  deduplicate skills, skill quality check, skill review, skill comparison,
  conflicting skills, description cleanup, trigger refinement,
  "too many skills", "skills are messy", "clean up my skills".
  Also triggers on Chinese: 技能审计, 技能清理, 技能合并, 重复技能, 技能冲突,
  触发条件, 技能优化, 技能重复, 技能检测, 技能整理, 技能管理, 技能审查,
  技能诊断, 技能瘦身, 技能精简, 描述优化, 触发词优化, 技能质量, 查重,
  技能覆盖, 清理技能, 我的技能太乱, 技能太多了, 检查一下技能.
---

# Skill Auditor

> **跨平台兼容：** 本技能自动检测运行平台并加载对应工具映射。检测结果永久缓存，后续触发不再重复检测。

## 平台检测（仅首次运行）

首次触发时自动检测平台，结果写入 `{SKILL_DIR}/references/platform.json`，以后直接读取缓存：

1. **检测平台** — 检查环境特征确定当前 AI 代理平台：
   - 有 `~/.claude/` → **Claude Code**（原生，无需映射）
   - 有 `~/.codex/config.toml` 或 `~/.codex/skills/` → **Codex CLI**
   - 有 `~/.gemini/skills/` 或 `~/.agents/skills/` → **Gemini CLI**
   - 有 `~/.config/github-copilot/` → **GitHub Copilot CLI**
   - 有 `~/.cursor/` → **Cursor**
   - 无法判断 → 询问用户

2. **加载映射** — 非 Claude Code 平台自动加载 `references/` 下对应工具映射

3. **缓存结果** — 写入 `platform.json`：
   ```json
   {"platform": "codex", "detected_at": "2026-06-13T14:30:00", "skill_dir": "~/.codex/skills/skill-auditor"}
   ```

后续每次触发直接读 `platform.json`，跳过检测步骤。

## Audit Workflow

Track progress with tasks when running an audit:

```markdown
- [ ] Phase 1: Run analysis script to collect data
- [ ] Phase 2: Present structured report to user
- [ ] Phase 3: Execute merges (if user approves)
- [ ] Phase 4: Fix trigger gaps (if user requests)
```

## How It Works

### Phase 1: Scan & Analyze

Run the analysis script:
```bash
python {SKILL_DIR}/scripts/analyze.py
```

> 其中 `{SKILL_DIR}` 是技能安装目录，根据检测到的平台确定：
> - Claude Code: `~/.claude/skills/skill-auditor`
> - Codex CLI: `~/.codex/skills/skill-auditor`
> - Gemini CLI: `~/.gemini/skills/skill-auditor`
> - 其他平台同理

This produces a JSON report with:
- **Skills table** — every installed skill with its description, length, concepts, Chinese analysis, and precision score
- **Duplicate pairs** (≥65% similarity) — skills so similar they likely do the same thing
- **Conflict pairs** (50-65%) — skills with significant semantic overlap
- **Trigger overlaps** (≥40% trigger phrase similarity) — skills that would activate on the same user request, even if described differently
- **Minor overlaps** (25-50%) — skills with related functionality
- **Chinese support gaps** — skills with no Chinese characters in description
- **Precision concerns** — descriptions that are too verbose, too vague, or missing trigger patterns

### Phase 2: Generate Human-Readable Report (逐项展示)

**不要一次性丢出完整报告。** 按顺序逐项展示，每项展示后给出具体选项让用户选择，再进入下一项。如果用户直接给指令（如"合并这两个"、"加中文"），按用户说的执行。

**关键规则：用户点击选项后，你必须给出具体实施方案，询问"这样实施可以吗？"，用户确认后直接执行，不要问多余的问题。**

展示顺序：

1. **概览 Summary** — 先给出总体数字：技能总数、重复对、冲突对、触发重叠、缺中文、精度问题
   - 然后列出选项让用户选：
     ```
     想看哪一项？
     1-触发重叠
     2-中文缺口
     3-精度问题
     4-修改技能内容（添加/删除/修改任意内容）
     5-按顺序逐项看
     ```

2. **逐项深入** — 根据用户选择，一次只展示一个类别。展示完给出具体操作选项。
   - 用户选择操作后 → 给出实施方案 → 询问"这样实施可以吗？" → 确认后直接执行
   - 用户选择"跳过" → 进入下一项
   - **任何时候用户想添加或删除技能内容，输入 4 回到修改模式**

各类别选项及对应实施方案：

   - **1. 重复对 (≥65%)** → 选项：合并 / 查看相似度明细 / 跳过
     - 合并方案示例："将 A 合并到 B，保留 B 的名称和目录，把 A 的独特内容追加到 B 后，将 A 标记为 alias"
     - **执行合并前，先用完整对比表格展示 A 和 B 的全部内容（包括完整工作流程）**

   - **2. 冲突对 (50-65%)** → 选项：分析冲突原因 / 调整描述 / 修改技能内容 / 跳过
     - 调整方案示例："在 B 的描述中添加`Use when...`限定场景，在 A 的描述中添加`Use when...`限定另一场景"
     - **分析前，读取两个技能的 SKILL.md，用对比表格展示双方完整工作流程**

   - **3. 触发重叠 (≥40%)** → 选项：合并 / 调整触发词 / 修改技能内容 / 查看明细 / 跳过
     - 合并方案示例："将 A 合并到 B，B 的描述加上 A 的独特触发词，删除 A"
     - 调整方案示例："在 A 的描述中添加排除条件，避免和 B 同时触发"
     - **合并或查看明细前，用对比表格展示双方 description、触发词、工作流程**

   - **4. 中文支持缺口** → 选项：逐个添加 / 批量添加 / 修改技能内容 / 跳过
     - 批量方案示例："对 12 个技能逐个在 description 末尾添加`Also triggers on Chinese: ...`，每个技能加 3-5 个相关中文关键词"
     - 逐个方案示例："先处理技能 X，在 desc 末尾添加`Also triggers on Chinese: ...`，展示 diff"

   - **5. 精度问题** → 选项：全部修复 / 选特定技能 / 修改技能内容 / 看建议 / 跳过
     - 全部修复方案示例："对 4 个精度问题技能分别：添加动作动词、补充触发场景、添加产出描述。逐个展示 diff"
     - 特定技能方案示例："先处理技能 X，[具体修复方案]，展示 diff"

   - **6. 推荐操作** → 选项：执行一项 / 批量执行 / 修改技能内容 / 完成
     - 方案示例："按顺序执行：①合并 grills ②添加中文 ③修复精度，每个步骤前展示方案并确认"

**修改技能内容（添加/删除）流程：**
- 用户选择修改 → 先读取该技能的完整 SKILL.md，展示给用户看：
  - **description**（触发条件）
  - **完整工作流程** — 展示所有标题层级和各阶段的核心指令（不是概述，是全部内容）
  - **资源文件**（scripts/references/assets）
  - 然后问你想怎么改进这个技能

**若用户希望对技能做深入改进（而不仅仅是简单修补）：** 转到下方"技能改进模式"章节，加载 creator 方法论执行完整改进循环。否则按简单修改流程执行。

- 用户描述需求后 → 展示要修改的文件、修改位置、新旧对比 → 问"这样实施可以吗？"
- 确认后 → 备份原文件 → 执行修改 → 记录操作日志

对每个类别的每个 pair，使用这个格式：

**Pair: A ↔ B**
- Overall similarity: XX%
- Trigger similarity: XX%
- Common concepts: [list]
- Recommendation: [merge / add Chinese keywords / improve description / no action needed]

始终包含原始相似度分数和触发词相似度分数，让用户能做 informed decision。

---

### 操作记录与回滚机制

每次修改文件前，必须保存操作记录，便于日后回滚。

**备份规则：**
1. 备份目录：`{SKILL_DIR}/references/backups/`
2. 每次修改前，将被修改文件的原始内容复制到备份目录
3. 备份文件名格式：`{技能名}_{YYYYMMDD_HHMMSS}_before_{操作类型}.md`
4. 存在已有备份时不覆盖，追加新备份

**操作日志：**
每次执行修改后，追加一条记录到 `{SKILL_DIR}/references/operation_log.json`：

```json
{
  "timestamp": "2026-06-13T14:30:00",
  "operation": "merge | add_chinese | fix_precision | modify_description | deep_improve",
  "target_skill": "技能名",
  "summary": "做了什么、为什么",
  "backup_file": "references/backups/xxx.md",
  "diff": "变更摘要（修改了什么字段，新旧对比要点）"
}
```

**回滚流程：**
- 如果用户要求回滚，读取对应备份文件，展示备份内容和当前内容的 diff
- 询问"确认回滚到备份版本？"，确认后用备份内容覆盖当前文件
- 在操作日志中添加一条回滚记录

---

### Phase 3: Merge Skills (on User Request)

当用户选择合并时，**先展示两个技能的完整内容对比表格，再出方案：**

1. **读取 A 和 B 的完整 SKILL.md**，用表格对比展示：

   | 维度 | A (被合并) | B (保留) |
   |------|-----------|---------|
   | 名称 | | |
   | description | | |
   | 触发词 | | |
   | 核心流程 | 所有标题层级和各阶段指令 | 所有标题层级和各阶段指令 |
   | 脚本资源 | scripts/ 下文件列表 | scripts/ 下文件列表 |
   | 参考文件 | references/ 下文件列表 | references/ 下文件列表 |
   | 精度评分 | X.X | X.X |

2. 然后给出合并方案（见下方步骤）

1. Create a backup of B's SKILL.md first
2. Read the content of both SKILL.md files
3. Identify the unique/valuable content from A that B doesn't have
4. Preserve the skill **name** and **description** from the target (B)
5. Append A's unique instructions, examples, or patterns into B's body
6. If A has useful trigger keywords that B lacks, add them to B's description
7. Update the description if A's trigger coverage complements B's
8. Ask user what to do with A (delete? rename? keep as alias?)
9. Execute only with explicit user confirmation

**Example:** If merging `grill-me` into `grill-with-docs`, keep `grill-with-docs` as the survivor. Append `grill-me`'s unique stress-test patterns and trigger keywords ("grill me" mention) into the survivor's description. Ask user whether to delete `grill-me` or keep as alias.

**Merge rules:**
- Keep the surviving skill's name and directory
- Never delete a skill without explicit user confirmation
- Preserve all unique scripts/references from the absorbed skill
- Add a comment noting the merge in the surviving skill

### Phase 4: Fix Trigger Gaps (on User Request)

When the user wants to fix a skill's trigger conditions:

1. For skills missing Chinese support: add an "Also triggers on Chinese:" line with relevant Chinese keywords (e.g., 优化, 重构, 测试, 架构, 设计, 调试, etc.)
2. For verbose descriptions: trim to under 300 chars, keep the essential trigger patterns, remove filler words
3. For vague descriptions: add concrete trigger scenarios ("Use when user wants to X, Y, or Z")
4. For precision issues: add action verbs that describe what the skill does

Always show the before/after diff before applying.

---

## 技能改进模式（Skill Improvement via Creator）

在审计过程中，当用户发现某个技能有问题（重复、精度差、触发重叠、缺中文等），并且表示**想深入改进这个技能本身**（而非仅仅做简单修补如加中文、改触发词），按以下步骤操作：

### Step 1: 加载 Creator 方法论

读取 `references/creator-core.md`，了解 skill-creator 的完整迭代流程：
- 测试方法论（并行 with_skill vs baseline）
- 评估系统（assertions + benchmark 聚合 + human review）
- 改进四原则（从反馈泛化、保持精简、解释 WHY、找出重复工作）
- Description 优化流程

### Step 2: 遵循改进循环

以 creator-core 的方法论为指导，执行改进循环：

```
诊断问题 → 修改 SKILL.md → 创建/更新测试用例 → 运行评估（with_skill vs 旧版本）→ 展示对比结果 → 根据反馈迭代
```

### Step 3: 运行对照测试

创建测试工作区（`<workspace>/iteration-N/`），对修改后的技能做基线对照测试。

### Step 4: 展示评估

尽可能用 `eval-viewer/generate_review.py` 生成对比页面供用户审查。

### Step 5: 根据反馈迭代

阅读 feedback.json，泛化改进建议（不做过拟合），继续循环直到满意。

---

## Important

- **Never modify files without user approval**
- Always show a diff/preview before making changes
- **Always back up before editing** — saves to `references/backups/` and logs to `references/operation_log.json`
- List ALL results in the report, not just the top matches
- The user works in Chinese, so present the report in Chinese
