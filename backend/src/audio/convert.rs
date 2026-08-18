use anyhow::{Context, Result};
use std::path::{Path, PathBuf};
use uuid::Uuid;

pub struct AudioManager {
    output_dir: PathBuf,
}

impl AudioManager {
    pub fn new(output_dir: &Path) -> Result<Self> {
        std::fs::create_dir_all(output_dir)
            .context("Failed to create audio output directory")?;
        Ok(Self {
            output_dir: output_dir.to_path_buf(),
        })
    }

    pub fn save_audio(&self, id: &str, data: &[u8]) -> Result<PathBuf> {
        let path = self.output_dir.join(format!("{}.mp3", id));
        std::fs::write(&path, data).context("Failed to write audio file")?;
        Ok(path)
    }

    pub fn get_path(&self, id: &str) -> PathBuf {
        self.output_dir.join(format!("{}.mp3", id))
    }

    pub fn exists(&self, id: &str) -> bool {
        self.get_path(id).exists()
    }

    pub fn delete(&self, id: &str) -> Result<bool> {
        let path = self.get_path(id);
        if path.exists() {
            std::fs::remove_file(&path)?;
            Ok(true)
        } else {
            Ok(false)
        }
    }

    pub fn generate_id() -> String {
        Uuid::new_v4().to_string()
    }

    pub fn cleanup_old_files(&self, max_age_secs: u64) -> Result<usize> {
        let mut removed = 0;
        if !self.output_dir.exists() {
            return Ok(0);
        }

        let now = std::time::SystemTime::now();
        for entry in std::fs::read_dir(&self.output_dir)? {
            let entry = entry?;
            let metadata = entry.metadata()?;
            if let Ok(modified) = metadata.modified() {
                if let Ok(age) = now.duration_since(modified) {
                    if age.as_secs() > max_age_secs {
                        std::fs::remove_file(entry.path())?;
                        removed += 1;
                    }
                }
            }
        }
        Ok(removed)
    }
}
