import json
import os
import shutil
import subprocess
import tempfile
import webbrowser

import sublime


def open_link(url):
    """Open url in the default browser.
    """
    webbrowser.open(url)


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
