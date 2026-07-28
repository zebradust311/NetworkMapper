# Observation Template

Copy the template below to record a new field observation in [FIELD-OBSERVATIONS.md](./FIELD-OBSERVATIONS.md).

See [README.md](./README.md) for why observations are recorded, and [KNOWLEDGE-LIFECYCLE.md](./KNOWLEDGE-LIFECYCLE.md) for how an observation is expected to mature after it is recorded.

## Instructions

- Record only what was actually observed. Do not infer details you did not directly witness.
- Do not propose a classification rule or benchmark case here — that comes later in the lifecycle, if the observation is corroborated.
- Set **Knowledge Maturity** to `Field Observation` for every new entry. Later stages are updated only as the observation actually progresses through [KNOWLEDGE-LIFECYCLE.md](./KNOWLEDGE-LIFECYCLE.md).
- Give the observation the next sequential number in [FIELD-OBSERVATIONS.md](./FIELD-OBSERVATIONS.md).

## Template

```markdown
### Field Observation #NNN

**Vendor:** <manufacturer>

**Product:** <specific product or product line>

**Typical Environment:** <e.g. homelab, small office, enterprise>

**Primary Operational Role:** <the single role this device should be treated as>

**Secondary Roles:**

- <other functions this device commonly performs, if any>

**Observed Frequency:** <Rare | Occasional | Common>

**Typical Deployment Pattern:** <describe how the device is actually configured and used in the field>

**Engineering Guidance:** <how this observation should be interpreted by NetworkMapper's classification and benchmarking work, if at all>

**Knowledge Maturity:** Field Observation

**Confidence:** <Low | Medium | High>
```
