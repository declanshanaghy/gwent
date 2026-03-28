---
name: feedback_srp
description: User expects Single Responsibility Principle — split announcement/message logic into small, focused methods
type: feedback
---

Keep methods small and focused — Single Responsibility Principle. When adding simple/verbose mode branching, each announcement type should be its own method (e.g., `_announce_turn()`, `_announce_pass()`, `_announce_placement()`), not inline if/else blocks inside large methods.

**Why:** User explicitly asked for this when planning the `--simple` TTS mode. Large methods with lots of branching are hard to read and maintain.

**How to apply:** When adding conditional logic to announcements, extract each announcement type into its own method. The caller picks simple vs verbose, each path is a separate clean method.
