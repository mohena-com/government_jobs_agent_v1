# V1.9.29

Verification-to-generation decoupling:

```text
verified facts        -> allowed facts
missing/unreadable    -> fallback / omit
factual contradiction -> block
allowed facts         -> Qwen
Qwen                  -> slide QA
slide QA              -> renderer
```
