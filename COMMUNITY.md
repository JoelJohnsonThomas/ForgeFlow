# ForgeFlow Community

ForgeFlow is built in the open. There are several ways to connect with
maintainers and other operators.

## Where to ask which question

| Question type | Channel |
|---------------|---------|
| Bug — reproducible, broken behavior | [Issues](https://github.com/JoelJohnsonThomas/ForgeFlow/issues/new?template=bug_report.md) |
| Feature request — concrete proposal with a use case | [Issues](https://github.com/JoelJohnsonThomas/ForgeFlow/issues/new?template=feature_request.md) |
| Idea / "would this fit?" / architecture discussion | [Discussions → Ideas](https://github.com/JoelJohnsonThomas/ForgeFlow/discussions/categories/ideas) |
| Help running it / config / deployment | [Discussions → Q&A](https://github.com/JoelJohnsonThomas/ForgeFlow/discussions/categories/q-a) |
| Show what you built | [Discussions → Show and tell](https://github.com/JoelJohnsonThomas/ForgeFlow/discussions/categories/show-and-tell) |
| Real-time chat | [Discord — invite via README](README.md#community) |
| Security vulnerability | Private email to the maintainer (see [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)) |

## GitHub Discussions

Enabled at the repo level. The four default categories:

1. **Announcements** (maintainer-only) — releases, breaking changes, roadmap shifts.
2. **Q&A** — getting-help questions. Mark an answer when something resolves; that makes the discussion searchable.
3. **Ideas** — half-formed proposals before they become Issues.
4. **Show and tell** — community workflows, connectors, templates.

To enable Discussions on a fresh fork: **Settings → General → Features →
Discussions**.

## Discord

A real-time chat space is helpful once the project has more than ~10
active contributors. To bootstrap:

1. Create a server with channels: `#general`, `#help`, `#contrib`,
   `#templates`, `#connectors`, `#showcase`.
2. Add the invite URL to the [README community section](README.md#community).
3. Bridge announcements with the GitHub Discussions "Announcements"
   category via a small webhook so neither channel goes stale.

Until enough demand exists, GitHub Discussions is sufficient — adding a
Discord prematurely splits the audience.

## Contributing code

See [CONTRIBUTING.md](CONTRIBUTING.md) for PR workflow, code style, and
test requirements. New connectors, workflow templates, and integration
fixes are especially welcome — pick anything in
[ROADMAP.md](ROADMAP.md) flagged "pending" and open an issue first to
discuss approach.

## Code of conduct

This project follows the [Contributor Covenant 2.1](CODE_OF_CONDUCT.md).
Be kind. Disagreement is fine; disrespect is not.

## Maintainers

Currently solo-maintained. Reach the maintainer via the email address
on the [GitHub profile](https://github.com/JoelJohnsonThomas).

## Anonymous adoption telemetry

ForgeFlow ships an opt-in telemetry emitter
([forgeflow/telemetry/](forgeflow/telemetry/)). It is OFF by default.
When enabled, it sends a small set of non-PII fields (event_name,
workflow_type, version, error_class) to a webhook the operator
configures — see [`.env.example`](.env.example) for the variables.

The community itself doesn't run a telemetry endpoint. The plumbing is
there for operators who want to instrument their own deployments.
