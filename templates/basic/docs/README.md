# Feature Documentation Directory

This directory stores documentation for features developed using the **Stage-Aware Development Workflow**.

> **Note**: This documentation structure is shared between all AI agents (Claude, Gemini, Codex).
> Claude uses specialized agents (@architect, @implementer, etc.) while Gemini and Codex execute the same workflow in a unified flow.

## Directory Structure

```
docs/
├── README.md (this file)
├── {feature-name}/
│   ├── architecture.md      # Phase 1: Architectural plan
│   ├── implementation.md    # Phase 2: Progress tracking
│   ├── qa-report.md        # Phase 3: QA validation
│   └── blockers.md         # Issues preventing progress (optional)
└── ...
```

## The Development Workflow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     STAGE-AWARE DEVELOPMENT WORKFLOW                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. CHECK/CREATE     2. PLANNING        3. APPROVAL                     │
│  ┌──────────────┐    ┌──────────────┐   ┌──────────────┐                │
│  │ docs/{feat}/ │───▶│ architecture │──▶│ User Review  │                │
│  │ exists?      │    │ .md          │   │ & Approval   │                │
│  └──────────────┘    └──────────────┘   └──────┬───────┘                │
│        │                                        │                        │
│        │ If exists: READ                        │ Approved?              │
│        │ If not: CREATE                         │                        │
│        ▼                                        ▼                        │
│  ┌──────────────┐                        ┌──────────────┐                │
│  │ Read existing│                        │     NO       │──▶ Revise     │
│  │ docs first   │                        └──────────────┘    Plan       │
│  └──────────────┘                               │                        │
│                                                 │ YES                    │
│                                                 ▼                        │
│  4. IMPLEMENTATION   5. UNIT TESTS      6. INTEGRATION TESTS            │
│  ┌──────────────┐    ┌──────────────┐   ┌──────────────┐                │
│  │ Build code   │───▶│ Write & run  │──▶│ Write & run  │                │
│  │ component by │    │ unit tests   │   │ integration  │                │
│  │ component    │    │ MUST PASS    │   │ tests        │                │
│  └──────────────┘    └──────────────┘   └──────┬───────┘                │
│                                                 │                        │
│                                                 │ All pass?              │
│                                                 ▼                        │
│  7. VALIDATION       8. FINAL APPROVAL                                  │
│  ┌──────────────┐    ┌──────────────┐                                   │
│  │ QA Review    │───▶│ User Review  │──▶ FEATURE COMPLETE              │
│  │ qa-report.md │    │ & Approval   │                                   │
│  └──────────────┘    └──────────────┘                                   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Workflow Phases

### Phase 1: PLANNING
**Output**: `docs/{feature}/architecture.md`

**Steps**:
1. Check if `docs/{feature}/` exists
   - If exists: READ existing documentation first
   - If not: CREATE the directory
2. Analyze requirements and constraints
3. Design stage-appropriate architecture
4. Select technology stack with rationale
5. Define testing strategy (unit + integration)
6. Document in `architecture.md`

**architecture.md must include**:
- Context & Requirements
- Stage Assessment
- Component Structure
- Technology Stack with trade-offs
- Build Order with dependencies
- **Testing Strategy** (what to test, how)
- Evolution Triggers

**Gate**: User must APPROVE plan before proceeding to Phase 2

### Phase 2: IMPLEMENTATION
**Output**: Code files + `docs/{feature}/implementation.md`

**Steps**:
1. READ `architecture.md` FIRST (mandatory)
2. Implement components in specified build order
3. Write unit tests for each component
4. **Unit tests MUST PASS** before continuing
5. Write integration tests
6. **Integration tests MUST PASS** before validation
7. Track progress in `implementation.md`
8. Document any deviations or blockers

**Testing Requirements by Stage**:
| Stage | Unit Tests | Integration Tests |
|-------|------------|-------------------|
| 1 (PoC) | Optional | Not required |
| 2 (Prototype) | Basic coverage | Optional |
| 3 (Production) | Full coverage | Required |
| 4 (Scale) | Full + edge cases | Full + performance |

**Gate**: All tests must PASS before Phase 3

### Phase 3: VALIDATION
**Output**: `docs/{feature}/qa-report.md`

**Steps**:
1. Read `architecture.md` and `implementation.md`
2. Validate implementation matches plan
3. Verify all tests pass (unit + integration)
4. Check security, correctness, performance
5. Verify stage-appropriate complexity
6. Document findings in `qa-report.md`
7. Recommendation: Approve / Minor Fixes / Request Changes

**Gate**: User must APPROVE before feature is complete

## Document Templates

### architecture.md Template

```markdown
# Architecture: {Feature Name}

**Date**: {YYYY-MM-DD}
**Stage**: {1-4}
**Complexity Level**: {Low/Medium/High}

## Context & Requirements
[Problem statement, user needs, constraints]

## Stage Assessment
**Current Project Stage**: {1-4}
**Allowed Patterns**: [List]
**Testing Requirements**: [Unit: X, Integration: Y]

## Component Structure
[Diagram or description]

## Technology Stack
- **{Component}**: {Technology}
  - Rationale: [Why]
  - Trade-offs: [Pros/Cons]

## Implementation Guidance

### Build Order
1. **{Component A}** - Files, dependencies, success criteria
2. **{Component B}** - [Same]

### Code Patterns to Follow
[Examples]

## Testing Strategy

### Unit Tests
- [ ] {Component A}: [What to test]
- [ ] {Component B}: [What to test]

### Integration Tests
- [ ] {Flow 1}: [End-to-end scenario]
- [ ] {Flow 2}: [End-to-end scenario]

## Evolution Triggers
[When to add complexity]

## Handoff Checklist
- [ ] Components defined
- [ ] Build order specified
- [ ] Technology justified
- [ ] Testing strategy defined
```

### implementation.md Template

```markdown
# Implementation: {Feature Name}

**Date Started**: {YYYY-MM-DD}
**Architecture Plan**: `docs/{feature}/architecture.md`

## Build Order
- [ ] Component A (file: path/to/file.py)
- [ ] Component B - depends on A
- [ ] Unit Tests
- [ ] Integration Tests

## Progress Log

### {Date} - Component A
- Status: ✅ Complete / 🔄 In Progress / ⏳ Pending
- Files: [list]

## Testing Status

### Unit Tests
- [ ] Component A tests: ⏳ Pending / ✅ Passing / ❌ Failing
- [ ] Component B tests: ⏳ Pending / ✅ Passing / ❌ Failing

### Integration Tests
- [ ] Flow 1: ⏳ Pending / ✅ Passing / ❌ Failing
- [ ] Flow 2: ⏳ Pending / ✅ Passing / ❌ Failing

**All Tests Passing**: ❌ No / ✅ Yes

## Deviations from Plan
[Any changes to original architecture]

## Blockers
[Issues preventing completion]
```

### qa-report.md Template

```markdown
# QA Report: {Feature Name}

**Date**: {YYYY-MM-DD}
**Architecture Plan**: `docs/{feature}/architecture.md`
**Implementation**: `docs/{feature}/implementation.md`

## 1. Plan Adherence
- [ ] All components implemented
- [ ] Technology stack matches
- [ ] Build order followed
**Score**: ✅ PASS / ⚠️ MINOR / ❌ MAJOR

## 2. Testing Validation
### Unit Tests
- Total: X tests
- Passing: X
- Coverage: X%
**Status**: ✅ PASS / ❌ FAIL

### Integration Tests
- Total: X tests
- Passing: X
**Status**: ✅ PASS / ❌ FAIL

## 3. Security Review
[Critical/High/Medium issues]
**Status**: ✅ SECURE / ⚠️ ISSUES / 🔴 CRITICAL

## 4. Correctness Review
[Bugs found, logic issues]
**Status**: ✅ CORRECT / ⚠️ ISSUES / ❌ BUGS

## 5. Stage Compliance
[Over/under-engineering check]
**Status**: ✅ APPROPRIATE / ⚠️ ISSUES / ❌ VIOLATIONS

## 6. Recommendation
**Status**: ✅ APPROVED | ⚠️ MINOR FIXES | ❌ REQUEST CHANGES

### If not approved:
[Specific actions required]
```

## Agent-Specific Notes

### Claude (with specialized agents)
- **@orchestrator**: Coordinates workflow, manages phase transitions
- **@architect**: Creates `architecture.md` in Phase 1
- **@implementer**: Builds code + tests in Phase 2
- **@code-reviewer**: Creates `qa-report.md` in Phase 3
- **@stage-keeper**: Validates stage-appropriateness

### Gemini & Codex (unified flow)
- Same workflow, executed by a single agent
- Follow the same phases and gates
- Use same documentation structure
- Same testing requirements apply

## Best Practices

### Do:
- ✅ Always check if `docs/{feature}/` exists first
- ✅ Read existing documentation before making changes
- ✅ Get user approval at each gate
- ✅ Write tests BEFORE moving to validation
- ✅ Document all deviations with rationale

### Don't:
- ❌ Skip reading `architecture.md` before implementing
- ❌ Skip tests (except Stage 1 PoC)
- ❌ Proceed without user approval at gates
- ❌ Make undocumented deviations from plan
- ❌ Mix multiple features in one directory

## Naming Conventions

Feature directory names should be:
- **Lowercase with hyphens**: `user-authentication`, `payment-processing`
- **Descriptive**: Clearly indicate what the feature does
- **Concise**: Avoid overly long names
- **Consistent**: Match naming used in code/commits

---

**This documentation structure is shared between Claude, Gemini, and Codex.**
