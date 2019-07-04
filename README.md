# Vale Server + Sublime Text

A **Sublime Text 3** (build 3080+) package for [Vale Server][Vale-home], a customizable linter for prose.

### Interactive Linting

![Preview image][preview-img]

Bring your style guide to life with detailed pop-ups or status bar messages.

### Style & Rule Management

![Demo GIF][demo-gif]

Easily access styles defined in your Vale configuration file on a per-view basis.

## Installation

1. Install [Vale Server][Vale-install].
2. Install [Package Control][pck-ctrl].
3. Bring up the Command Palette
   (<kbd>Command-Shift-P</kbd> on macOS and <kbd>Ctrl-Shift-P</kbd> on Linux/Windows).
4. Select `Package Control: Install Package`
   and then select `Vale` when the list appears.

## Usage

You can run one of the following commands via the Command Palette:

1. `Vale Server: Lint View`: runs Vale Server on the active view.
2. `Vale Server: Edit Styles`: shows a list of styles relevant to the active view.
3. `Vale Server: Open Dashboard`: opens the Vale Server dashboard in your default browser.

## Configuration

This package exposes a number of [configuration options](https://github.com/jdkato/SubVale/blob/master/Vale.sublime-settings). These include styling the in-text alerts, adding custom HTML/CSS for the pop-ups, and listing accepted syntaxes.

See the Default settings file (`Preferences → Package Settings → Vale → Settings - Default`) for more details.

[Vale-home]: https://errata.ai/vale-server/
[Vale-install]: https://errata-ai.github.io/vale-server/docs/install
[pck-ctrl]: https://packagecontrol.io/installation "Sublime Package Control by wbond"

[preview-img]: https://user-images.githubusercontent.com/8785025/60686241-734b3800-9e5c-11e9-85f0-cf2899b2fb26.gif
[demo-gif]: https://i.gyazo.com/819d7793b4080d5b613836d06a89740e.gif
