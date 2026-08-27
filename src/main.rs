mod aniworld;
mod functions;

use functions::*;
use inquire::ui::{Color, RenderConfig, StyleSheet, Styled};
use inquire::{MultiSelect, Select, Text};

// Styling options for inquire
fn label(text: &str) -> RenderConfig<'_> {
    let white = StyleSheet::empty().with_fg(Color::White);
    let mut cfg = RenderConfig::empty()
        .with_prompt_prefix(Styled::new(text).with_fg(Color::White))
        .with_answered_prompt_prefix(Styled::new(text).with_fg(Color::White))
        .with_highlighted_option_prefix(Styled::new(">").with_fg(Color::White))
        .with_selected_checkbox(Styled::new("[x]").with_fg(Color::White))
        .with_unselected_checkbox(Styled::new("[ ]").with_fg(Color::White))
        .with_answer(white)
        .with_option(white)
        .with_selected_option(Some(white))
        .with_text_input(white)
        .with_help_message(white);
    cfg.prompt = white;
    cfg
}

// Quit if keyboard interrupt
#[tokio::main]
async fn main() {
    if let Err(e) = run().await {
        if matches!(
            e.downcast_ref(),
            Some(inquire::InquireError::OperationInterrupted)
        ) {
            return;
        }
        eprintln!("{e}");
    }
}

async fn run() -> Result<(), Box<dyn std::error::Error>> {
    inquire::set_global_render_config(label(""));

    // Boot
    boot();

    // Choose categories
    let categories = vec![
        NamedOption {
            name: "Movie".to_string(),
            value: 0,
        },
        NamedOption {
            name: "Show".to_string(),
            value: 1,
        },
    ];
    let category = {
        Select::new("", categories)
            .with_render_config(label("Categories:"))
            .without_help_message()
            .prompt()?
    };

    // Choose quality

    let qualities: Vec<NamedOption> = if category.value == 0 {
        vec![
            NamedOption {
                name: "2160p+".to_string(),
                value: 211,
            },
            NamedOption {
                name: "720p-1080p".to_string(),
                value: 207,
            },
            NamedOption {
                name: "≤480p".to_string(),
                value: 201,
            },
        ]
    } else {
        vec![
            NamedOption {
                name: "2160p+".to_string(),
                value: 212,
            },
            NamedOption {
                name: "720p-1080p".to_string(),
                value: 208,
            },
            NamedOption {
                name: "≤480p".to_string(),
                value: 201,
            },
        ]
    };
    let quality = {
        MultiSelect::new("", qualities)
            .with_render_config(label("Quality:   "))
            .without_help_message()
            .with_default(&[1])
            .prompt()?
    };

    // Search
    let query = Text::new("")
        .with_render_config(label("Search:    "))
        .prompt()?;

    // Play loading animation
    let loading = spawn_spinner("Searching...");

    // Find torrents
    let mut torrents = Vec::new();
    for q in &quality {
        let cat = rbay::Category::new(q.value);
        torrents.extend(rbay::search(&query, cat).await?);
    }
    stop_spinner(loading);
    // apibay returns a placeholder row with id 0 when nothing matches
    torrents.retain(|t: &rbay::PartialTorrent| t.id != 0);

    println!(
        "Results:    {} torrent{}",
        torrents.len(),
        if torrents.len() != 1 { "s" } else { "" }
    );
    if torrents.is_empty() {
        return Ok(()); // Quit if nothing found
    }

    // Iterate through all results
    // Only passes reputable sources
    let keep = |t: &rbay::PartialTorrent| {
        !matches!(t.status, rbay::UserStatus::Member) && !is_episode(&t.name)
    };

    //
    let longest_name_length = torrents
        .iter()
        .filter(|t| keep(t))
        .map(|t| t.name.chars().count())
        .max()
        .unwrap_or(0);

    let mut results: Vec<NamedOption> = Vec::new();
    for (i, torrent) in torrents.iter().enumerate() {
        if !keep(torrent) {
            continue;
        }
        results.push(NamedOption {
            name: format!(
                "{:<longest_name_length$} | {:.2}GB",
                torrent.name,
                torrent.size as f64 / 1e9
            ),
            value: i as u16,
        });
    }

    // Select torrent
    let selected = Select::new("", results)
        .with_render_config(label("Select:    "))
        .prompt()?;

    open::that(torrents[selected.value as usize].magnet())?;
    println!("\nOpened magnet link in default app.");

    loop {
        let action = Select::new(
            "",
            vec![
                NamedOption {
                    name: "Done".to_string(),
                    value: 0,
                },
                NamedOption {
                    name: "Reopen magnet link".to_string(),
                    value: 1,
                },
                NamedOption {
                    name: "Show magnet link".to_string(),
                    value: 2,
                },
                NamedOption {
                    name: "Cancel".to_string(),
                    value: 3,
                },
            ],
        )
        .with_render_config(label("Select 'Done' when the download finished."))
        .prompt()?;

        match action.value {
            1 => open::that(torrents[selected.value as usize].magnet())?,
            2 => println!(
                "\nMagnet link: {}\n",
                torrents[selected.value as usize].magnet()
            ),
            3 => std::process::exit(0),
            _ => break,
        }
    }

    Ok(())
}
