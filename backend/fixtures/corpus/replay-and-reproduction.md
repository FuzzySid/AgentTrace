---
doc_id: replay-and-reproduction
title: Reproducing an agent failure
---
# Reproducing an agent failure

To reproduce a failure, keep the task input, run identifier, prompt version, model tier, capture tier, and tool configuration. Replay the same task with the same corpus revision where possible. Comparing runs is useful only when the important inputs are known.

Do not assume that two runs with the same question are equivalent if their retrieved documents or model routing differ. Record enough metadata to explain those differences without storing content by default.
