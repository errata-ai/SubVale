import os
import subprocess
import tempfile
import webbrowser

import sublime

from .settings import Settings


def open_link(url):
    """
    """
    webbrowser.open(url)


def make_link(url, linkText='{url}'):
    """Returns a link HTML string.
    """
    template = '<a href={url}>' + linkText + '</a>'
    return template.format(url=url)


def pipe_through_prog(cmd, content, filename):
    """
    """
    try:
        _, ext = os.path.splitext(filename)
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
            f.write(content)
            f.flush()
            startupinfo = None
            if sublime.platform() == 'windows':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            p = subprocess.Popen(cmd, cwd=os.path.dirname(filename),
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 stdin=subprocess.PIPE,
                                 startupinfo=startupinfo)
            return p.communicate()
    finally:
        os.remove(f.name)


def get_is_supported(syntax_path):
    """Determine if the current syntax is supported.

    Returns:
        (str, bool): The matching syntax if it's supported and False otherwise.
    """
    return any(s in syntax_path for s in Settings.supported)


def get_syntax(syntax_path):
    """Return the name of the current syntax.

    Returns:
        (str, None): The name of the syntax is it's supported; None otherwise.
    """
    if not get_is_supported(syntax_path):
        return None
    possible = []
    syntax = syntax_path.split("/")[-1].split('.')[0]
    for s in Settings.supported:
        if all(i in syntax for i in s):
            possible.append(s)
    return max(possible, key=len)
