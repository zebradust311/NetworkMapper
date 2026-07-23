# NetworkMapper Documentation

This directory contains the technical documentation for NetworkMapper.

## Documents

### System Design

- **ARCHITECTURE.md**  
  High-level architecture, subsystem interactions, discovery pipeline, classification engine, exporters, and project design philosophy.

### Classification

- **classification-rules.md**  
  Catalog of device classification rules, matching heuristics, rule precedence, and evidence collection.

### Development

- **DEPENDENCIES.md**  
  Third-party libraries, external tools, and their purpose within the project.

### Research & Field Notes

- **field-notes.md**  
  Real-world observations, edge cases, testing notes, vendor behaviors, and implementation discoveries.

---

## Recommended Reading Order

For new contributors:

1. `README.md` (repository root)
2. `ROADMAP.md` (repository root)
3. `ARCHITECTURE.md`
4. `classification-rules.md`
5. `DEPENDENCIES.md`
6. `field-notes.md`

---

## Documentation Philosophy

Documentation is intended to answer different questions:

| Question | Document |
|----------|----------|
| What is NetworkMapper? | README.md |
| Where is the project going? | ROADMAP.md |
| How does it work? | ARCHITECTURE.md |
| Why does a device classify this way? | classification-rules.md |
| What external components are used? | DEPENDENCIES.md |
| What have we learned during development? | field-notes.md |