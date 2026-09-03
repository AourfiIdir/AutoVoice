use axum::{
    extract::{Path, State},
    http::StatusCode,
    Json,
};
use serde::{Deserialize, Serialize};

use crate::audio::convert::AudioManager;
use crate::config::TtsConfig;
use crate::tts::{SynthesizeRequest, VoiceInfo};
use crate::AppState;

#[derive(Serialize)]
pub struct HealthResponse {
    pub ok: bool,
    pub service: &'static str,
    pub version: &'static str,
}

pub async fn health() -> Json<HealthResponse> {
    Json(HealthResponse {
        ok: true,
        service: "autovoice-backend",
        version: "0.1.0",
    })
}

pub async fn list_voices(
    State((tts, _)): State<AppState>,
) -> Result<Json<Vec<VoiceInfo>>, (StatusCode, String)> {
    tts.list_voices()
        .await
        .map(Json)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))
}

pub async fn get_config(State((tts, _)): State<AppState>) -> Json<TtsConfig> {
    Json(tts.get_config())
}

pub async fn set_config(
    State((tts, _)): State<AppState>,
    Json(config): Json<TtsConfig>,
) -> Result<Json<TtsConfig>, (StatusCode, String)> {
    tts.set_config(config)
        .map(|_| Json(tts.get_config()))
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))
}

#[derive(Deserialize)]
pub struct GenerateRequest {
    pub text: String,
    #[serde(default = "default_voice")]
    pub voice: String,
    #[serde(default = "default_rate")]
    pub rate: String,
    #[serde(default = "default_pitch")]
    pub pitch: String,
    #[serde(default = "default_volume")]
    pub volume: String,
}

fn default_voice() -> String {
    "en-US-GuyNeural".to_string()
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

#[derive(Serialize)]
pub struct GenerateResponse {
    pub id: String,
    pub path: String,
}

pub async fn generate(
    State((tts, audio)): State<AppState>,
    Json(req): Json<GenerateRequest>,
) -> Result<Json<GenerateResponse>, (StatusCode, String)> {
    let synthesize_req = SynthesizeRequest {
        text: req.text,
        voice: req.voice,
        rate: req.rate,
        pitch: req.pitch,
        volume: req.volume,
    };

    let result = tts
        .synthesize(&synthesize_req)
        .await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    let id = AudioManager::generate_id();
    let path = audio
        .save_audio(&id, &result.audio_bytes)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    Ok(Json(GenerateResponse {
        id,
        path: path.to_string_lossy().to_string(),
    }))
}

#[derive(Deserialize)]
pub struct GenerateBatchRequest {
    pub segments: Vec<BatchSegment>,
    #[serde(default = "default_voice")]
    pub voice: String,
    #[serde(default = "default_rate")]
    pub rate: String,
    #[serde(default = "default_pitch")]
    pub pitch: String,
    #[serde(default = "default_volume")]
    pub volume: String,
}

#[derive(Deserialize)]
pub struct BatchSegment {
    pub text: String,
    pub start_frame: f64,
    pub end_frame: f64,
    pub track_index: Option<u32>,
}

#[derive(Serialize)]
pub struct BatchResult {
    pub id: String,
    pub path: String,
    pub start_frame: f64,
    pub end_frame: f64,
    pub track_index: u32,
}

#[derive(Serialize)]
pub struct GenerateBatchResponse {
    pub results: Vec<BatchResult>,
    pub errors: Vec<BatchError>,
}

#[derive(Serialize)]
pub struct BatchError {
    pub index: usize,
    pub error: String,
}

pub async fn generate_batch(
    State((tts, audio)): State<AppState>,
    Json(req): Json<GenerateBatchRequest>,
) -> Result<Json<GenerateBatchResponse>, (StatusCode, String)> {
    let mut results = Vec::new();
    let mut errors = Vec::new();

    for (i, segment) in req.segments.iter().enumerate() {
        let synthesize_req = SynthesizeRequest {
            text: segment.text.clone(),
            voice: req.voice.clone(),
            rate: req.rate.clone(),
            pitch: req.pitch.clone(),
            volume: req.volume.clone(),
        };

        match tts.synthesize(&synthesize_req).await {
            Ok(result) => {
                let id = AudioManager::generate_id();
                match audio.save_audio(&id, &result.audio_bytes) {
                    Ok(path) => {
                        results.push(BatchResult {
                            id,
                            path: path.to_string_lossy().to_string(),
                            start_frame: segment.start_frame,
                            end_frame: segment.end_frame,
                            track_index: segment.track_index.unwrap_or(1),
                        });
                    }
                    Err(e) => {
                        errors.push(BatchError {
                            index: i,
                            error: e.to_string(),
                        });
                    }
                }
            }
            Err(e) => {
                errors.push(BatchError {
                    index: i,
                    error: e.to_string(),
                });
            }
        }
    }

    Ok(Json(GenerateBatchResponse { results, errors }))
}

pub async fn get_audio(
    Path(id): Path<String>,
    State((_, audio)): State<AppState>,
) -> Result<(StatusCode, Vec<u8>), (StatusCode, String)> {
    if !audio.exists(&id) {
        return Err((StatusCode::NOT_FOUND, "Audio not found".to_string()));
    }

    let path = audio.get_path(&id);
    let data = std::fs::read(&path).map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    Ok((StatusCode::OK, data))
}

pub async fn delete_audio(
    Path(id): Path<String>,
    State((_, audio)): State<AppState>,
) -> Result<StatusCode, (StatusCode, String)> {
    audio
        .delete(&id)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    Ok(StatusCode::NO_CONTENT)
}

pub async fn cleanup(
    State((_, audio)): State<AppState>,
) -> Result<Json<serde_json::Value>, (StatusCode, String)> {
    let removed = audio
        .cleanup_old_files(3600)
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;
    Ok(Json(serde_json::json!({ "removed": removed })))
}
