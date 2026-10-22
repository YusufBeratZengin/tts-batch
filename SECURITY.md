# Security policy

Security fixes target the latest 0.1.x release. Install engine executables,
optional Python packages and model/voice files only from sources you trust.
Model formats loaded by optional dependencies may carry their own risks.

The renderer passes text through subprocess stdin without a shell. Engine
subprocesses have a 120-second timeout per segment. The core does not send text
to external services. Kokoro is configured for offline Hugging Face/Transformers
operation, but this package is not an operating-system network sandbox. Use an
isolated environment when strict network or resource limits are required.

Output directories and caches contain readable scripts or derived audio. They
are not encrypted. Use dedicated directories, avoid concurrent writers and
protect local file permissions. Very large scripts, pauses or audio files can
consume substantial memory and disk space. Do not expose the CLI directly as an
unrestricted multi-user service.

For a vulnerability, use GitHub private vulnerability reporting if it is enabled
on [the repository](https://github.com/YusufBeratZengin/tts-batch/security).
Otherwise open a minimal issue requesting a private reporting channel, without
exploit details, credentials or personal data. Do not put sensitive reports in
public issues. Include affected versions, impact and a synthetic reproduction
once a private channel is available.
