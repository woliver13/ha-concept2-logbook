# Loop instructions
1. Pick an open issue that is NOT: hitl-only, blocked by another open issue,
   already has an open PR/branch, or is a large multi-session feature.
   If nothing qualifies, stop and report that instead of picking anyway.
2. Create a branch off develop named `<issue#>-<short-slug>`.
3. Address the issue. Define acceptance criteria in the PR description
   (not the GitHub issue body) using `afk` for items you completed and
   `hitl` for items that need a human on the real HA instance/device.
4. Run the test suite; all tests must pass before committing.
5. Commit, push the branch, and open a PR back to develop.
   Use `Refs #N` if any hitl criteria remain open, `Closes #N` only if
   every criterion is met.
6. Notify me with the PR link and a list of any hitl criteria left open.