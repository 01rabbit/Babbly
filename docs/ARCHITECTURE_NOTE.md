# Architecture boundary

Babbly Core should remain usable without Azazel. Azazel is an adapter, not a core dependency.

The dependency direction is:

```text
Babbly Core <- Adapter <- External system
```

Never:

```text
Babbly Core -> Azazel-specific implementation
```

This preserves Babbly as a generic offline voice/operator-assistance framework.
