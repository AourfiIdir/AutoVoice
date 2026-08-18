use std::path::PathBuf;

#[allow(dead_code)]
pub struct Config {
    pub backend_port: u16,
    pub resolve_port: u16,
    pub resolve_host: String,
    pub audio_dir: PathBuf,
}

impl Default for Config {
    fn default() -> Self {
        // Use the exe's directory as base, not CWD
        let exe_dir = std::env::current_exe()
            .ok()
            .and_then(|p| p.parent().map(|p| p.to_path_buf()))
            .unwrap_or_else(|| PathBuf::from("."));

        Self {
            backend_port: 56133,
            resolve_port: 56132,
            resolve_host: "127.0.0.1".to_string(),
            audio_dir: exe_dir.join("audio_output"),
        }
    }
}

impl Config {
    #[allow(dead_code)]
    pub fn resolve_url(&self) -> String {
        format!("http://{}:{}", self.resolve_host, self.resolve_port)
    }
}
