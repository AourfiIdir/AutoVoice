use anyhow::{bail, Context, Result};
use serde_json::json;

use super::{rate_percent_to_factor, SynthesizeRequest, SynthesizeResult, VoiceInfo};

const OPENAI_TTS_URL: &str = "https://api.openai.com/v1/audio/speech";

/// Voices supported by the gpt-4o-mini-tts model (superset of tts-1 voices).
const OPENAI_VOICES: [&str; 11] = [
    "alloy", "ash", "ballad", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer", "verse",
];

pub struct OpenAiProvider {
    client: reqwest::Client,
    api_key: String,
    model: String,
}

impl OpenAiProvider {
    pub fn new(client: reqwest::Client, api_key: String, model: String) -> Self {
        Self {
            client,
            api_key,
            model,
        }
    }

    pub async fn synthesize(&self, req: &SynthesizeRequest) -> Result<SynthesizeResult> {
        let body = json!({
            "model": self.model,
            "input": req.text,
            "voice": req.voice,
            "speed": rate_percent_to_factor(&req.rate),
            "response_format": "mp3",
        });

        let resp = self
            .client
            .post(OPENAI_TTS_URL)
            .bearer_auth(&self.api_key)
            .json(&body)
            .send()
            .await
            .context("OpenAI request failed")?;

        let status = resp.status();
        let bytes = resp.bytes().await.context("Failed to read OpenAI response")?;

        if !status.is_success() {
            bail!("OpenAI error {status}: {}", String::from_utf8_lossy(&bytes));
        }
        if bytes.is_empty() {
            bail!("OpenAI returned an empty audio response");
        }

        Ok(SynthesizeResult {
            audio_bytes: bytes.to_vec(),
        })
    }

    pub async fn list_voices(&self) -> Result<Vec<VoiceInfo>> {
        Ok(OPENAI_VOICES
            .iter()
            .map(|v| VoiceInfo {
                name: (*v).to_string(),
                short_name: (*v).to_string(),
                gender: String::new(),
                locale: String::new(),
            })
            .collect())
    }
}