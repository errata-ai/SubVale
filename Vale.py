import binascii
import json
import os
import subprocess
import urllib.parse
import webbrowser

import requests

import sublime
import sublime_plugin

Settings = None


class ValeFixCommand(sublime_plugin.TextCommand):
    """Applies a fix for an alert.
    """

    def run(self, edit, **args):
        alert, suggestion = args["alert"], args["suggestion"]

        offset = self.view.text_point(alert["Line"] - 1, 0)
        coords = sublime.Region(
            offset + alert["Span"][0] - 1, offset + alert["Span"][1]
        )

        if alert["Action"]["Name"] != "remove":
            self.view.replace(edit, coords, suggestion)
        else:
            coords.b = coords.b + 1
            self.view.erase(edit, coords)

        self.view.window().status_message(
            "[Vale Server] Successfully applied fix!")


def debug(message, prefix="Vale", level="debug"):
    """Print a formatted console entry to the Sublime Text console.

    Args:
        message (str): A message to print to the console
        prefix (str): An optional prefix
        level (str): One of debug, info, warning, error [Default: debug]

    Returns:
        str: Issue a standard console print command.
    """
    if Settings.get("vale_debug"):
        print(
            "{prefix}: [{level}] {message}".format(
                message=message, prefix=prefix, level=level
            )
        )


def show_suggestions(suggestions, payload):
    """Show a Quick Panel of possible solutions for the given alert.
    """
    alert = json.loads(payload)

    options = []
    for suggestion in suggestions:
        if alert["Action"]["Name"] == "remove":
            options.append("Remove '" + alert["Match"] + "'")
        else:
            options.append("Replace with '" + suggestion + "'")

    sublime.active_window().show_quick_panel(
        options,
        lambda idx: apply_suggestion(alert, suggestions, idx),
        sublime.MONOSPACE_FONT
    )


def apply_suggestion(alert, suggestions, idx):
    """Apply the given suggestion to the active buffer.
    """
    if idx >= 0 and idx < len(suggestions):
        suggestion = suggestions[idx]

        view = sublime.active_window().active_view()
        view.run_command("vale_fix", {
            "alert": alert, "suggestion": suggestion
        })


def handle_navigation(path):
    """Handle navigation after a user clicks one of our links.
    """
    if os.path.exists(path):
        # The path exists, open it in a new tab.
        sublime.active_window().open_file(path)
    elif path.startswith("http"):
        # The path doesn't exist, assume it's an URL.
        webbrowser.open(path)
    else:
        # It's an alert to process.
        server = urllib.parse.urljoin(Settings.get("vale_server"), "suggest")

        alert = binascii.unhexlify(path.encode()).decode()
        r = requests.post(server, data={
            "alert": alert
        })

        show_suggestions(r.json().get("suggestions", []), alert)


def query(endpoint, payload={}):
    """Query the Vale Server API with the given `endpoint` and `payload`.
    """
    try:
        server = urllib.parse.urljoin(Settings.get("vale_server"), endpoint)
        r = requests.get(server, data=payload)
        return r.json() if r.status_code == 200 else {}
    except requests.exceptions.RequestException as e:
        debug(str(e), level="error")
        return {}


def make_link(url, linkText="{url}"):
    """Return a link HTML string.
    """
    template = "<a href=\"{url}\">" + linkText + "</a>"
    return template.format(url=url)


class ValeSettings(object):
    """Provide global access to and management of Vale's settings.
    """

    settings_file = "Vale.sublime-settings"
    settings = sublime.load_settings(settings_file)

    def __init__(self):
        self.on_hover = []

        self.error_template = None
        self.warning_template = None
        self.info_template = None
        self.css = None

        self.settings.add_on_change("reload", lambda: self.load())
        self.load()

    def load(self):
        """Load Vale's settings.
        """
        self.settings = sublime.load_settings(self.settings_file)
        self.__load_resources()

    def is_supported(self, syntax):
        """Determine if `syntax` has been specified in the settings.
        """
        supported = self.get("vale_syntaxes")
        return any(s.lower() in syntax.lower() for s in supported)

    def get_styles(self):
        """Get Vale's base styles.
        """
        config = self.get_config()
        return config["GBaseStyles"]

    def get_draw_style(self):
        """Get the region styling.
        """
        underlined = sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE
        style = self.get("vale_alert_style")
        if style == "solid_underline":
            return sublime.DRAW_SOLID_UNDERLINE | underlined
        elif style == "stippled_underline":
            return sublime.DRAW_STIPPLED_UNDERLINE | underlined
        elif style == "squiggly_underline":
            return sublime.DRAW_SQUIGGLY_UNDERLINE | underlined
        return sublime.DRAW_OUTLINED

    def get_config(self):
        """Create a list of settings from the vale binary.
        """
        return query("config")

    def put(self, setting, value):
        """Store and save `setting` as `value`.

        Args:
            setting (str): The name of the setting to be accessed.
            value (str, int, bool): The value to be stored.
        """
        self.settings.set(setting, value)
        sublime.save_settings(self.settings_file)

    def get(self, setting):
        """Return the value associated with `setting`.

        Args:
            setting (str): The name of the setting to be accessed.

        Returns:
            (str, int, bool): The value associated with `setting`. The default
                value is ''.
        """
        return self.settings.get(setting, "")

    def clear_on_hover(self):
        """Clear Vale's regions and hover data.
        """
        for alert in self.on_hover:
            for level in ["error", "warning", "suggestion"]:
                sublime.View(alert["view_id"]).erase_regions(
                    "vale-server-" + level
                )
        del self.on_hover[:]

    def __load_resources(self):
        """Load Vale's static resources.
        """
        self.error_template = sublime.load_resource(
            self.settings.get("vale_error_template")
        )
        self.warning_template = sublime.load_resource(
            self.settings.get("vale_warning_template")
        )
        self.info_template = sublime.load_resource(
            self.settings.get("vale_info_template")
        )
        self.css = sublime.load_resource(self.settings.get("vale_css"))


class ValeDashboardCommand(sublime_plugin.WindowCommand):
    """Opens the Vale Server dashboard.

    TODO: Get port from application?
    """

    def run(self):
        webbrowser.open("http://localhost:7777")


class ValeEditStylesCommand(sublime_plugin.WindowCommand):
    """Provides quick access to styles on a view-specific basis.
    """

    styles = []

    def run(self):
        """Show a list of all styles applied to the active view.
        """
        styles_dir = os.path.dirname(self.window.active_view().file_name())
        config = Settings.get_config()
        path = config["StylesPath"]
        if not path or not os.path.exists(path):
            debug("invalid path!")
            return

        styles = []
        for s in os.listdir(path):
            style = os.path.join(path, s)
            if s == "Vocab" or not os.path.isdir(style):
                continue
            self.styles.append(style)
            styles.append(s)
        self.window.show_quick_panel(styles, self.choose_rule)

    def choose_rule(self, idx):
        """Show a list of all rules in the user-selected style.
        """
        if idx == -1:
            return  # The panel was cancelled.
        d = self.styles[idx]
        rules = [x for x in os.listdir(d) if x.endswith(".yml")]
        open_rule = (
            lambda i: None
            if i == -1
            else self.window.open_file(os.path.join(d, rules[i]))
        )
        self.window.show_quick_panel(rules, open_rule)


class ValeCommand(sublime_plugin.TextCommand):
    """Manages Vale's linting functionality.
    """

    def is_enabled(self):
        syntax = self.view.settings().get("syntax")
        return Settings.is_supported(syntax)

    def run(self, edit):
        """Run vale on the user-indicated buffer.
        """
        path = self.view.file_name()
        if not path or self.view.is_scratch():
            debug("invalid path: {0}!".format(path))
            return

        _, ext = os.path.splitext(path)
        buf = self.view.substr(sublime.Region(0, self.view.size()))

        try:
            server = urllib.parse.urljoin(Settings.get("vale_server"), "vale")
            debug("running vale ({0}) on {1}".format(
                server,
                self.view.settings().get("syntax")
            ))
            r = requests.post(server, data={
                "format": ext,
                "text": buf,
                "path": os.path.dirname(path)
            })
            if r.status_code != 200:
                return
        except requests.exceptions.RequestException as e:
            debug(e)
            return

        self.show_alerts(r.json())

    def show_alerts(self, data):
        """Add alert regions to the view.
        """
        Settings.clear_on_hover()

        regions = {"suggestion": [], "warning": [], "error": []}
        level_to_scope = {
            "error": "region.redish",
            "warning": "region.orangish",
            "suggestion": "region.bluish"
        }

        for f, alerts in data.items():
            for a in alerts:
                start = self.view.text_point(a["Line"] - 1, 0)
                loc = (start + a["Span"][0] - 1, start + a["Span"][1])

                region = sublime.Region(*loc)

                regions[a["Severity"]].append(region)
                Settings.on_hover.append(
                    {
                        "region": region,
                        "HTML": self._make_content(a),
                        "view_id": self.view.id(),
                        "level": a["Severity"],
                        "msg": a["Message"],
                    }
                )

        for level in ["error", "warning", "suggestion"]:
            self.view.add_regions(
                "vale-server-" + level,
                regions[level],
                level_to_scope[level],
                "circle",
                Settings.get_draw_style(),
            )

    def _make_content(self, alert):
        """Convert an alert into HTML suitable for a popup.
        """
        actions = []

        style, rule = alert["Check"].split(".")
        path = query("path")["path"]

        loc = os.path.join(path, style, rule) + ".yml"
        if os.path.exists(loc):
            actions.append(make_link(loc, "Edit rule"))

        if "Action" in alert and alert["Action"]["Name"] != "":
            stringify = json.dumps(alert, separators=(",", ":")).strip()
            stringify = binascii.hexlify(stringify.encode()).decode()
            actions.append(make_link(stringify, "Fix Alert"))

        level = alert["Severity"].capitalize()
        if level == "Error":
            html = Settings.error_template
        elif level == "Warning":
            html = Settings.warning_template
        else:
            html = Settings.info_template

        source = alert["Link"]
        if source != "":
            actions.append(make_link(source, "Read more"))

        if alert["Description"] == "":
            title = "{} - {}".format(level, alert["Check"])
            body = alert["Message"]
        else:
            title = "{}: {}".format(level, alert["Message"])
            body = alert["Description"]

        return html.format(
            CSS=Settings.css,
            header=title,
            body=body,
            actions=" | ".join(actions))


class ValeEventListener(sublime_plugin.EventListener):
    """Monitors events related to Vale.
    """

    def is_enabled(self):
        syntax = self.view.settings().get("syntax")
        return Settings.is_supported(syntax)

    def on_modified_async(self, view):
        Settings.clear_on_hover()
        if Settings.get("vale_mode") == "background":
            debug("running vale on modified")
            view.run_command("vale")

    def on_activated_async(self, view):
        if Settings.get("vale_mode") == "load_and_save":
            debug("running vale on activated")
            view.run_command("vale")

    def on_pre_save_async(self, view):
        if Settings.get("vale_mode") in ("load_and_save", "save"):
            debug("running vale on pre save")
            view.run_command("vale")

    def on_hover(self, view, point, hover_zone):
        loc = Settings.get("vale_alert_location")
        for alert in Settings.on_hover:
            region = alert["region"]
            if alert["view_id"] == view.id() and region.contains(point):
                if loc == "hover_popup":
                    view.show_popup(
                        alert["HTML"],
                        flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                        location=point,
                        on_navigate=handle_navigation,
                        max_width=Settings.get("vale_popup_width"),
                    )
                elif loc == "hover_status_bar":
                    sublime.status_message(
                        "vale:{0}:{1}".format(alert["level"], alert["msg"])
                    )


def plugin_loaded():
    """Load plugin settings and resources.
    """
    global Settings
    Settings = ValeSettings()
