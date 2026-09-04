# GitHub settings checklist

This checklist is intentionally manual. Local candidate tooling does not call
the GitHub API with write permissions and never changes repository settings.

Before publishing a release, an authenticated repository administrator should
record evidence for each item:

- [ ] branch protection is enabled on the release branch;
- [ ] required status checks and required reviewers match the support matrix;
- [ ] `CODEOWNERS` is active and the listed owners are current;
- [ ] Dependabot security updates and grouped update policy are enabled;
- [ ] secret scanning and push protection are enabled;
- [ ] release permissions use least privilege and immutable workflow actions;
- [ ] the release assets, checksums, SBOM and candidate source SHA agree;
- [ ] the Chroma residual-risk decision in
      `docs/CHROMA-RESIDUAL-DECISION.md` is filled by a human maintainer.

Record the date, administrator identity and links to authenticated settings
pages outside the candidate bundle. An anonymous health check must be reported
as `not verified`, never as success.
