# Situation/Adapter PR scope

This change adds only read-only/advisory foundations:

- generic situation data model
- aggregation engine
- adapter abstraction
- initial read-only Azazel payload translator
- failure isolation tests

It does not add live Azazel network access, write actions, autonomous response, or arbitrary command authority.
