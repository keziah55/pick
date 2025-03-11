import shutil
from abc import abstractmethod, ABC


class BaseProgressBar(ABC):
    def __init__(self, maximum: float):
        self._max = maximum

    @property
    def complete(self) -> bool:
        return self._complete

    def progress(self, value: float):
        """
        Update the progress bar.

        Parameters
        ----------
        value : float
            Progress value
        """
        self._complete = value >= self._max
        return self._progress(value)

    @abstractmethod
    def _progress(self, value: float):
        pass


class ProgressBar(BaseProgressBar):
    """Simple ProgressBar object, going up to `maximum`"""

    def __init__(self, maximum, write_func=None):
        super().__init__(maximum=maximum)
        self._write_func = write_func if write_func is not None else print

        try:
            # get width of terminal
            width = shutil.get_terminal_size().columns
            # width of progress bar
            # 9 characters are needed for percentage etc.
            self.width = int(width) - 9
            self.show_bar = True
        except ValueError:
            # if we can't get terminal size, show only the percentage
            self.show_bar = False
        self.progress(0)

    def _progress(self, value):

        # calculate percentage progress
        p = value / self._max
        show = f"{p:6.1%}"

        # make bar, if required
        if self.show_bar:
            progress = int(self.width * p)
            remaining = self.width - progress
            show += " [" + "#" * progress + "-" * remaining + "]"

        # set line ending to either carriage return or new line
        end = "\r" if p < 1 else "\n"
        self._write_func(show, end=end, flush=True)


class HtmlProgressBar(BaseProgressBar):

    def _progress(self, value):
        p = f"{100 * value / self._max:6.1f}"
        lines = [
            f'<label for="progress-bar">{p}%</label>'
            f'<progress id="progress-bar" max="100" value="{p}">{p}%</progress>'
        ]
        return "\n".join(lines)
