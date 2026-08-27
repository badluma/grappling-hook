use std::fmt;
use std::string::String;

// === Structs ===
pub struct NamedOption {
    pub name: String,
    pub value: u16,
}

impl fmt::Display for NamedOption {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "{}", self.name) // only the name is shown in the list
    }
}

// === Constants ===
pub const LOGO: &str = "    ______
    \\ \\ \\ \\
<⎺\\ /_/_/_/
 \\(____|___/)
  \\________/";

pub const WAVE: &str = "~-_.,.,_-~~-_.,.,_-~~";

// === Functions ===
pub fn boot() {
    let width = terminal_size::terminal_size().map_or(20, |(w, _)| w.0);

    let wave: String = WAVE
        .chars()
        .cycle()
        .take(width.saturating_sub(4) as usize)
        .collect();

    print!("{}\n  {}  \n\n", LOGO, wave);
}

pub fn is_episode(name: &str) -> bool {
    name.as_bytes().windows(6).any(|w| {
        (w[0] | 32) == b's'
            && (w[3] | 32) == b'e'
            && [1, 2, 4, 5].iter().all(|&i| w[i].is_ascii_digit())
    })
}

/// Spinner on its own line until the returned handle is passed to `stop_spinner`.
pub fn spawn_spinner(message: &'static str) -> tokio::task::JoinHandle<()> {
    tokio::spawn(async move {
        let width = 11;
        let frames: Vec<String> = (0..WAVE.len())
            .map(|i| {
                (0..width)
                    .map(|j| WAVE.as_bytes()[(i + j) % WAVE.len()] as char)
                    .collect()
            })
            .collect();

        for frame in frames.iter().cycle() {
            print!("\r{frame} {message}");
            let _ = std::io::Write::flush(&mut std::io::stdout());
            tokio::time::sleep(std::time::Duration::from_millis(100)).await;
        }
    })
}

pub fn stop_spinner(handle: tokio::task::JoinHandle<()>) {
    handle.abort();
    print!("\r\x1b[2K"); // clear spinner line
}
