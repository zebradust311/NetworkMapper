# NetworkMapper Documentation

This directory contains the technical documentation for NetworkMapper.

## Documents

### System Design

- **ARCHITECTURE.md**  
  High-level architecture narrative, subsystem interactions, discovery pipeline, classification engine, exporters, and project design philosophy.

- **architecture/**  
  Canonical, currently-implemented architecture — [overview.md](architecture/overview.md) (system-wide) and [classification.md](architecture/classification.md) (classification subsystem). Prefer this directory over ARCHITECTURE.md when the two describe the same subsystem differently; see [architecture/README.md](architecture/README.md).

- **ADR.md**  
  Architectural Decision Records — accepted architecture decisions, their rationale, and their consequences.

### Classification

- **classification-rules.md**  
  A single worked example of a classification rule in an older, pre-RuleResult format. Not a current catalog of the project's classification rules — see [architecture/classification.md](architecture/classification.md) for the canonical rule-evaluation architecture.

### Process

- **process/**  
  The Engineering Handbook: sprint lifecycle, engineering principles, role definitions, mandatory stop conditions, validation workflow, and prompt templates.

### Knowledge

- **knowledge/**  
  The Knowledge Framework: how field observations mature into corroborated knowledge, benchmark datasets, and classification changes.

### Reports

- **reports/**  
  Historical investigation and implementation reports — why past engineering decisions were made. Not living documents; see [reports/README.md](reports/README.md).

### Development

- **DEPENDENCIES.md**  
  Third-party libraries, external tools, and their purpose within the project.

### Research & Field Notes

- **field-notes.md**  
  Early, informal real-world observations that predate the Knowledge Framework's canonical format. New observations belong in [knowledge/FIELD-OBSERVATIONS.md](knowledge/FIELD-OBSERVATIONS.md) instead.

---

## Recommended Reading Order

For new contributors:

1. `README.md` (repository root)
2. `ROADMAP.md` (repository root)
3. `ENGINEERING.md` (repository root)
4. `architecture/overview.md` and `architecture/classification.md`
5. `ADR.md`
6. `process/engineering-handbook.md`
7. `knowledge/README.md`
8. `DEPENDENCIES.md`

`ARCHITECTURE.md`, `classification-rules.md`, and `field-notes.md` are earlier-generation documents kept for historical narrative; the numbered list above is the current, maintained path through the documentation.

---

## Documentation Philosophy

Documentation is intended to answer different questions:

| Question | Document |
|----------|----------|
| What is NetworkMapper? | README.md |
| Where is the project going? | ROADMAP.md |
| What engineering principles govern the project? | ENGINEERING.md |
| How does it work, currently? | architecture/overview.md, architecture/classification.md |
| Why was an architectural decision made? | ADR.md |
| How does an engineering sprint actually run? | process/ |
| Why does a device classify this way? | architecture/classification.md (mechanism), docs/ADR.md (decisions) |
| How does field experience become a classification rule? | knowledge/ |
| Why was a past change made the way it was? | reports/ |
| What external components are used? | DEPENDENCIES.md |