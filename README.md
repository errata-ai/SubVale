# Vale + Sublime Text

A **Sublime Text 3** (build 3080+) package for [Vale][Vale-home], the customizable linter for prose.

### Interactive Linting

![Preview image][preview-img]

Bring your style guide to life with detailed pop-ups or status bar messages.

### Style & Rule Management

![Demo GIF][demo-gif]

Easily access styles defined in your Vale configuration file on a per-view basis.

## Installation

1. Install [Vale][Vale-install].
2. Install [Package Control][pck-ctrl].
3. Bring up the Command Palette
   (<kbd>Command-Shift-P</kbd> on macOS and <kbd>Ctrl-Shift-P</kbd> on Linux/Windows).
4. Select `Package Control: Install Package`
   and then select `Vale` when the list appears.

## Usage

The first step is to specify the location of the Vale binary in your settings file (`Preferences → Package Settings → Vale → Settings - User`):

```json
// Enter your path here ...
{
    "vale_binary": "/usr/local/bin/vale",
}
```

From here, you can run one of the following commands via the Command Palette:

1. `Vale: Lint View`: runs the Vale binary on the active view.
2. `Vale: Edit Styles`: shows a list of styles relevant to the active view.
3. `Vale: New Rule`: shows a list of extension points and opens the associated template.

## Configuration

This package exposes a number of [configuration options](https://github.com/jdkato/SubVale/blob/master/Vale.sublime-settings). These include styling the in-text alerts, adding custom HTML/CSS for the pop-ups, and listing accepted syntaxes.

See the Default settings file (`Preferences → Package Settings → Vale → Settings - Default`) for more details.

[Vale-home]: https://valelint.github.io/
[Vale-install]: https://valelint.github.io/getting-started/
[pck-ctrl]: https://packagecontrol.io/installation "Sublime Package Control by wbond"

[preview-img]: https://cloud.githubusercontent.com/assets/8785025/23342357/b756e524-fc0d-11e6-8705-856c8a4c56f3.png
[demo-gif]: https://i.gyazo.com/819d7793b4080d5b613836d06a89740e.gif
