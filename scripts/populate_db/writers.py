from pathlib import Path
from abc import abstractmethod, ABC

from .progress_bar import ProgressBar, HtmlProgressBar


class BaseWriter(ABC):
    def __init__(self, quiet: bool = False):
        self._quiet = quiet
        self._progress = None

    def make_progress_bar(self, maximum):
        if not self._quiet:
            self._progress = self._make_progress_bar(maximum)

    @abstractmethod
    def _make_progress_bar(self, maximum):
        pass

    def update_progress(self, value):
        if self._progress is not None and not self._quiet:
            self._update_progress(value)

    @abstractmethod
    def _update_progress(self, value):
        pass

    def write(self, msg, *args, **kwargs):
        if not self._quiet:
            self._write(msg, *args, **kwargs)

    @abstractmethod
    def _write(self, msg, *args, **kwargs):
        pass


class StdoutWriter(BaseWriter):
    def _write(self, msg, *args, **kwargs):
        print(msg, *args, **kwargs)

    def _make_progress_bar(self, maximum):
        return ProgressBar(maximum, write_func=self.write)

    def _update_progress(self, value):
        self._progress.progress(value)


class HtmlWriter(BaseWriter):
    def __init__(self, out_dir: Path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        out_dir.mkdir(exist_ok=True, parents=True)
        self._html_path = out_dir.joinpath("index.html")

        self._html_header = """
<!DOCTYPE html>
<html>
<head>
<link rel="stylesheet" href="https://cdn.simplecss.org/simple.min.css">
</head>
"""

        self._html_footer = """
</html>
"""
        self._html_body = ""

    def _make_html_doc(self, body_end=""):
        return (
            self._html_header
            + "<body>\n"
            + self._html_body
            + body_end
            + "</body>\n"
            + self._html_footer
        )

    def _write(self, msg, tag="div"):
        self._html_body += f"<{tag}>{msg}</tag>"

        html = self._make_html_doc()

        with open(self._html_path, "w") as fileobj:
            fileobj.write(html)

    def _make_progress_bar(self, maximum):
        return HtmlProgressBar(maximum)

    def _update_progress(self, value):
        s = self._progress.progress(value)

        if self._progress.complete:
            self._html_body += s
            html = self._make_html_doc()
        else:
            html = self._make_html_doc(body_end=s)

        with open(self._html_path, "w") as fileobj:
            fileobj.write(html)
