# AI-Powered Course Creation — Technical Design

> **IMPORTANT NOTICE:** Per the take-home assignment instructions:
> *"Do not use AI to write this design/documentation. The purpose of this section is to understand your own system-design thinking. Using AI-generated documentation containing terminology or architecture concepts that you cannot explain yourself may result in disqualification."*
>
> Therefore, this file is intentionally reserved for the human author to write in their own words.

---

## Author Placeholder

Please complete this technical design covering:

### 1. Information Sent to the AI
- Inputs provided by Tenant Admin (e.g. target role/learner profile, current proficiency level, learning goals, available hours/week, total course duration).
- Context formatting and prompt structure.

### 2. Response Structure and Validation
- Schema / format expected from the AI (e.g. structured JSON schema with modules, lessons, order, estimated study time, objectives).
- Validation mechanisms (parsing, schema validation, fallback strategies if output fails schema).

### 3. Personalization Strategy
- Pacing adaptation based on weekly hours and total weeks.
- Content tailoring for beginner vs advanced prerequisite knowledge.

### 4. Failure Modes and Mitigations
- Hallucinations & factual inaccuracies in lesson content.
- Inconsistent or malformed output schemas.
- Token limits and cost control.
- Privacy & data leakage across institutes/tenants.
- Prompt injection risks (sanitization of user-provided goals and descriptions).
