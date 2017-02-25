import sublime
import sublime_plugin

from .util import *

Settings = None


def plugin_loaded():
    """Load plugin settings and resources.
    """
    global Settings
    Settings = ValeSettings()
    Settings.load(resources=True)


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
        if not Settings.is_supported(view.settings().get('syntax')):
            return
        Settings.clear_on_hover()
        if Settings.get('mode') == 'background':
            print('Auto-applying Vale in background...')
            view.run_command('vale')

    def on_activated_async(self, view):
        if not Settings.is_supported(view.settings().get('syntax')):
            return
        elif Settings.get('mode') == 'load_and_save':
            print('Auto-applying Vale on load...')
            view.run_command('vale')

    def on_pre_save_async(self, view):
        if not Settings.is_supported(view.settings().get('syntax')):
            return
        elif Settings.get('mode') in ('load_and_save', 'save'):
            print('Auto-applying Vale on save...')
            view.run_command('vale')

    def on_hover(self, view, point, hover_zone):
        if not Settings.is_supported(view.settings().get('syntax')):
            return
        loc = Settings.get('alert_location')
        for alert in Settings.on_hover:
            region = alert['region']
            if alert['view_id'] == view.id() and region.contains(point):
                if loc == 'hover_popup':
                    view.show_popup(
                        alert['HTML'], flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
                        location=point, max_width=450,
                        on_navigate=open_link)
                elif loc == 'hover_status_bar':
                    sublime.status_message(
                        'vale:{0}:{1}'.format(alert['level'], alert['msg']))
