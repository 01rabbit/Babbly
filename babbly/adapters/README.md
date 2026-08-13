# Babbly Adapters

Adapters translate external system state into Babbly's generic Situation Model.

The default contract is read-only/advisory:

- observations may describe state, alerts, and evidence
- recommendations may suggest operator actions
- recommendations are advisory-only by default
- adapter failure must not terminate Babbly
- adapters do not receive arbitrary shell-command authority

Write-capable integrations, if added later, must use a separate explicit request/approval contract rather than extending the read-only adapter interface.
