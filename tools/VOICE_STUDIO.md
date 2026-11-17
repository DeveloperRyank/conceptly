# VoiceStudio narration connection

Conceptly calls VoiceStudio's OpenAI-compatible `POST /v1/audio/speech` endpoint
from its backend. The upstream service is https://github.com/debpalash/VoiceStudio.
No upstream implementation or model weights are bundled into Conceptly.

VoiceStudio must run on a persistent host with sufficient memory for its selected
engine. Its documented Docker image is `ghcr.io/debpalash/voicestudio:stable`;
use the upstream Docker installation guide, persistent model/data storage,
`OMNIVOICE_API_KEY`, and HTTPS through the host's reverse proxy. Download a model
and confirm the selected voice works on that host before connecting Conceptly.
Vercel serves the web app; it does not host these speech models.

Set these in Vercel's project environment settings, then redeploy:

- `VOICESTUDIO_URL`: HTTPS origin of the VoiceStudio server, without `/v1`.
- `VOICESTUDIO_API_KEY`: the host's private `OMNIVOICE_API_KEY`.
- `VOICESTUDIO_MODEL`: installed engine ID, default `omnivoice`.
- `VOICESTUDIO_VOICE`: configured voice profile ID/name, default `default`.

Credentials stay on the server. Responses must be WAV audio. A connection failure
falls back to the existing narrator. The lesson player uses audio progress to keep
writing and voice aligned and applies its selected playback rate.

No host or credential was provided for this update, so the connector is dormant.
