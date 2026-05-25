# CI Supply-Chain Hardening

This public demo workflow is pinned for defensive integrity pass18:

- `actions/checkout` is pinned to commit `34e114876b0b11c390a56381ad16ebd13914f8d5`, the v4 release tag commit observed during pass18.
- `actions/setup-python` is pinned to commit `a26af69be951a213d495a4c3e4e4022e16d87065`, the v5 release tag commit observed during pass18.
- `actions/setup-node` is pinned to commit `49933ea5288caeca8642d1e84afbd3f7d6820020`, the v4 release tag commit observed during pass18.
- Python installs use `requirements.lock.txt` as a constraints file.
- TypeScript is pinned to `5.8.3` and reflected in `package-lock.json`.

This remains a public demo workflow, not a production runtime deployment workflow.
