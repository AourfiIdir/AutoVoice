pub mod edge;
pub mod elevenlabs;
pub mod openai;

use std::path::PathBuf;
use std::sync::RwLock;

use anyhow::{bail, Result};

use self::edge::EdgeProvider;
use self::elevenlabs::ElevenLabsProvider;
use self::openai::OpenAiProvider;
use crate::config::Config;

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct VoiceInfo {
    pub name: String,
    pub short_name: String,
    pub gender: String,
    pub locale: String,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SynthesizeRequest {
    pub text: String,
    pub voice: String,
    #[serde(default = "default_rate")]
    pub rate: String,
    #[serde(default = "default_pitch")]
    pub pitch: String,
    #[serde(default = "default_volume")]
    pub volume: String,
}

fn default_rate() -> String {
    "+0%".to_string()
}

fn default_pitch() -> String {
    "+0Hz".to_string()
}

fn default_volume() -> String {
    "+0%".to_string()
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct SynthesizeResult {
    pub audio_bytes: Vec<u8>,
}

/// Parse a "+50%"/"0%"/"-25%" speed string into a multiplicative factor.
pub fn rate_percent_to_factor(rate: &str) -> f32 {
    let trimmed = rate.trim().trim_start_matches('+').trim_end_matches('%');
    let num: f32 = trimmed.trim().parse().unwrap_or(0.0);
    (1.0 + num / 100.0).clamp(0.25, 4.0)
}

/// Dispatch engine: picks the configured provider per request so the user can
/// switch providers at runtime without restarting the backend.
pub struct TtsEngine {
    config: RwLock<crate::config::TtsConfig>,
    config_path: PathBuf,
    client: reqwest::Client,
}

impl TtsEngine {
    pub fn new(config_path: PathBuf) -> Self {
        let cfg = Self::load_tts_config(&config_path);
        let client = reqwest::Client::builder()
            .timeout(std::time::Duration::from_secs(120))
            .build()
            .unwrap_or_default();
        Self {
            config: RwLock::new(cfg),
            config_path,
            client,
        }
    }

    fn load_tts_config(config_path: &PathBuf) -> crate::config::TtsConfig {
        if let Ok(data) = std::fs::read_to_string(config_path) {
            if let Ok(cfg) = serde_json::from_str::<Config>(&data) {
                return cfg.tts;
            }
        }
        crate::config::TtsConfig::default()
    }

    pub fn get_config(&self) -> crate::config::TtsConfig {
        self.config.read().unwrap().clone()
    }

    pub fn set_config(&self, new_tts: crate::config::TtsConfig) -> Result<()> {
        let mut full = if let Ok(data) = std::fs::read_to_string(&self.config_path) {
            serde_json::from_str::<Config>(&data)
                .map(|mut c| {
                    c.config_path = self.config_path.clone();
                    c
                })
                .unwrap_or_else(|_| Config::default())
        } else {
            Config::default()
        };
        full.tts = new_tts;
        full.save()?;
        *self.config.write().unwrap() = full.tts.clone();
        Ok(())
    }

    pub async fn list_voices(&self) -> Result<Vec<VoiceInfo>> {
        let cfg = self.config.read().unwrap().clone();
        match cfg.provider.as_str() {
            "openai" => {
                if cfg.openai_api_key.is_empty() {
                    bail!("OpenAI API key not configured — open TTS Settings");
                }
                OpenAiProvider::new(self.client.clone(), cfg.openai_api_key, cfg.openai_model)
                    .list_voices()
                    .await
            }
            "elevenlabs" => {
                if cfg.elevenlabs_api_key.is_empty() {
                    bail!("ElevenLabs API key not configured — open TTS Settings");
                }
                ElevenLabsProvider::new(self.client.clone(), cfg.elevenlabs_api_key, cfg.elevenlabs_model)
                    .list_voices()
                    .await
            }
            _ => EdgeProvider::list_voices().await,
        }
    }

    pub async fn synthesize(&self, req: &SynthesizeRequest) -> Result<SynthesizeResult> {
        let cfg = self.config.read().unwrap().clone();
        match cfg.provider.as_str() {
            "openai" => {
                if cfg.openai_api_key.is_empty() {
                    bail!("OpenAI API key not configured — open TTS Settings");
                }
                OpenAiProvider::new(self.client.clone(), cfg.openai_api_key, cfg.openai_model)
                    .synthesize(req)
                    .await
            }
            "elevenlabs" => {
                if cfg.elevenlabs_api_key.is_empty() {
                    bail!("ElevenLabs API key not configured — open TTS Settings");
                }
                ElevenLabsProvider::new(self.client.clone(), cfg.elevenlabs_api_key, cfg.elevenlabs_model)
                    .synthesize(req)
                    .await
            }
            _ => EdgeProvider.synthesize(req).await,
        }
    }
}