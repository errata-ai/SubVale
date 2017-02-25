import json
import os
import shutil
import subprocess
import tempfile
import webbrowser

import sublime
import sublime_plugin

Settings = None


def make_link(url, linkText='{url}'):
    """Returns a link HTML string.
    """
    template = '<a href={url}>' + linkText + '</a>'
    return template.format(url=url)


def pipe_through_prog(cmd, path=None):
    """Run the Vale binary with the given command.
    """
    startupinfo = None
    if sublime.platform() == 'windows':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    p = subprocess.Popen(cmd, cwd=path, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         stdin=subprocess.PIPE,
                         startupinfo=startupinfo)
    return p.communicate()


def run_on_temp(cmd, content, filename, encoding):
    """Create a named temporary file and run Vale on it.
    """
    try:
        _, ext = os.path.splitext(filename)
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(content.encode('utf-8'))
            f.flush()
            out, err = pipe_through_prog(cmd, os.path.dirname(filename))
            return json.loads(out.decode('utf-8')), err
    finally:
        os.remove(f.name)


class ValeSettings:
    """Provide global access to and management of Vale's settings.
    """
    settings_file = 'SubVale.sublime-settings'

    def __init__(self):
        self.default_binary = 'vale'
        if sublime.platform() == 'windows':
            self.default_binary += '.exe'
        self.settings = {}
        self.on_hover = []
        self.error_template = None
        self.warning_template = None
        self.info_template = None
        self.css = None

    def load(self, resources=False):
        """Load Vale's settings.
        """
        self.settings = sublime.load_settings(self.settings_file)
        self.settings.add_on_change('reload', lambda: self.load())
        if resources:
            self.__load_resources()

    def is_supported(self, syntax):
        """Determine if `syntax` has been specified in the settings..
        """
        supported = self.get('syntaxes')
        return any(s.lower() in syntax.lower() for s in supported)

    def vale_exists(self):
        """Determine if the Vale binary exists.

        Returns:
            bool: True if the check was successful and False otherwise.
        """
        msg = 'The vale binary was not found. Do you want to set a new path?'
        # If we couldn't find the binary.
        if shutil.which(self.get('binary')) is None:
            # Try to guess the correct setting.
            path = shutil.which(self.default_binary)
            if path:
                self.set('binary', path)
            elif sublime.ok_cancel_dialog(msg):
                self.__update_binary_path()
            return shutil.which(self.get('binary'))
        return True

    def get_styles(self):
        """Get Vale's base styles.
        """
        config = self.get_config()
        return config['GBaseStyles']

    def get_draw_style(self):
        """Get the region styling.
        """
        underlined = sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE
        style = self.get('alert_style')
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
        command = [self.get('binary'), 'dump-config']
        output, error = pipe_through_prog(command, path)
        return json.loads(output.decode('utf-8'))

    def set(self, setting, value):
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

    def __update_binary_path(self):
        """Update the path Vale's binary.
        """
        w = sublime.active_window()
        caption = 'Path to vale: '
        on_done = lambda path: self.set('binary', path)
        w.show_input_panel(caption, self.get('binary'), on_done, None, None)

    def __load_resources(self):
        """Load Vale's static resources.
        """
        self.error_template = sublime.load_resource(
            'Packages/SubVale/static/error.html')
        self.warning_template = sublime.load_resource(
            'Packages/SubVale/static/warning.html')
        self.info_template = sublime.load_resource(
            'Packages/SubVale/static/info.html')
        self.css = sublime.load_resource('Packages/SubVale/static/ui.css')


class ValeEditStylesCommand(sublime_plugin.WindowCommand):
    """
    """
    styles = []

    def run(self):
        """Show a list of all styles applied to the active view.
        """
        styles_dir = os.path.dirname(self.window.active_view().file_name())
        config = Settings.get_config(path=styles_dir)
        path = config['StylesPath']
        if not path or not os.path.exists(path):
            sublime.error_message('SubVale: invalid path!')
            return

        styles = []
        for s in os.listdir(path):
            style = os.path.join(path, s)
            if not os.path.isdir(style):
                continue
            self.styles.append(style)
            styles.append(s)

        if len(styles) == 1:
            self.choose_rule(0)  # There's only one style; just show the rules.
        else:
            self.window.show_quick_panel(styles, self.choose_rule)

    def choose_rule(self, idx):
        """Show a list of all rules in the user-selected style.
        """
        d = self.styles[idx]
        rules = [x for x in os.listdir(d) if x.endswith('.yml')]
        open_rule = lambda i: self.window.open_file(os.path.join(d, rules[i]))
        self.window.show_quick_panel(rules, open_rule)


class ValeCommand(sublime_plugin.TextCommand):
    """Manages Vale's linting functionality.
    """
    def run(self, edit):
        """Run vale on the user-indicated buffer.
        """
        syntax = self.view.settings().get('syntax')
        path = self.view.file_name()

        if not Settings.vale_exists():
            return
        elif not Settings.is_supported(syntax):
            return
        elif not path or self.view.is_scratch():
            return

        encoding = self.view.encoding()
        if encoding == 'Undefined':
            encoding = 'utf-8'

        cmd = [Settings.get('binary'), '--output=JSON', path]
        buf = self.view.substr(sublime.Region(0, self.view.size()))
        output, error = run_on_temp(cmd, buf, path, encoding)
        if error:
            sublime.error_message('Vale: ' + error.decode('utf-8'))
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
                              Settings.get('highlight_scope'),
                              Settings.get('icon'),
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
    def on_modified_async(self, view):
        Settings.clear_on_hover()
        if Settings.get('mode') == 'background':
            view.run_command('vale')

    def on_activated_async(self, view):
        if Settings.get('mode') == 'load_and_save':
            view.run_command('vale')

    def on_pre_save_async(self, view):
        if Settings.get('mode') in ('load_and_save', 'save'):
            view.run_command('vale')

    def on_hover(self, view, point, hover_zone):
        loc = Settings.get('alert_location')
        for alert in Settings.on_hover:
            region = alert['region']
            if alert['view_id'] == view.id() and region.contains(point):
                if loc == 'hover_popup':
                    view.show_popup(
                        alert['HTML'], flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                        location=point, max_width=450,
                        on_navigate=webbrowser.open)
                elif loc == 'hover_status_bar':
                    sublime.status_message(
                        'vale:{0}:{1}'.format(alert['level'], alert['msg']))


def plugin_loaded():
    """Load plugin settings and resources.
    """
    global Settings
    Settings = ValeSettings()
    Settings.load(resources=True)
