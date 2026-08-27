# Grappling Hook

Grappling Hook is a terminal client that lets you search movies and shows from The Pirate Bay and download them using your default BitTorrent client.

![](./assets/demo.gif)

## Features

- Choose quality (from ≤480p to 2160p+)
- Search for anything
- Filtering
  - Single episodes
  - Unreputable sources
  - Torrents that don't match search options
- Choose a torrent to download
- View file size before downloading

## Install

If you dont already have it installed, install rustup which ships with the cargo package manager by running the following command on Linux or MacOS

```
curl https://sh.rustup.rs -sSf | sh
```

If you are on Windows, download and open the exe for your system [here](https://rust-lang.github.io/rustup/installation/other.html#manual-installation).

Once you have cargo installed, run this command to install grappling hook.


```
cargo install grappling-hook
```

## Usage

To open Grappling Hook in the terminal, simply run this command.

```
grappling-hook
```

## License

This project is MIT licensed.

# Disclaimer

Grappling Hook is not affiliated with The Pirate Bay or any of its content providers, and is intended to download copyright-free content. Use at your own risk.
