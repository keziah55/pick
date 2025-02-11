import shutil

class ProgressBar:
    """Simple ProgressBar object, going up to `maximum`"""

    def __init__(self, maximum):
        self.mx = maximum
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

    def progress(self, value):
        """Update the progress bar

        Parameters
        ----------
        value : float
            Progress value
        """
        # calculate percentage progress
        p = value / self.mx
        show = f"{p:6.1%}"

        # make bar, if required
        if self.show_bar:
            progress = int(self.width * p)
            remaining = self.width - progress
            show += " [" + "#" * progress + "-" * remaining + "]"

        # set line ending to either carriage return or new line
        end = "\r" if p < 1 else "\n"
        print(show, end=end, flush=True)