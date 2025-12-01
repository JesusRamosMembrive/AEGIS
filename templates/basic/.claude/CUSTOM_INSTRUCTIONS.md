## 🎯 PROJECT CONTEXT

Before ANY work, read in this order:
1. .claude/00-project-brief.md - Project scope and constraints
2. .claude/01-current-phase.md - Current state and progress
3. .claude/02-stage[X]-rules.md - Rules for current stage

## 📝 SESSION WORKFLOW

⚠️ MANDATORY: At the START of EVERY session, BEFORE responding to user:

1. **ALWAYS read these files first** (use Read tool in parallel):
   - .claude/00-project-brief.md - Project scope and constraints
   - .claude/01-current-phase.md - Current state and next steps (COMPACT)
   - .claude/02-stage[X]-rules.md - Rules for current stage

2. **ALWAYS confirm to user** you've read the context:
   - State current phase/stage
   - Summarize what was last done
   - Ask for clarification if anything is unclear

3. **ONLY THEN** respond to the user's request

**This applies EVEN IF the user's first message is a simple question.**
Do NOT skip this protocol to "be helpful faster" - reading context IS being helpful.

**Need deep context?** Read `.claude/01-session-history.md` for full session details.

At END of session:
- Update .claude/01-current-phase.md with progress
- **CRITICAL**: Keep 01-current-phase.md under 150 lines

## 🔄 FEATURE DEVELOPMENT WORKFLOW

For ANY new feature, follow this workflow with explicit gates:

```
1. CHECK/CREATE → 2. PLAN → 3. APPROVE → 4. IMPLEMENT → 5. TEST → 6. VALIDATE → 7. APPROVE
```

### Phase 1: PLANNING (Research & Design)
**Agents**: @architect, @stage-keeper
**Output**: `docs/{feature}/architecture.md`

**Steps**:
1. Check if `docs/{feature}/` exists
   - If exists: **READ existing documentation first**
   - If not: Create the directory
2. @architect analyzes requirements and constraints
3. @architect designs stage-appropriate architecture
4. @architect defines testing strategy (unit + integration)
5. @stage-keeper validates stage-appropriateness
6. Document in `docs/{feature}/architecture.md`

**Architecture must include**:
- Context & Requirements
- Stage Assessment
- Component Structure
- Technology Stack with trade-offs
- Build Order with dependencies
- **Testing Strategy** (what to test, how)
- Evolution Triggers

**🚦 GATE**: Present plan to user. **WAIT FOR APPROVAL** before Phase 2.

### Phase 2: IMPLEMENTATION (Building & Testing)
**Agent**: @implementer
**Output**: Code files + `docs/{feature}/implementation.md`

**Steps**:
1. **READ `architecture.md` FIRST** (mandatory)
2. Implement components in specified build order
3. Write unit tests for each component
4. **Run unit tests - MUST PASS**
5. Write integration tests (if Stage 2+)
6. **Run integration tests - MUST PASS**
7. Track progress in `docs/{feature}/implementation.md`
8. Document any deviations or blockers

**Testing Requirements by Stage**:
| Stage | Unit Tests | Integration Tests |
|-------|------------|-------------------|
| 1 (PoC) | Optional | Not required |
| 2 (Prototype) | Basic coverage | Optional |
| 3 (Production) | Full coverage | Required |
| 4 (Scale) | Full + edge cases | Full + performance |

**Blockers trigger**:
- Plan is unclear or incomplete
- Technical constraints make plan infeasible
- Need to deviate significantly from plan
→ **STOP**, document in `blockers.md`, request architect clarification

**🚦 GATE**: All tests must **PASS** before Phase 3.

### Phase 3: VALIDATION (Quality Assurance)
**Agents**: @code-reviewer, @stage-keeper
**Output**: `docs/{feature}/qa-report.md`

**Steps**:
1. @code-reviewer reads `architecture.md` and `implementation.md`
2. Validate implementation matches plan
3. Verify all tests pass (unit + integration)
4. Check security, correctness, performance
5. @stage-keeper verifies stage-appropriate complexity
6. Document findings in `docs/{feature}/qa-report.md`

**Recommendation options**:
- ✅ **APPROVED**: Feature complete
- ⚠️ **MINOR FIXES**: Small changes needed
- ❌ **REQUEST CHANGES**: Return to Phase 2

**🚦 GATE**: Present QA report to user. **WAIT FOR FINAL APPROVAL**.

## 📁 DOCUMENTATION STRUCTURE

For each feature, maintain:
```
docs/{feature-name}/
├── architecture.md      # Phase 1: Plan
├── implementation.md    # Phase 2: Progress
├── qa-report.md        # Phase 3: Validation
└── blockers.md         # Issues (optional)
```

## 👥 AGENT ROLES

| Agent | Phase | Role | Can Write Code? |
|-------|-------|------|-----------------|
| @architect | 1 | Design architecture, create plan | ❌ No |
| @stage-keeper | 1, 2, 3 | Validate stage-appropriateness | ❌ No |
| @implementer | 2 | Execute plan, write code & tests | ✅ Yes |
| @code-reviewer | 3 | Validate quality, plan adherence | ❌ No |
| @orchestrator | All | Coordinate phases, manage transitions | ✅ Limited |

## ⚠️ CRITICAL RULES

### Workflow Compliance
- **NEVER skip phases** (must go 1 → 2 → 3)
- **NEVER implement without approved plan**
- **NEVER skip tests** (except Stage 1 PoC)
- **NEVER proceed without user approval at gates**
- **ALWAYS read existing docs before changes**

### Agent-Specific Rules
- **@architect, @stage-keeper**: NEVER write implementation code
- **@implementer**: ALWAYS read architecture.md FIRST
- **@code-reviewer**: NEVER redesign architecture
- **All agents**: Output to correct `docs/{feature}/` locations

### Session Management
- Never implement without reading current context
- Never skip updating progress at end of session
- Never assume you remember from previous sessions
- Always check current stage rules before proposing solutions

### Stage Awareness
- **Stage 1 (PoC)**: Speed and simplicity, minimal tests
- **Stage 2 (Prototype)**: Basic structure, basic tests
- **Stage 3 (Production)**: Full tests, error handling
- **Stage 4 (Scale)**: Performance tests, edge cases

## 🚫 NEVER

### Phase 1 (Planning)
- Write implementation code
- Skip stage-keeper validation
- Create incomplete architecture plans
- Proceed to Phase 2 without user approval

### Phase 2 (Implementation)
- Start coding without reading architecture.md
- Make architectural decisions not in the plan
- Skip writing tests (Stage 2+)
- Proceed to Phase 3 with failing tests
- Ignore blockers (document and escalate)

### Phase 3 (Validation)
- Redesign the architecture
- Approve code that deviates from plan without documented reason
- Skip reading architecture.md before review
- Ignore stage compliance violations

## 📚 PROJECT RESOURCES

Available in `docs/` folder:
- **README.md** - Workflow documentation and templates
- **PROMPT_LIBRARY.md** - Templates for common situations
- **QUICK_START.md** - Workflow guide
- **STAGES_COMPARISON.md** - Quick reference table
- **CLAUDE_CODE_REFERENCE.md** - Claude Code tips, slash commands, MCP, subagents

## 💡 REMEMBER

- **Check → Plan → Approve → Implement → Test → Validate → Approve**
- Tests are mandatory (Stage 2+)
- User approval required at gates
- Simplicity > Completeness
- When in doubt, check the stage rules

---

*To update these instructions, modify templates/basic/.claude/CUSTOM_INSTRUCTIONS.md*
