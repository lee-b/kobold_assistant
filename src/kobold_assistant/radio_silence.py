import os


class FakeSilence:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        pass

    def __exit__(self, *_):
        pass


class RadioSilence:
    """
    Adapted further from https://stackoverflow.com/a/67962563 for kobold-assistant.

    PyAudio is noisy af every time you initialise it, which makes reading the
    log output rather difficult.  The output appears to be being made by the
    C internals, so I can't even redirect the logs with Python's logging
    facility.  Therefore the nuclear option was selected: swallow all stderr
    and stdout for the duration of PyAudio's use.

    Lifted and adapted from StackOverflow:
      https://stackoverflow.com/questions/11130156/

    """

    def __init__(self, stderr=True, stdout=False):
        self.silence_stdout = stdout
        self.silence_stderr = stderr

        if self.silence_stdout:
            self.stdout_null_fd = os.open(os.devnull, os.O_RDWR)
            self.stdout_save_fd = os.dup(1)

        if self.silence_stderr:
            self.stderr_null_fd = os.open(os.devnull, os.O_RDWR)
            self.stderr_save_fd = os.dup(2)


    def __enter__(self):
        if self.silence_stdout:
            os.dup2(self.stdout_null_fd, 1)

        if self.silence_stderr:
            os.dup2(self.stderr_null_fd, 2)


    def __exit__(self, *_):
        fds_to_close = []

        # Re-assign the real fds back
        if self.silence_stdout:
            os.dup2(self.stdout_save_fd, 1)
            fds_to_close.append(self.stdout_null_fd)
            fds_to_close.append(self.stdout_save_fd)

        if self.silence_stderr:
            os.dup2(self.stderr_save_fd, 2)
            fds_to_close.append(self.stderr_null_fd)
            fds_to_close.append(self.stderr_save_fd)

        for fd in fds_to_close:
            os.close(fd)
