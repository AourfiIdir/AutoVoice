mod api;
mod audio;
mod config;
mod tts;

use std::sync::Arc;

use axum::{routing::{get, post, delete}, Router};
use tower_http::cors::{Any, CorsLayer};
use tracing_subscriber::EnvFilter;

use crate::api::routes;
use crate::audio::convert::AudioManager;
use crate::config::Config;
use crate::tts::edge::TtsEngine;

pub type AppState = (Arc<TtsEngine>, Arc<AudioManager>);

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")),
        )
        .init();

    let config = Config::default();
    let tts = Arc::new(TtsEngine::new()?);
    let audio = Arc::new(AudioManager::new(&config.audio_dir)?);

    tracing::info!("AutoVoice backend starting on port {}", config.backend_port);

    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    let app = Router::new()
        .route("/health", get(routes::health))
        .route("/voices", get(routes::list_voices))
        .route("/generate", post(routes::generate))
        .route("/generate-batch", post(routes::generate_batch))
        .route("/audio/{id}", get(routes::get_audio))
        .route("/audio/{id}", delete(routes::delete_audio))
        .route("/cleanup", post(routes::cleanup))
        .layer(cors)
        .with_state((tts, audio));

    let addr = format!("0.0.0.0:{}", config.backend_port);
    let listener = tokio::net::TcpListener::bind(&addr).await?;
    tracing::info!("Listening on {}", addr);
    axum::serve(listener, app).await?;

    Ok(())
}
