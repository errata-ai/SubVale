import json
import os
import subprocess
import webbrowser

import sublime
import sublime_plugin

Settings = None


def debug(message, prefix='SubVale', level='debug'):
    """Print a formatted console entry to the Sublime Text console.

    Args:
        message (string): A message to print to the console
        prefix (string): An optional prefix
        level (string): One of debug, info, warning, error [Default: debug]

    Returns:
        string: Issue a standard console print command.
    """
    if Settings.get('vale_debug'):
        print('{prefix}: [{level}] {message}'.format(
            message=message,
            prefix=prefix,
            level=level
        ))


def make_link(url, linkText='{url}'):
    """Return a link HTML string.
    """
    template = '<a href={url}>' + linkText + '</a>'
    return template.format(url=url)


def pipe_through_prog(cmd, path=None):
    """Run the Vale binary with the given command.
    """
    ret = None
    startupinfo = None
    if sublime.platform() == 'windows':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    p = subprocess.Popen(cmd, cwd=path, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         stdin=subprocess.PIPE,
                         startupinfo=startupinfo)
    out, err = p.communicate()
    try:
        ret = json.loads(out.decode('utf-8'))
    except ValueError as e:
        err = str(e)
    return ret, err


class ValeSettings(object):
    """Provide global access to and management of Vale's settings.
    """
    settings_file = 'SubVale.sublime-settings'
    settings = sublime.load_settings(settings_file)

    def __init__(self):
        self.default_binary = 'vale'
        if sublime.platform() == 'windows':
            self.default_binary += '.exe'
        self.on_hover = []
        self.error_template = None
        self.warning_template = None
        self.info_template = None
        self.css = None
        self.settings.add_on_change('reload', lambda: self.load())
        self.load()

    def load(self):
        """Load Vale's settings.
        """
        self.settings = sublime.load_settings(self.settings_file)
        self.__load_resources()

    def is_supported(self, syntax):
        """Determine if `syntax` has been specified in the settings.
        """
        supported = self.get('vale_syntaxes')
        return any(s.lower() in syntax.lower() for s in supported)

    def vale_exists(self):
        """Determine if the Vale binary exists.
        """
        return os.path.exists(self.get('vale_binary'))

    def get_styles(self):
        """Get Vale's base styles.
        """
        config = self.get_config()
        return config['GBaseStyles']

    def get_draw_style(self):
        """Get the region styling.
        """
        underlined = sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE
        style = self.get('vale_alert_style')
        if style == 'solid_underline':
            return sublime.DRAW_SOLID_UNDERLINE | underlined
        elif style == 'stippled_underline':
            return sublime.DRAW_STIPPLED_UNDERLINE | underlined
        elif style == 'squiggly_underline':
            return sublime.DRAW_SQUIGGLY_UNDERLINE | underlined
        return sublime.DRAW_OUTLINED

    def get_config(self, path):
        """Create a list of settings from the vale binary.
        """
        if not self.vale_exists():
            return {}
        command = [self.get('vale_binary'), 'dump-config']
        output, error = pipe_through_prog(command, path)
        return json.loads(output.decode('utf-8'))

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
        return self.settings.get(setting, '')

    def clear_on_hover(self):
        """Clear Vale's regions and hover data.
        """
        for alert in self.on_hover:
            sublime.View(alert['view_id']).erase_regions('Vale Alerts')
        del self.on_hover[:]

    def __load_resources(self):
        """Load Vale's static resources.
        """
        self.error_template = sublime.load_resource(
            self.settings.get('vale_error_template'))
        self.warning_template = sublime.load_resource(
            self.settings.get('vale_warning_template'))
        self.info_template = sublime.load_resource(
            self.settings.get('vale_info_template'))
        self.css = sublime.load_resource(self.settings.get('vale_css'))


class ValeEditStylesCommand(sublime_plugin.WindowCommand):
    """Provides quick access to styles on a view-specific basis.
    """
    styles = []

    def run(self):
        """Show a list of all styles applied to the active view.
        """
        styles_dir = os.path.dirname(self.window.active_view().file_name())
        config = Settings.get_config(path=styles_dir)
        path = config['StylesPath']
        if not path or not os.path.exists(path):
            debug('invalid path!')
            return

        styles = []
        for s in os.listdir(path):
            style = os.path.join(path, s)
            if not os.path.isdir(style):
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
        rules = [x for x in os.listdir(d) if x.endswith('.yml')]
        open_rule = lambda i: None if i == -1 else self.window.open_file(
            os.path.join(d, rules[i]))
        self.window.show_quick_panel(rules, open_rule)


class ValeCommand(sublime_plugin.TextCommand):
    """Manages Vale's linting functionality.
    """
    def is_enabled(self):
        syntax = self.view.settings().get('syntax')
        return Settings.is_supported(syntax)

    def run(self, edit):
        """Run vale on the user-indicated buffer.
        """
        path = self.view.file_name()

        if not Settings.vale_exists():
            debug('binary not found!')
            return
        elif not path or self.view.is_scratch():
            debug('invalid path!')
            return
        debug('running vale on {0}'.format(self.view.settings().get('syntax')))

        encoding = self.view.encoding()
        if encoding == 'Undefined':
            encoding = 'utf-8'

        cmd = [Settings.get('vale_binary'), '--output=JSON', path]
        output, error = pipe_through_prog(cmd, os.path.dirname(path))
        if error:
            debug(error)
            return
        self.show_alerts(output)

    def show_alerts(self, data):
        """Add alert regions to the view.
        """
        Settings.clear_on_hover()
        regions = []
        for f, alerts in data.items():
            for a in alerts:
                start = self.view.text_point(a['Line'] - 1, 0)
                loc = (start + a['Span'][0] - 1, start + a['Span'][1])
                regions.append(sublime.Region(*loc))
                Settings.on_hover.append({
                    'region': regions[-1], 'HTML': self._make_content(a),
                    'view_id': self.view.id(), 'level': a['Severity'],
                    'msg': a['Message']
                })
        self.view.add_regions('Vale Alerts', regions,
                              Settings.get('vale_highlight_scope'),
                              Settings.get('vale_icon'),
                              Settings.get_draw_style())

    def _make_content(self, alert):
        """Convert an alert into HTML suitable for a popup.
        """
        level = alert['Severity'].capitalize()
        if level == 'Error':
            html = Settings.error_template
        elif level == 'Warning':
            html = Settings.warning_template
        else:
            html = Settings.info_template

        source = alert['Link']
        if source != '':
            source = make_link(source, 'Read more ...')

        if alert['Description'] == '':
            title = '{}: {}'.format(level, alert['Check'])
            body = alert['Message']
        else:
            title = '{}: {}'.format(level, alert['Message'])
            body = alert['Description']

        content = html.format(
            CSS=Settings.css, header=title, body=body, source=source)
        return content


class ValeEventListener(sublime_plugin.EventListener):
    """Monitors events related to Vale.
    """
    def is_enabled(self):
        syntax = self.view.settings().get('syntax')
        return Settings.is_supported(syntax)

    def on_modified_async(self, view):
        Settings.clear_on_hover()
        if Settings.get('vale_mode') == 'background':
            debug('running vale on modified')
            view.run_command('vale')

    def on_activated_async(self, view):
        if Settings.get('vale_mode') == 'load_and_save':
            debug('running vale on activated')
            view.run_command('vale')

    def on_pre_save_async(self, view):
        if Settings.get('vale_mode') in ('load_and_save', 'save'):
            debug('running vale on pre save')
            view.run_command('vale')

    def on_hover(self, view, point, hover_zone):
        loc = Settings.get('vale_alert_location')
        for alert in Settings.on_hover:
            region = alert['region']
            if alert['view_id'] == view.id() and region.contains(point):
                if loc == 'hover_popup':
                    view.show_popup(
                        alert['HTML'], flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                        location=point, on_navigate=webbrowser.open,
                        max_width=Settings.get('vale_popup_width'))
                elif loc == 'hover_status_bar':
                    sublime.status_message(
                        'vale:{0}:{1}'.format(alert['level'], alert['msg']))


def plugin_loaded():
    """Load plugin settings and resources.
    """
    global Settings
    Settings = ValeSettings()
