> This file predates NetworkMapper's `RuleResult`/evidence-based
> classification architecture and documents only one rule in an older
> pseudo-code format. It is not a current catalog of the project's
> classification rules. For the canonical, current classification
> architecture, see [architecture/classification.md](architecture/classification.md);
> for individual rule implementations, see `networkmapper/classification/rules/`.
> Rebuilding this file as an accurate, complete rule catalog is recommended
> as a dedicated follow-up sprint (see ARCH-011's sprint report).

## Rule 12

If:

Vendor == Ubiquiti

AND

Hostname starts with "UAP"

Then:

DeviceType = ACCESS_POINT

Confidence = High

Reason:

Ubiquiti access points ship with this naming convention.