# Security Policy

## Supported versions

Only the latest release of `ecactus-ecos-py` receives security fixes.

## Reporting a vulnerability

Please do not open a public issue for a security problem. Report it privately
through GitHub instead: **Security** tab → **Report a vulnerability**, or
<https://github.com/gmasse/ecactus-ecos-py/security/advisories/new>.

Include what you can of:

- the affected version and the client used (`Ecos` or `AsyncEcos`);
- what an attacker could do, and under which conditions;
- steps or a minimal script to reproduce it, using made-up credentials.

This project is maintained on a best-effort basis by a single volunteer. You
will get an answer in the advisory thread, and the fix will be credited to you
in the release notes unless you ask otherwise.

## Scope

This policy covers the code in this repository. A vulnerability in the ECOS
platform or its API belongs to WEIHENG Group, which runs it: this project is
not affiliated with them and cannot fix it.

## Sharing logs

Debug output from this library can contain access tokens and personal data
(email address, phone number). Remove them before attaching logs to an issue.
A published token may stay valid until it expires: treat it as compromised,
change your ECOS password and log in again.
