# Field Notes

This document captures real-world observations made during customer engagements.

These notes are not implementation requirements.

A note should only become a classification rule after it has been observed consistently across multiple customer environments.

The purpose of this document is to preserve operational knowledge that may later improve NetworkMapper's intelligence.

---

## Hypervisors

Observation

Physical virtualization hosts are typically named by the MSP or internal IT staff.

Notes

- A meaningful hostname is a strong indicator of an intentionally managed server.
- Lack of a hostname should not imply workstation.

---

## Ubiquiti Access Points

Observation

Many Ubiquiti access points retain their factory hostname, which often includes the hardware model.

Examples

- UAP-AC-LR
- U6-Pro
- U7-Pro

Notes

Model names may be more valuable than the hostname itself for identifying device type.

---

## Printers

Observation

Businesses frequently rename printers within Windows print queues, but rarely change the printer's actual network hostname.

Notes

Factory hostnames often contain useful identification information and should not be discarded.

### Ubiquiti Access Points

Factory default hostnames typically begin with:

- UAP
- U6
- U7

However, in well-managed MSP environments, access points are commonly renamed based on their physical location.

Examples:

- Lobby AP
- Conference Room AP
- Warehouse AP

Hostname alone should not be relied upon for identifying deployed Ubiquiti access points.