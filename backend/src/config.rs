use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

/// Runtime-selectable TTS provider configuration.
/// Persisted to `config.json` next to the backend executable.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct TtsConfig {
    /// One of: "edge", "openai", "elevenlabs"
    pub provider: String,
    pub openai_api_key: String,
    pub openai_model: String,
    pub elevenlabs_api_key: String,
    pub elevenlabs_model: String,
}

impl Default for TtsConfig {
    fn default() -> Self {
        Self {
            provider: "edge".to_string(),
            openai_api_key: String::new(),
            openai_model: "gpt-4o-mini-tts".to_string(),
            elevenlabs_api_key: String::new(),
            elevenlabs_model: "eleven_multilingual_v2".to_string(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct Config {
    pub backend_version:u16,
    pub backend_port: u16,
    pub resolve_port: u16,
    pub resolve_host: String,
    pub audio_dir: PathBuf,
    pub tts: TtsConfig,
    #[serde(skip)]
    pub config_path: PathBuf,
}

impl Default for Config {
    fn default() -> Self {
        // Use the exe's directory as base, not CWD
        let exe_dir = std::env::current_exe()
            .ok()
            .and_then(|p| p.parent().map(|p| p.to_path_buf()))
            .unwrap_or_else(|| PathBuf::from("."));

        Self {
            backend_version:2,
            backend_port: 56133,
            resolve_port: 56132,
            resolve_host: "127.0.0.1".to_string(),
            audio_dir: exe_dir.join("audio_output"),
            tts: TtsConfig::default(),
            config_path: exe_dir.join("config.json"),
        }
    }
}

impl Config {
    /// Load `config.json` from the exe dir, falling back to defaults.
    pub fn load() -> Self {
        let defaults = Self::default();
        let path = defaults.config_path.clone();
        if let Ok(data) = std::fs::read_to_string(&path) {
            if let Ok(mut parsed) = serde_json::from_str::<Config>(&data) {
                parsed.config_path = path;
                return parsed;
            }
        }
        defaults
    }

    pub fn save(&self) -> Result<(), std::io::Error> {
        let data = serde_json::to_string_pretty(self)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?;
        std::fs::write(&self.config_path, data)
    }

    #[allow(dead_code)]
    pub fn resolve_url(&self) -> String {
        format!("http://{}:{}", self.resolve_host, self.resolve_port)
    }

    pub fn config_path(&self) -> &Path {
        &self.config_path
    }
}