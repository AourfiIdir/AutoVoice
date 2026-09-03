use anyhow::{bail, Context, Result};
use serde_json::{json, Value};

use super::{SynthesizeRequest, SynthesizeResult, VoiceInfo};

const ELEVENLABS_VOICES_URL: &str = "https://api.elevenlabs.io/v1/voices";
const ELEVENLABS_TTS_URL: &str = "https://api.elevenlabs.io/v1/text-to-speech";

pub struct ElevenLabsProvider {
    client: reqwest::Client,
    api_key: String,
    model: String,
}

impl ElevenLabsProvider {
    pub fn new(client: reqwest::Client, api_key: String, model: String) -> Self {
        Self {
            client,
            api_key,
            model,
        }
    }

    pub async fn synthesize(&self, req: &SynthesizeRequest) -> Result<SynthesizeResult> {
        let url = format!("{ELEVENLABS_TTS_URL}/{}", req.voice);
        let body = json!({
            "text": req.text,
            "model_id": self.model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        });

        let resp = self
            .client
            .post(&url)
            .header("xi-api-key", &self.api_key)
            .header("Accept", "audio/mpeg")
            .json(&body)
            .send()
            .await
            .context("ElevenLabs request failed")?;

        let status = resp.status();
        let bytes = resp.bytes().await.context("Failed to read ElevenLabs response")?;

        if !status.is_success() {
            bail!("ElevenLabs error {status}: {}", String::from_utf8_lossy(&bytes));
        }
        if bytes.is_empty() {
            bail!("ElevenLabs returned an empty audio response");
        }

        Ok(SynthesizeResult {
            audio_bytes: bytes.to_vec(),
        })
    }

    pub async fn list_voices(&self) -> Result<Vec<VoiceInfo>> {
        let resp = self
            .client
            .get(ELEVENLABS_VOICES_URL)
            .header("xi-api-key", &self.api_key)
            .send()
            .await
            .context("ElevenLabs voice request failed")?;

        let status = resp.status();
        let text = resp.text().await.context("Failed to read ElevenLabs voices")?;

        if !status.is_success() {
            bail!("ElevenLabs error {status}: {text}");
        }

        let data: Value = serde_json::from_str(&text).context("Invalid ElevenLabs voice response")?;
        let mut voices = Vec::new();
        if let Some(list) = data.get("voices").and_then(Value::as_array) {
            for v in list {
                let name = v.get("name").and_then(Value::as_str).unwrap_or("Unknown");
                let id = v.get("voice_id").and_then(Value::as_str).unwrap_or("");
                voices.push(VoiceInfo {
                    name: name.to_string(),
                    short_name: id.to_string(),
                    gender: String::new(),
                    locale: String::new(),
                });
            }
        }
        Ok(voices)
    }
}