use anyhow::Result;
use edge_tts_rust::{Boundary, EdgeTtsClient, SpeakOptions};

pub struct TtsEngine {
    client: EdgeTtsClient,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct VoiceInfo {
    pub name: String,
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

impl TtsEngine {
    pub fn new() -> Result<Self> {
        let client = EdgeTtsClient::new()?;
        Ok(Self { client })
    }

    pub async fn synthesize(&self, req: &SynthesizeRequest) -> Result<SynthesizeResult> {
        let result = self
            .client
            .synthesize(
                &req.text,
                SpeakOptions {
                    voice: req.voice.clone(),
                    boundary: Boundary::Sentence,
                    ..SpeakOptions::default()
                },
            )
            .await?;

        Ok(SynthesizeResult {
            audio_bytes: result.audio,
        })
    }

    pub async fn list_voices() -> Result<Vec<VoiceInfo>> {
        // edge-tts-rust doesn't expose a list_voices API directly,
        // so we provide a hardcoded set of popular voices.
        // This can be expanded or fetched from the WebSocket protocol.
        let voices = vec![
            VoiceInfo { name: "en-US-GuyNeural".into(), gender: "Male".into(), locale: "en-US".into() },
            VoiceInfo { name: "en-US-AriaNeural".into(), gender: "Female".into(), locale: "en-US".into() },
            VoiceInfo { name: "en-US-JennyNeural".into(), gender: "Female".into(), locale: "en-US".into() },
            VoiceInfo { name: "en-US-EmmaMultilingualNeural".into(), gender: "Female".into(), locale: "en-US".into() },
            VoiceInfo { name: "en-US-DavisNeural".into(), gender: "Male".into(), locale: "en-US".into() },
            VoiceInfo { name: "en-GB-RyanNeural".into(), gender: "Male".into(), locale: "en-GB".into() },
            VoiceInfo { name: "en-GB-SoniaNeural".into(), gender: "Female".into(), locale: "en-GB".into() },
            VoiceInfo { name: "fr-FR-DeniseNeural".into(), gender: "Female".into(), locale: "fr-FR".into() },
            VoiceInfo { name: "fr-FR-HenriNeural".into(), gender: "Male".into(), locale: "fr-FR".into() },
            VoiceInfo { name: "es-ES-ElviraNeural".into(), gender: "Female".into(), locale: "es-ES".into() },
            VoiceInfo { name: "es-ES-AlvaroNeural".into(), gender: "Male".into(), locale: "es-ES".into() },
            VoiceInfo { name: "de-DE-KatjaNeural".into(), gender: "Female".into(), locale: "de-DE".into() },
            VoiceInfo { name: "de-DE-ConradNeural".into(), gender: "Male".into(), locale: "de-DE".into() },
            VoiceInfo { name: "ja-JP-NanamiNeural".into(), gender: "Female".into(), locale: "ja-JP".into() },
            VoiceInfo { name: "ja-JP-KeitaNeural".into(), gender: "Male".into(), locale: "ja-JP".into() },
            VoiceInfo { name: "zh-CN-XiaoxiaoNeural".into(), gender: "Female".into(), locale: "zh-CN".into() },
            VoiceInfo { name: "zh-CN-YunxiNeural".into(), gender: "Male".into(), locale: "zh-CN".into() },
            VoiceInfo { name: "pt-BR-FranciscaNeural".into(), gender: "Female".into(), locale: "pt-BR".into() },
            VoiceInfo { name: "pt-BR-AntonioNeural".into(), gender: "Male".into(), locale: "pt-BR".into() },
            VoiceInfo { name: "ar-SA-ZariyahNeural".into(), gender: "Female".into(), locale: "ar-SA".into() },
            VoiceInfo { name: "ar-SA-HamedNeural".into(), gender: "Male".into(), locale: "ar-SA".into() },
        ];
        Ok(voices)
    }
}
