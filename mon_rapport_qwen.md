# Slopwise Semantic Diff Report

## Executive Summary

### Themes Found

- **Authentication and API Refactoring**: 2 functions affected.

| Category | Count |
| :--- | :--- |
| Breaking_change | 1 |
| Security | 1 |

| Risk Level | Count |
| :--- | :--- |
| High | 1 |
| Medium | 1 |

## Detailed Analysis

### Theme: Authentication and API Refactoring

#### `main`

- **Risk**: MEDIUM
- **Category**: Security
- **Summary**: Changed authentication function from 'auth_user' to 'auth_user_v2' with a different configuration/data pointer.
- **Reviewer Notes**: insufficient_context, false_safety_assumption

---

#### `calculate_data`

- **Risk**: HIGH
- **Category**: Breaking_change
- **Summary**: The function signature was changed from accepting two parameters to one, and the internal logic was changed from addition to multiplication. This is a breaking API change that requires caller updates.
- **Reviewer Notes**: Incorrect Security Categorization, Missing Breaking Change Analysis, Insufficient Risk Assessment for ABI/API Compatibility

---

