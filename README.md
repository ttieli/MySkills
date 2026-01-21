# MySkills

Custom Claude Code Skills for productivity enhancement.

## Skills

| Skill | Description |
|-------|-------------|
| [form-filling](./form-filling/) | Auto-fill Word/Excel templates while preserving formatting |
| [generate-ralph](./generate-ralph/) | Meta-skill: Generate Ralph Loop development environment |
| [project-organizer](./project-organizer/) | Intelligent project structure organizer with Git backup |

---

## Installation

### Quick Install (All Skills)

```bash
git clone https://github.com/ttieli/MySkills.git
cd MySkills

# Copy all skills to Claude Code skills directory
cp -r form-filling ~/.claude/skills/
cp -r generate-ralph ~/.claude/skills/
cp -r project-organizer ~/.claude/skills/
```

### Install Individual Skill

```bash
# form-filling only
cp -r form-filling ~/.claude/skills/

# generate-ralph only
cp -r generate-ralph ~/.claude/skills/

# project-organizer only
cp -r project-organizer ~/.claude/skills/
```

---

## Skills Detail

### 1. form-filling

Auto-fill Word/Excel templates with data while preserving original formatting (fonts, borders, alignment).

**Use Cases:**
- Batch fill registration forms
- Generate documents from CSV/JSON data
- Fill templates without breaking layout

**Dependencies:**
```bash
pip install python-docx openpyxl
```

**Trigger:** `/form-filling` or describe form-filling tasks

---

### 2. generate-ralph

Meta-skill that creates complete Ralph Loop development environments. "Agent that creates Agents."

**Output Files:**
- `task_plan.md` - Phase planning
- `findings.md` - Research notes
- `progress.md` - Execution log
- `ralph_loop.sh` - Auto-loop script

**Trigger:** `/generate-ralph` or describe complex coding tasks

---

### 3. project-organizer

Intelligent project structure organizer with three-layer safety:

1. **Git Backup** - Auto backup before any changes
2. **Protected Paths** - Core directories are never touched
3. **User Confirmation** - All deletions require approval

**Features:**
- Detect scattered files and suggest proper locations
- Find and clean macOS duplicate files (`file 2.py`)
- Recommend standard project structures
- One-click restore if unhappy

**Scripts:**
- `scripts/git_backup.py` - Backup/restore management
- `scripts/root_inventory.py` - Directory analysis

**Trigger:** `/project-organizer` or say "organize this project"

---

## Related Projects

- [docxjs-cli](https://github.com/ttieli/docxjs-cli) - Markdown to Word/PDF converter
- [web-fetcher](https://github.com/ttieli/web-fetcher) - Smart web scraper to Markdown
- [mineru-cloud](https://github.com/ttieli/mineru-cloud) - MinerU OCR cloud wrapper

## License

MIT
