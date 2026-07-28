# Field Observations

This document contains recorded field observations using NetworkMapper's canonical observation format.

It complements [README.md](./README.md), which explains why observations are recorded, and [KNOWLEDGE-LIFECYCLE.md](./KNOWLEDGE-LIFECYCLE.md), which explains how an observation matures over time.

New observations should be added using [OBSERVATION-TEMPLATE.md](./OBSERVATION-TEMPLATE.md) and appended after the examples below.

## Canonical Observation Format

Every observation records the following fields:

- **Vendor** — the manufacturer of the observed device.
- **Product** — the specific product or product line observed.
- **Typical Environment** — the kind of environment the device is typically observed in (for example, small office, enterprise, homelab).
- **Primary Operational Role** — the single role NetworkMapper should treat as the device's primary function.
- **Secondary Roles** — other functions the device commonly performs, which are not its primary classification.
- **Observed Frequency** — how often this pattern has been observed (for example, Rare, Occasional, Common).
- **Typical Deployment Pattern** — a description of how the device is actually configured and used in the field.
- **Engineering Guidance** — how this observation should be interpreted by NetworkMapper's classification and benchmarking work.
- **Knowledge Maturity** — the observation's current stage in [KNOWLEDGE-LIFECYCLE.md](./KNOWLEDGE-LIFECYCLE.md).
- **Confidence** — the observer's confidence in the accuracy of the observation (Low, Medium, High).

---

## Worked Examples

The two observations below are worked examples. They establish the canonical format using knowledge already established within this project. They are not a template for new entries — use [OBSERVATION-TEMPLATE.md](./OBSERVATION-TEMPLATE.md) for that.

### Field Observation #001

**Vendor:** VMware

**Product:** ESXi (bare-metal hypervisor)

**Typical Environment:** Small office through enterprise

**Primary Operational Role:** Hypervisor / Virtualization Host

**Secondary Roles:** None observed — ESXi hosts are typically dedicated to virtualization.

**Observed Frequency:** Common

**Typical Deployment Pattern:** Physical virtualization hosts are typically given an intentional hostname by MSP or internal IT staff, rather than left at a factory default. These hostnames frequently contain identifying keywords such as `esx`, `esxi`, `vcenter`, or `vmhost`. A meaningful hostname is a strong indicator of an intentionally managed virtualization host. The absence of a hostname should not be interpreted as evidence that a device is a workstation.

**Engineering Guidance:** This observation is already reflected in production classification. `HypervisorHostnameRule` matches these hostname keywords as evidence of the `HYPERVISOR` device type, consistent with the pre-existing operational notes in [docs/field-notes.md](../field-notes.md).

**Knowledge Maturity:** Classification — already encoded as a classification rule and covered by regression tests.

**Confidence:** High

---

### Field Observation #002

**Vendor:** Ubiquiti

**Product:** UniFi Dream Router (UDR)

**Typical Environment:** Small office

**Primary Operational Role:** Firewall / Gateway

**Secondary Roles:**

- Wireless Access Point
- UniFi Network Controller

**Observed Frequency:** Common

**Typical Deployment Pattern:** In small office environments, the UDR commonly serves as the site's primary firewall and gateway while also providing Wi-Fi coverage. Some deployments include one or two additional UniFi access points to extend wireless coverage, but in many installations the UDR is the only wireless access point.

**Engineering Guidance:** NetworkMapper classifies devices by their primary operational role rather than by every capability they provide. Although the UDR integrates firewall, gateway, wireless access point, and controller functionality, its primary operational role is Firewall / Gateway.

**Knowledge Maturity:** Field Observation — this is the project's first documented UDR field observation. It has not yet been corroborated into Knowledge, benchmarked, or reflected in a classification rule.

**Confidence:** High

---

## Future Observations

New observations belong below this line. Each new entry should:

- Use the format in [OBSERVATION-TEMPLATE.md](./OBSERVATION-TEMPLATE.md).
- Be numbered sequentially, continuing from the highest existing observation number.
- Record only what was actually observed — not a proposed classification rule or benchmark case.

No future observations have been recorded yet.
