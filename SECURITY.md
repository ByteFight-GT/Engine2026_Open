# Security Policy

## Supported Versions

Security fixes are developed only for the currently supported engine release
and the engine version deployed for the current competition, if different.

ByteFight competition engines are not necessarily supported across
competition years. In particular, an engine released for a previous
competition may become unsupported when a new competition engine is
adopted.

Older releases, archived versions, and superseded competition engines are not
supported and will not receive backported patches. When a report affects an
unsupported version, maintainers may provide upgrade guidance, a mitigation,
or a public advisory at their discretion. This does not create a commitment to
maintain or patch that version.

## Reporting a Vulnerability

Please do not report security vulnerabilities through public GitHub issues,
pull requests, discussions, chat rooms, or social media.

Use GitHub's **Report a vulnerability** button in this repository's Security
tab to submit a private vulnerability report. Reports may include a proof of
concept when it is necessary to demonstrate impact. Do not attach production
credentials, personal data, or data obtained from other users; describe the
location and exposure so the maintainers can investigate and rotate it.

If GitHub private vulnerability reporting is unavailable, use the security
contact published by the ByteFight organization and request a private channel.
Do not open a public issue merely to report the vulnerability.

Please include:

- affected engine version, release, commit, or deployment date;
- a clear description of the issue and its security impact;
- reproducible, minimally invasive steps or a proof of concept;
- any prerequisites, configuration assumptions, and suggested mitigation; and
- your preferred attribution name and a private contact method for follow-up.

## Scope and Good-Faith Research

This policy covers the ByteFight 2026 Engine and its official runtime,
sandboxing, packaging, and match-execution components.

Discovering or exploiting a security vulnerability to gain an unfair competitive advantage, access another participant's submission or data, or interfere with competition infrastructure is not permitted, even if the vulnerability is within the scope of this policy

Research must avoid access to, modification of, or disruption to accounts,
submissions, matches, systems, or data that you do not own or are not
explicitly authorized to test. Avoid denial-of-service testing, persistence,
and broad data collection. Stop testing once you have demonstrated impact and
report the issue promptly.

We will not pursue action for good-faith research that follows this policy and
applicable law. This does not authorize testing outside the stated scope or
accessing data belonging to other users.

## Response and Disclosure

The maintainers aim to:

- acknowledge a report within 7 calendar days;
- provide an initial triage decision or request for information within 14
  calendar days; and
- provide status updates at least every 14 calendar days while a confirmed
  issue is being remediated.

Please allow time for validation and remediation before public disclosure. For
confirmed vulnerabilities, we will coordinate a disclosure timeline with the
reporter and normally publish after a fix or mitigation is available. If an
issue requires urgent disclosure to protect users, we will explain the reason
and coordinate the safest practical timeline.

## Advisories, CVEs, and Credit

For confirmed vulnerabilities that are appropriate for public disclosure, the
maintainers will create or accept a private GitHub Security Advisory, work with
the reporter during remediation, and request a CVE through the advisory process
when the issue is eligible. The final decision to assign a CVE rests with the
relevant CVE Numbering Authority and GitHub's process.

With the reporter's consent, published advisories will credit the reporter by
their requested name or GitHub account. Credit is not conditioned on submitting
a patch.
