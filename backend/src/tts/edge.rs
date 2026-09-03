use anyhow::Result;
use edge_tts_rust::{Boundary, EdgeTtsClient, SpeakOptions};

use super::{SynthesizeRequest, SynthesizeResult, VoiceInfo};

pub struct EdgeProvider;

impl EdgeProvider {
    pub async fn synthesize(&self, req: &SynthesizeRequest) -> Result<SynthesizeResult> {
        let client = EdgeTtsClient::new()?;
        let result = client
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
        #[rustfmt::skip]
        let raw = [
            ("en-US-GuyNeural", "Male", "en-US"),
            ("en-US-AriaNeural", "Female", "en-US"),
            ("en-US-JennyNeural", "Female", "en-US"),
            ("en-US-EmmaMultilingualNeural", "Female", "en-US"),
            ("en-US-DavisNeural", "Male", "en-US"),
            ("en-GB-RyanNeural", "Male", "en-GB"),
            ("en-GB-SoniaNeural", "Female", "en-GB"),
            ("fr-FR-DeniseNeural", "Female", "fr-FR"),
            ("fr-FR-HenriNeural", "Male", "fr-FR"),
            ("es-ES-ElviraNeural", "Female", "es-ES"),
            ("es-ES-AlvaroNeural", "Male", "es-ES"),
            ("de-DE-KatjaNeural", "Female", "de-DE"),
            ("de-DE-ConradNeural", "Male", "de-DE"),
            ("ja-JP-NanamiNeural", "Female", "ja-JP"),
            ("ja-JP-KeitaNeural", "Male", "ja-JP"),
            ("zh-CN-XiaoxiaoNeural", "Female", "zh-CN"),
            ("zh-CN-YunxiNeural", "Male", "zh-CN"),
            ("pt-BR-FranciscaNeural", "Female", "pt-BR"),
            ("pt-BR-AntonioNeural", "Male", "pt-BR"),
            ("ar-SA-ZariyahNeural", "Female", "ar-SA"),
            ("ar-SA-HamedNeural", "Male", "ar-SA"),
        ];
        let voices = raw
            .iter()
            .map(|(name, gender, locale)| VoiceInfo {
                name: (*name).to_string(),
                short_name: (*name).to_string(),
                gender: (*gender).to_string(),
                locale: (*locale).to_string(),
            })
            .collect();
        Ok(voices)
    }
}