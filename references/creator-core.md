# Skill Creator 核心方法论

本文件总结了 skill-creator 的开发迭代流程，供 skill-auditor 改进时参考。

---

## 核心迭代循环

```
草拟技能 → 运行测试 → 评估结果 → 改进技能 → 重复
```

每个环节都有配套的工具和方法论。

---

## 一、测试方法论

### 并行运行

每个测试用例同时启动两个子 agent：

| 配置 | 用途 |
|------|------|
| **with_skill** | 加载目标技能执行任务 |
| **baseline** | 新技能 → 无技能对照 / 改进技能 → 旧版本对照 |

两者在同一轮中并行启动，结果同时返回。

### 工作区结构

```
<skill-name>-workspace/
├── iteration-N/
│   ├── skill-snapshot/       # (改进现有技能时)旧版本备份
│   ├── eval-<name>/
│   │   ├── eval_metadata.json  # 评估元数据：id, name, prompt, assertions
│   │   ├── with_skill/outputs/ # 带技能的输出
│   │   ├── without_skill/      # 基线输出
│   │   ├── grading.json        # 评分结果
│   │   └── timing.json         # 耗时数据
│   └── benchmark.json          # 聚合基准
```

### 时序数据捕获

子 agent 完成后，通知中包含 `total_tokens` 和 `duration_ms`，**必须立即保存**到 `timing.json`，不可恢复：

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3
}
```

---

## 二、评估系统

### Assertions（定量断言）

每个测试用例定义一组断言，用 `agents/grader.md` 的流程进行评估：

- **PASS**: 有明确的证据表明断言成立，且证据反映了实质性完成而非表面合规
- **FAIL**: 无证据 / 证据矛盾 / 不可验证 / 证据表面化

**好的断言是有区分度的** — 正确完成时通过，错误时失败。不要让断言检查文件名而不检查内容。

### Benchmark 聚合

用聚合脚本生成 `benchmark.json`，包含：
- 每个配置（with_skill vs baseline）的通过率、耗时、token 数
- 均值 ± 标准差
- Delta 对比
- 分析师的观察笔记

### Human Review（定性评估）

用 `eval-viewer/generate_review.py` 生成 HTML 浏览器界面，用户可逐条查看输出并提交反馈。对于无显示环境，使用 `--static` 生成独立 HTML 文件。

### Analyst Pass

聚合数据后，检查：
- **非区分性断言** — 两种配置都 100% 通过或失败的断言
- **高方差评估** — 可能不稳定的用例
- **时间/Token 权衡** — 技能带来的性能提升是否值得额外开销

---

## 三、改进原则

### 1. 从反馈中泛化（不做过拟合）

改进时不要只针对那几个测试用例修修补补。测试数据是有限的，但技能会被用在各种场景。宁可尝试不同的比喻、不同的工作模式，也不要用一堆 `MUST` / `ALWAYS` 来压死灵活性。

### 2. 保持 Prompt 精简

阅读执行 transcript 而不是只看最终输出。如果技能导致模型花费大量时间做无用功，就删除那些导致此行为的指令。

### 3. 解释 WHY

不要只是罗列指令。LLM 有很好的心智理论能力，理解背后的「为什么」后能做出更好的判断。写 `ALWAYS` / `NEVER` 是一个黄牌警告 — 尝试重新组织，解释为什么这样做很重要。

### 4. 找出重复工作

阅读所有测试用例的 transcript，看它们是否独立编写了相似的辅助脚本。如果 3 个用例都写了 `create_docx.py`，这就是信号：把这个脚本打包进技能。

---

## 四、Description 优化流程

### Step 1: 生成触发评估查询

创建 20 个评估查询（混合应该触发和不应触发的场景），保存为 JSON。

**应该触发的查询（8-10个）**：
- 不同措辞：正式、随意
- 不明确命名的隐式需求
- 罕见用例、与其他技能竞争的场景

**不应触发的查询（8-10个）**：
- 最有用的是"接近但不触发"— 共享关键词但实际需要不同技能的查询
- 不要用明显无关的查询（如 PDF 技能用"写斐波那契函数"做反例没有意义）

查询要具体：包含文件路径、用户背景、列名、公司名、URL，而不是抽象的"格式化数据"。

### Step 2: 用户审查

用 `assets/eval_review.html` 模板生成交互页面，用户可编辑查询、切换 should_trigger 标记、最终导出 eval_set.json。

### Step 3: 运行优化循环

```bash
python -m scripts.run_loop \
  --eval-set <trigger-eval.json> \
  --skill-path <skill-path> \
  --model <model-id> \
  --max-iterations 5 \
  --verbose
```

流程：60% 训练 / 40% 保留测试 → 评估当前描述（每条 3 次运行）→ 模型提出改进 → 重新评估 → 迭代最多 5 次。

最佳描述根据测试集得分选择（而非训练集），防止过拟合。

---

## 五、关键 JSON Schema

### evals.json

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "用户提示词",
      "expected_output": "预期结果描述",
      "files": ["evals/files/sample1.pdf"],
      "assertions": ["输出包含 X", "使用了脚本 Y"]
    }
  ]
}
```

### grading.json

```json
{
  "expectations": [
    { "text": "断言描述", "passed": true, "evidence": "证据引用" }
  ],
  "summary": { "passed": 2, "failed": 1, "total": 3, "pass_rate": 0.67 }
}
```

### benchmark.json

See `references/schemas.md` in skill-creator for the full schema.

包含 `runs[]`（每个用例的通过率/耗时/token）、`run_summary`（with_skill 和 baseline 的均值±标准差）、`notes`（分析师观察）。

---

## 六、Decision Flow

```
用户需求
  │
  ├─ 创建新技能 → 访谈 → 草拟 SKILL.md
  │                → 创建测试用例（evals.json）
  │                → 并行运行（with_skill vs without_skill）
  │                → 评分 + 聚合 + 分析师观察
  │                → generate_review.py 展示给用户
  │                → 根据反馈改进 → 重复
  │                → Description 优化（可选）
  │                → 打包发布
  │
  └─ 改进现有技能 → 快照旧版本
                   → 修改 SKILL.md
                   → 运行测试（with_skill vs 快照）
                   → 评估 + 展示（--previous-workspace）
                   → 根据反馈改进 → 重复
```

---

## 参考来源

完整内容请参阅 skill-creator 的以下文件：
- `SKILL.md` — 主流程
- `agents/grader.md` — 断言评分流程
- `agents/comparator.md` — 盲对比流程
- `agents/analyzer.md` — 基准分析和胜因分析
- `references/schemas.md` — 完整 JSON schema
