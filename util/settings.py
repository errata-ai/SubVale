import json
import shutil
import subprocess

import sublime

SUPPORTED = [
    'HTML', 'Markdown', 'Plain Text', 'Markdown GFM', 'reStructuredText',
    'reStructuredText Improved', 'Asciidoc', 'Asciidoc (AsciiDoctor)'
]


class ValeSettings:
    """Provide global access to and management of Vale's settings.
    """
    def __init__(self):
        self.supported = SUPPORTED
        self.settings_file = 'SubVale.sublime-settings'
        self.default_binary = 'vale'
        if sublime.platform() == 'windows':
            self.default_binary += '.exe'
        self.settings = {}
        self.on_hover = []

    def load(self):
        """Load vale's settings.
        """
        self.settings = sublime.load_settings(self.settings_file)
        self.settings.add_on_change('reload', lambda: self.load())

    def vale_exists(self):
        """Determine if the vale binary exists.

        Returns:
            bool: True if the check was successful and False otherwise.
        """
        msg = 'The vale binary was not found. Do you want to set a new path?'
        # If we couldn't find the binary.
        if shutil.which(self.get('binary')) is None:
            # Try to guess the correct setting.
            path = shutil.which(self.default_binary)
            if path:
                # Looks like vale is in the path, remember that.
                self.set('binary', path)
            elif sublime.ok_cancel_dialog(msg):
                self._update_binary_path()
            return shutil.which(self.get('binary'))
        return True

    def get_styles(self):
        """Get Vale's base styles.
        """
        config = self._get_config()
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

    def _get_config(self):
        """Create a list of settings from the vale binary.
        """
        if not self.vale_exists():
            return {}

        binary = self.get('binary')
        startupinfo = None
        if sublime.platform() == 'windows':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        command = [binary, 'dump-config']
        p = subprocess.Popen(command, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             startupinfo=startupinfo)
        output, error = p.communicate()

        return json.loads(output.decode('utf-8'))

    def _update_binary_path(self):
        """Update the path to the vale binary.
        """
        w = sublime.active_window()
        caption = 'Path to vale: '
        on_done = lambda path: self.set('binary', path)
        w.show_input_panel(caption, self.get('binary'), on_done, None, None)

    def set(self, setting, value):
        """Store and save `setting` as `value`.

        Args:
            setting (str): The name of the setting to be accessed.
            value (str, int, bool): The value to be stored.
        """
        self.settings.set(setting, value)
        f = self.settings_file
        sublime.save_settings(f)

    def get(self, setting):
        """Return the value associated with `setting`.

        Args:
            setting (str): The name of the setting to be accessed.

        Returns:
            (str, int, bool): The value associated with `setting`. The default
                value is None.
        """
        return self.settings.get(setting, None)

    def clear_on_hover(self):
        """
        """
        del self.on_hover[:]

Settings = ValeSettings()
