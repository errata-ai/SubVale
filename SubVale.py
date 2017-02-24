import json

import sublime_plugin
import sublime

from .util.settings import Settings
from .util import util


def plugin_loaded():
    """Load plugin settings and resources.
    """
    Settings.load()
    Settings.load_resources()


class ValeCommand(sublime_plugin.TextCommand):
    """Manages Vale's linting functionality.
    """
    def run(self, edit):
        """Run vale on the user-indicated buffer.
        """
        syntax = self.view.settings().get('syntax')

        # Verify that the binary exists and that the syntax is supported.
        if not Settings.vale_exists():
            print('The vale binary was not found.')
            return
        elif not util.get_is_supported(syntax):
            print('Syntax not supported; skipping...')
            return

        encoding = self.view.encoding()
        if encoding == 'Undefined':
            encoding = 'utf-8'

        path = self.view.file_name()
        cmd = [Settings.get('binary'), '--output=JSON', path]
        buf = self.view.substr(sublime.Region(0, self.view.size()))
        output, error = util.pipe_through_prog(cmd, buf.encode(encoding), path)
        if error:
            sublime.error_message('Vale: ' + error.decode('utf-8'))
            return
        self.show_alerts(json.loads(output.decode(encoding)))

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
                    'view': self.view.id, 'level': a['Severity'],
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
            source = util.make_link(source, 'Read more ...')

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
    """Monitors event related to Vale.
    """
    def on_modified_async(self, view):
        """Clear the view of Vale's regions.
        """
        Settings.clear_on_hover()
        view.erase_regions('Vale Alerts')

    def on_pre_save_async(self, view):
        """Run Vale on the entire buffer on file save.
        """
        syntax = view.settings().get('syntax')
        if util.get_is_supported(syntax):
            if Settings.get('format_on_save'):
                print('Auto-applying Vale on save...')
                view.run_command('vale')

    def on_hover(self, view, point, hover_zone):
        """Show an alert.
        """
        if not util.get_is_supported(view.settings().get('syntax')):
            return

        loc = Settings.get('alert_location')
        for alert in Settings.on_hover:
            if alert['view'] == view.id and alert['region'].contains(point):
                if loc == 'hover_popup':
                    view.show_popup(
                        alert['HTML'], flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                        location=point, max_width=450,
                        on_navigate=util.open_link)
                elif loc == 'hover_status_bar':
                    sublime.status_message(
                        'vale:{0}:{1}'.format(alert['level'], alert['msg']))
