---
name: deepgram-transcribe
description: Transcribes an audio file using Deepgram nova-3 with Russian language and speaker diarization. Use for meetings, interviews, or any multi-speaker recording. Saves output with a date-prefixed filename.
argument-hint: <audio-file> [destination-folder] [suffix]
allowed-tools: Bash, Read, Write, Glob
---

Transcribe an audio file with speaker diarization using Deepgram nova-3.

Arguments:
- audio-file: Path to the audio file to transcribe (absolute or relative).
- destination-folder: (optional) Folder where the transcription will be saved. Default: `company/meetings/`.
- suffix: (optional) Short topic or participant name for the output file, e.g. "team-sync", "hotel-interview".

Steps:
1. Verify the audio file exists at the specified path. If not found, report and stop.
2. If suffix was not provided, ask: "What should the output file be named? (e.g. 'team-sync', 'hotel-interview')" — wait for the answer before continuing.
3. Convert suffix to lowercase, replace spaces with dashes (kebab-case).
4. If destination-folder was not provided, default to `company/meetings/`.
5. Ensure the destination folder exists. Create it if necessary.
6. Use today's real system date in YYYY-MM-DD format (run `date +%Y-%m-%d`, do not rely on `currentDate` in system prompt).
7. Run the transcription: `cd scripts/transcriber && poetry run deepgram-transcribe <absolute-path-to-audio-file>`
8. Save the transcription output to `<destination-folder>/YYYY-MM-DD-<suffix>.txt`

Output format: each speaker turn appears as `[Speaker N]: <utterance>` on its own line.

Report what was done: audio file path, transcription saved to path.

Notes:
- Requires `DEEPGRAM_API_KEY` in `scripts/transcriber/.env` (file is gitignored).
- Pass `--language <code>` to the CLI for non-Russian recordings (default: `ru`).
