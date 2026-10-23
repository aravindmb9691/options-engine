These three files could not be written to their final locations remotely. Move them once, then delete this folder:

```bash
mkdir -p .claude .github/workflows
mv _setup/claude-settings.json .claude/settings.json
mv _setup/pre-commit-config.yaml .pre-commit-config.yaml
mv _setup/ci.yml .github/workflows/ci.yml
rm -r _setup
```
