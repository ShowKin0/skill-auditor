"""
skill-auditor: Analyze installed skills for duplicates, conflicts, and trigger gaps.

Scans ~/.claude/skills/ (SKILL.md files), extracts frontmatter descriptions,
and produces a structured JSON report covering:
  - Pairwise similarity between skills (for duplicate/overlap detection)
  - Chinese keyword coverage (for Chinese trigger gap detection)
  - Description precision scoring (for verbose/imprecise detection)
  - Conflict scoring (skills that would trigger on same user request)
"""

import os
import re
import json
from pathlib import Path

SKILLS_DIR = Path.home() / ".claude" / "skills"


def read_frontmatter(filepath):
    """Extract YAML frontmatter fields from SKILL.md (handles block scalars and multiline).
    Returns (fm, body) where body is the markdown content after frontmatter."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    fm = {}
    body = ""
    match = re.match(r"^---\s*\n(.*?)\n(?:---|\.\.\.)", content, re.DOTALL)
    if not match:
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if match:
        yaml_block = match.group(1)
        body = content[match.end():].strip()
    else:
        return fm, ""

    lines = yaml_block.split("\n")

    current_key = None
    current_value = None
    in_block_scalar = False
    block_scalar_style = None  # '>' folded, '|' literal
    block_indent = 0

    for line in lines:
        # Check for new key-value pair (non-indented line with colon)
        kv_match = re.match(r"^(\w[\w_-]*)\s*:(?:\s*(.*))?$", line)
        if kv_match is not None:
            # Save previous key if any
            if current_key is not None and current_value is not None:
                fm[current_key] = current_value.strip()

            current_key = kv_match.group(1)
            raw_value = kv_match.group(2) or ""

            # Check for block scalar indicators
            if raw_value.strip() == ">":
                in_block_scalar = True
                block_scalar_style = "folded"
                block_indent = 0
                current_value = ""
            elif raw_value.strip() == "|":
                in_block_scalar = True
                block_scalar_style = "literal"
                block_indent = 0
                current_value = ""
            elif raw_value.strip() == ">-":
                in_block_scalar = True
                block_scalar_style = "folded_strip"
                block_indent = 0
                current_value = ""
            elif raw_value.strip() == "|-":
                in_block_scalar = True
                block_scalar_style = "literal_strip"
                block_indent = 0
                current_value = ""
            else:
                in_block_scalar = False
                # Handle quoted inline values
                val = raw_value.strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:-1]
                elif val.startswith("'") and val.endswith("'"):
                    val = val[1:-1]
                current_value = val

        elif in_block_scalar and line.strip() == "":
            # Empty line inside block scalar
            if current_value is not None:
                current_value += "\n"

        elif in_block_scalar:
            stripped = line.lstrip()
            if stripped and (block_indent == 0 or len(line) - len(stripped) >= block_indent):
                if block_indent == 0:
                    block_indent = len(line) - len(stripped)

                if block_scalar_style in ("folded", "folded_strip"):
                    if current_value and not current_value.endswith("\n"):
                        current_value += " " + stripped
                    else:
                        current_value += stripped
                else:  # literal or literal_strip
                    if current_value and not current_value.endswith("\n"):
                        current_value += "\n" + stripped
                    else:
                        current_value += stripped

        elif current_key is not None and not in_block_scalar:
            # Continuation of inline value (indented)
            stripped = line.strip()
            if stripped and line[0] in (" ", "\t") and current_value is not None:
                current_value += " " + stripped

    # Save last key
    if current_key is not None and current_value is not None:
        fm[current_key] = current_value.strip()

    # Handle folded scalar newlines -> spaces
    for k, v in fm.items():
        if isinstance(v, str) and "\n" in v:
            # Folded style: newlines become spaces
            if block_scalar_style in ("folded", "folded_strip"):
                fm[k] = re.sub(r"\n+", " ", v)

    return fm, content


def normalize_term(word):
    """Normalize words to concept groups for semantic matching."""
    synonym_groups = {
        # Grilling / interviewing
        "grill": "interrogate", "grilled": "interrogate", "grilling": "interrogate",
        "interview": "interrogate", "relentlessly": "interrogate",
        # Planning / design
        "plan": "planning", "plans": "planning", "planning": "planning",
        "design": "planning", "designs": "planning", "spec": "planning",
        "prd": "planning", "architecture": "planning",
        # Stress-test / validation
        "stress": "verify", "challenge": "verify", "challenges": "verify",
        "validate": "verify", "validation": "verify", "verify": "verify",
        "test": "testing", "tests": "testing", "testing": "testing",
        # Code/codebase
        "code": "code", "codebase": "code", "codes": "code",
        "project": "code", "repo": "code", "repository": "code",
        # Skill creation
        "skill": "skill", "skills": "skill", "agent": "agent", "agents": "agent",
        # Issue/ticket management
        "issue": "task", "issues": "task", "ticket": "task", "tickets": "task",
        "triage": "task", "workflow": "task",
        # Writing/creating
        "create": "create", "build": "create", "make": "create", "write": "create",
        "generate": "create", "convert": "create", "publish": "create",
        "break": "create", "turn": "create",
        # Fixing/improving
        "fix": "improve", "debug": "improve", "improve": "improve",
        "optimize": "improve", "refactor": "improve", "clean": "improve",
        "consolidate": "improve", "tighten": "improve",
        # Managing/organizing
        "manage": "manage", "organize": "manage", "setup": "manage",
        "configure": "manage", "install": "manage",
        # Finding/discovering
        "find": "find", "search": "find", "discover": "find", "query": "find",
        # Reviewing
        "review": "review", "check": "review", "audit": "review",
        # Documentation
        "doc": "doc", "docs": "doc", "document": "doc", "documentation": "doc",
        "md": "doc", "markdown": "doc",
        # User
        "user": "user", "users": "user",
        # Decision/understanding
        "decision": "decision", "decisions": "decision", "understanding": "decision",
        "terminology": "decision", "language": "decision", "domain": "decision",
        "context": "decision",
    }
    return synonym_groups.get(word, word)


def extract_concepts(description):
    """Extract meaningful concepts from a description string."""
    if not description:
        return {
            "all": set(), "actions": set(), "domains": set(),
            "chinese": set(), "bigrams": set(), "normalized": set(),
        }

    text = description.lower()
    text_clean = re.sub(r"[^\w\s一-鿿]", " ", text)

    # Stopwords
    stopwords = {
        "the", "and", "for", "use", "when", "with", "this", "that",
        "from", "you", "are", "not", "can", "all", "has", "how",
        "its", "was", "but", "also", "any", "each", "than", "will",
        "should", "would", "could", "need", "must", "into", "about",
        "your", "their", "they", "what", "who", "which", "where",
        "want", "ask", "asks", "mentions", "says", "tells", "does",
        "after", "before", "such", "like", "just", "very", "well",
        "only", "even", "then", "them", "over", "used", "using",
        "might", "that", "these", "those", "have", "been", "being",
        "some", "does", "done", "going", "make", "made", "does",
        "also", "more", "much", "many", "still", "yet", "already",
        "both", "each", "every", "few", "into", "onto", "upon",
        "than", "then", "here", "there", "where", "while", "during",
        "without", "within", "across", "through", "among", "between",
        "because", "since", "until", "though", "although", "other",
        "another", "various", "certain", "specific", "particular",
    }

    # Extract words
    eng_words = set()
    tokens = text_clean.split()
    for w in tokens:
        if re.match(r"^[a-z]{3,}$", w) and w not in stopwords:
            eng_words.add(w)

    # Chinese concepts (2-6 chars)
    chinese_phrases = set()
    chinese_chars = re.findall(r"[一-鿿]{2,6}", text_clean)
    chinese_phrases.update(chinese_chars)

    # Extract trigger-specific portion — ALL matching patterns, not just first
    trigger_terms = set()
    trigger_patterns = [
        r"(?:use\s+when|triggers?\s+on|when\s+user|whenever|examples?:)\s*(.+?)(?=use\s+when|triggers?\s+on|when\s+user|whenever|examples?:|also\s+triggers|$)",
        r"(?:also\s+triggers?\s+on\s+Chinese)\s*:\s*(.+?)$",
    ]
    combined_triggers = ""
    for pat in trigger_patterns:
        for m in re.finditer(pat, text, re.IGNORECASE | re.DOTALL):
            combined_triggers += " " + m.group(1)

    if combined_triggers:
        trigger_clean = re.sub(r"[^\w\s一-鿿]", " ", combined_triggers.lower())
        for w in trigger_clean.split():
            if re.match(r"^[a-z]{3,}$", w) and w not in stopwords:
                trigger_terms.add(normalize_term(w))
            # Also capture Chinese keywords from trigger section
            if re.match(r"^[一-鿿]{2,6}$", w):
                trigger_terms.add(w)

    # Normalize ALL words to concept groups (all words, not just changed ones)
    normalized = set()
    for w in eng_words:
        normalized.add(normalize_term(w))

    # Bigrams (all meaningful words including stopwords for structural matching)
    all_words = [w for w in tokens if re.match(r"^[a-z]{2,}$", w)]
    bigrams = set()
    for i in range(len(all_words) - 1):
        bigrams.add(f"{all_words[i]} {all_words[i+1]}")

    action_verbs = {
        "create", "build", "make", "write", "edit", "modify", "update",
        "delete", "remove", "fix", "debug", "test", "analyze", "review",
        "refactor", "optimize", "improve", "generate", "convert", "transform",
        "search", "find", "query", "fetch", "download", "upload",
        "deploy", "publish", "release", "configure", "setup", "install",
        "manage", "organize", "plan", "design", "implement", "integrate",
        "validate", "verify", "check", "monitor", "track", "report",
        "extract", "parse", "render", "display", "visualize", "export",
        "import", "sync", "backup", "restore", "migrate", "merge",
        "break", "turn", "tell", "give", "help", "cover",
    }
    domain_nouns = {
        "code", "file", "data", "api", "database", "config",
        "test", "doc", "docs", "document", "skill", "plugin", "component",
        "module", "service", "function", "class", "interface", "schema",
        "model", "view", "controller", "route", "middleware", "hook",
        "script", "command", "tool", "library", "package", "dependency",
        "image", "video", "audio", "text", "markdown", "html", "css",
        "javascript", "python", "typescript", "sql", "graphql", "rest",
        "ui", "ux", "frontend", "backend", "fullstack", "mobile",
        "web", "app", "server", "client", "network", "security",
        "auth", "user", "account", "payment", "email", "notification",
        "market", "stock", "trade", "finance", "chart", "report",
        "pdf", "excel", "csv", "json", "yaml", "xml", "image",
        "plan", "design", "prd", "issue", "issues", "ticket", "workflow",
        "architecture", "agent", "agents", "project", "repo", "repository",
        "context", "session", "branch", "codebase", "feature", "bug",
    }

    actions = eng_words & action_verbs
    domains = eng_words & domain_nouns

    return {
        "all": eng_words | chinese_phrases,
        "actions": actions,
        "domains": domains,
        "chinese": chinese_phrases,
        "bigrams": bigrams,
        "normalized": normalized,
        "trigger": trigger_terms,
    }


def jaccard_similarity(set_a, set_b):
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def extract_name_tokens(name):
    """Extract meaningful tokens from skill name for similarity matching."""
    tokens = set()
    # Split on hyphens and underscores
    parts = re.split(r"[-_]", name.lower())
    for part in parts:
        if len(part) >= 3 and part not in {"the", "and", "for", "use", "with"}:
            tokens.add(part)
    return tokens


def combined_similarity(concepts_a, concepts_b, body_a, body_b, name_a, name_b):
    """
    Multi-faceted similarity combining raw terms, normalized concepts,
    trigger phrases, bigrams, body content, and name overlap.
    """
    all_sim = jaccard_similarity(concepts_a["all"], concepts_b["all"]) * 0.15
    norm_sim = jaccard_similarity(concepts_a["normalized"], concepts_b["normalized"]) * 0.15
    trigger_sim = jaccard_similarity(concepts_a["trigger"], concepts_b["trigger"]) * 0.20
    phrase_sim = jaccard_similarity(concepts_a["bigrams"], concepts_b["bigrams"]) * 0.15

    # Body content overlap
    body_norm_sim = jaccard_similarity(body_a["normalized"], body_b["normalized"]) * 0.10

    # Chinese concept overlap
    chinese_sim = jaccard_similarity(concepts_a["chinese"], concepts_b["chinese"]) * 0.10

    # Name overlap
    name_a_tokens = extract_name_tokens(name_a)
    name_b_tokens = extract_name_tokens(name_b)
    name_sim = jaccard_similarity(name_a_tokens, name_b_tokens) * 0.15

    return all_sim + norm_sim + trigger_sim + phrase_sim + body_norm_sim + chinese_sim + name_sim


def analyze_chinese_support(description):
    """Analyze Chinese support in a description."""
    if not description:
        return {
            "has_chinese": False, "chinese_ratio": 0,
            "has_chinese_triggers": False, "gaps": ["Description is empty"],
        }

    has_chinese = bool(re.search(r"[一-鿿]", description))
    has_chinese_triggers = bool(
        re.search(r"(?:triggers?\s+on\s+Chinese|chinese[s\:])", description, re.IGNORECASE)
    )

    all_chars = len(description.strip())
    chinese_chars = len(re.findall(r"[一-鿿]", description))
    chinese_ratio = chinese_chars / all_chars if all_chars > 0 else 0

    gaps = []
    if not has_chinese:
        gaps.append(
            "No Chinese characters in description — Chinese-speaking users "
            "may not trigger this skill naturally"
        )
    if not has_chinese_triggers:
        gaps.append(
            "No explicit Chinese trigger keywords listed "
            "(e.g., 'Also triggers on Chinese: 优化, 重构...')"
        )

    return {
        "has_chinese": has_chinese,
        "chinese_ratio": round(chinese_ratio, 4),
        "has_chinese_triggers": has_chinese_triggers,
        "gaps": gaps,
    }


def analyze_description_precision(description):
    """Analyze whether the description is precise enough for reliable triggering."""
    if not description:
        return {"precision_score": 0, "issues": ["Empty description"]}

    issues = []
    score = 1.0

    if len(description) > 300:
        issues.append("Description is verbose (>300 chars) — may cause imprecise triggering")
        score -= 0.15
    elif len(description) < 40:
        issues.append("Description is too short (<40 chars) — may miss relevant triggers")
        score -= 0.1

    action_pattern = (
        r"\b(create|build|write|edit|modify|fix|debug|test|review|"
        r"refactor|optimize|generate|convert|transform|search|find|"
        r"analyze|validate|verify|plan|design|implement|merge|migrate|"
        r"extract|parse|render|display|export|import|sync|manage|tell|"
        r"give|help|break|turn|cover|audit|detect|flag|check|scan)\b"
    )
    has_action = re.search(action_pattern, description, re.IGNORECASE)
    if not has_action:
        issues.append("No action verb found — hard for Claude to determine when this skill applies")
        score -= 0.2

    has_examples = re.search(
        r"(?:use\s+when|triggers?\s+on|examples?:|for\s+example|"
        r"such\s+as|like\s+|when\s+user|whenever)",
        description, re.IGNORECASE
    )
    if not has_examples:
        issues.append(
            "No specific trigger scenarios listed — may under-trigger or over-trigger"
        )
        score -= 0.15

    # Check for "Also triggers on Chinese:" pattern
    if not re.search(r"also\s+triggers?\s+on\s+chinese", description, re.IGNORECASE):
        issues.append(
            "No 'Also triggers on Chinese:' line — Chinese-speaking users may not trigger naturally"
        )
        score -= 0.10

    # Check for concrete outcome description
    if not re.search(
        r"(?:generates?|produces?|creates?|outputs?|returns?|saves?|writes?)",
        description, re.IGNORECASE
    ):
        issues.append(
            "No concrete output description — Claude may not know what the skill produces"
        )
        score -= 0.10

    vague_pattern = r"\b(etc|and so on|things|stuff|various|multiple|different|certain|some)\b"
    if re.search(vague_pattern, description, re.IGNORECASE):
        issues.append("Contains vague language (e.g., 'etc', 'various', 'things')")
        score -= 0.1

    return {"precision_score": round(max(0, score), 2), "issues": issues}


def check_bundled_resources(skill_dir):
    """Check for bundled resources (scripts, references, assets) usage."""
    results = {"has_scripts": False, "has_references": False, "has_assets": False,
               "scripts_count": 0, "references_count": 0}
    scripts_dir = skill_dir / "scripts"
    refs_dir = skill_dir / "references"
    assets_dir = skill_dir / "assets"

    if scripts_dir.exists():
        py_files = list(scripts_dir.glob("*.py"))
        sh_files = list(scripts_dir.glob("*.sh"))
        results["scripts_count"] = len(py_files) + len(sh_files)
        results["has_scripts"] = results["scripts_count"] > 0

    if refs_dir.exists():
        md_files = list(refs_dir.glob("*.md"))
        results["references_count"] = len(md_files)
        results["has_references"] = results["references_count"] > 0

    if assets_dir.exists():
        results["has_assets"] = True

    return results


def main():
    if not SKILLS_DIR.exists():
        print(json.dumps({"error": f"Skills directory not found: {SKILLS_DIR}"}))
        return

    skills = []
    for item in sorted(SKILLS_DIR.iterdir()):
        if item.is_dir() or item.is_symlink():
            skill_dir = item.resolve() if item.is_symlink() else item
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                fm, body = read_frontmatter(skill_file)
                name = fm.get("name", item.name)
                desc = fm.get("description", "")

                if not desc:
                    with open(skill_file, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    desc_match = re.search(r"description:\s*(.+)", content[:500])
                    if desc_match:
                        desc = desc_match.group(1).strip().strip('"').strip("'")

                concepts = extract_concepts(desc)
                body_concepts = extract_concepts(body[:1000]) if body else {
                    "all": set(), "actions": set(), "domains": set(),
                    "chinese": set(), "bigrams": set(), "normalized": set(),
                    "trigger": set(),
                }
                chinese_analysis = analyze_chinese_support(desc)
                precision = analyze_description_precision(desc)
                resources = check_bundled_resources(skill_dir)

                skills.append({
                    "name": name,
                    "path": str(skill_file),
                    "source_path": str(item),
                    "is_symlink": item.is_symlink(),
                    "description": desc,
                    "description_length": len(desc),
                    "_concepts_raw": concepts,
                    "_body_concepts_raw": body_concepts,
                    "chinese_analysis": chinese_analysis,
                    "precision": precision,
                    "resources": resources,
                })

    # Pairwise comparison
    comparisons = []
    for i in range(len(skills)):
        for j in range(i + 1, len(skills)):
            sim = combined_similarity(
                skills[i]["_concepts_raw"], skills[j]["_concepts_raw"],
                skills[i]["_body_concepts_raw"], skills[j]["_body_concepts_raw"],
                skills[i]["name"], skills[j]["name"],
            )
            trigger_sim = jaccard_similarity(
                skills[i]["_concepts_raw"]["trigger"],
                skills[j]["_concepts_raw"]["trigger"],
            )
            comparisons.append({
                "skill_a": skills[i]["name"],
                "skill_b": skills[j]["name"],
                "similarity": round(sim, 4),
                "is_conflict": sim >= 0.50,
                "is_duplicate_candidate": sim >= 0.65,
                "is_trigger_overlap": trigger_sim >= 0.40,
                "trigger_similarity": round(trigger_sim, 4),
                "common_actions": sorted(
                    skills[i]["_concepts_raw"]["actions"] & skills[j]["_concepts_raw"]["actions"]
                ),
                "common_domains": sorted(
                    skills[i]["_concepts_raw"]["domains"] & skills[j]["_concepts_raw"]["domains"]
                ),
                "common_chinese": sorted(
                    skills[i]["_concepts_raw"]["chinese"] & skills[j]["_concepts_raw"]["chinese"]
                ),
            })

    # Convert raw concepts to serializable
    for s in skills:
        s["concepts"] = {
            "all": sorted(s["_concepts_raw"]["all"]),
            "actions": sorted(s["_concepts_raw"]["actions"]),
            "domains": sorted(s["_concepts_raw"]["domains"]),
            "chinese": sorted(s["_concepts_raw"]["chinese"]),
            "normalized": sorted(s["_concepts_raw"]["normalized"]),
            "trigger": sorted(s["_concepts_raw"]["trigger"]),
        }
        del s["_concepts_raw"]
        del s["_body_concepts_raw"]

    duplicates = sorted(
        [c for c in comparisons if c["is_duplicate_candidate"]],
        key=lambda x: -x["similarity"],
    )
    conflicts = sorted(
        [c for c in comparisons if c["is_conflict"] and not c["is_duplicate_candidate"]],
        key=lambda x: -x["similarity"],
    )
    minor_overlaps = sorted(
        [c for c in comparisons if not c["is_conflict"] and c["similarity"] >= 0.25],
        key=lambda x: -x["similarity"],
    )
    trigger_overlaps = sorted(
        [c for c in comparisons if c["is_trigger_overlap"] and not c["is_conflict"]],
        key=lambda x: -x["trigger_similarity"],
    )

    chinese_issues = [s for s in skills if not s["chinese_analysis"]["has_chinese"]]
    precision_issues = [s for s in skills if s["precision"]["precision_score"] < 0.70]

    report = {
        "summary": {
            "total_skills": len(skills),
            "duplicate_pairs": len(duplicates),
            "conflict_pairs": len(conflicts),
            "trigger_overlap_pairs": len(trigger_overlaps),
            "minor_overlap_pairs": len(minor_overlaps),
            "skills_without_chinese": len(chinese_issues),
            "precision_concerns": len(precision_issues),
        },
        "skills": skills,
        "duplicates": duplicates,
        "conflicts": conflicts,
        "trigger_overlaps": trigger_overlaps,
        "minor_overlaps": minor_overlaps,
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
