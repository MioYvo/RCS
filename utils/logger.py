#
# Copyright 2012 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""Logging support for Tornado.

Tornado uses three logger streams:

* ``tornado.access``: Per-request logging for Tornado's HTTP servers (and
  potentially other servers in the future)
* ``tornado.application``: Logging of errors from application code (i.e.
  uncaught exceptions from callbacks)
* ``tornado.general``: General-purpose logging, including any errors
  or warnings from Tornado itself.

These streams may be configured independently using the standard library's
`logging` module.  For example, you may wish to send ``tornado.access`` logs
to a separate file for analysis.
"""
import logging
import logging.handlers
import sys

from utils.escape import _unicode, unicode_type, basestring_type

try:
    import colorama  # type: ignore
except ImportError:
    colorama = None

try:
    import curses
except ImportError:
    curses = None  # type: ignore

from typing import Dict, Any, cast, Optional

# Logger objects for internal tornado use
access_log = logging.getLogger("tornado.access")
app_log = logging.getLogger("tornado.application")
gen_log = logging.getLogger("tornado.general")


def _stderr_supports_color() -> bool:
    try:
        if hasattr(sys.stderr, "isatty") and sys.stderr.isatty():
            if curses:
                curses.setupterm()
                if curses.tigetnum("colors") > 0:
                    return True
            elif colorama:
                if sys.stderr is getattr(
                    colorama.initialise, "wrapped_stderr", object()
                ):
                    return True
    except Exception:
        # Very broad exception handling because it's always better to
        # fall back to non-colored logs than to break at startup.
        pass
    return False


def _safe_unicode(s: Any) -> str:
    try:
        return _unicode(s)
    except UnicodeDecodeError:
        return repr(s)


DEFAULT_FORMAT = "%(color)s[%(asctime)s %(module)s:%(lineno)d %(levelname)1.1s]%(end_color)s %(message)s"  # noqa: E501
DEFAULT_DATE_FORMAT = "%Y%m%d %H:%M:%S"
DEFAULT_COLORS = {
    logging.DEBUG: 4,  # Blue
    logging.INFO: 2,  # Green
    logging.WARNING: 3,  # Yellow
    logging.ERROR: 1,  # Red
    logging.CRITICAL: 5,  # Magenta
}


class LogFormatter(logging.Formatter):
    """Log formatter used in Tornado.

    Key features of this formatter are:

    * Color support when logging to a terminal that supports it.
    * Timestamps on every log line.
    * Robust against str/bytes encoding problems.

    This formatter is enabled automatically by
    `tornado.options.parse_command_line` or `tornado.options.parse_config_file`
    (unless ``--logging=none`` is used).

    Color support on Windows versions that do not support ANSI color codes is
    enabled by use of the colorama__ library. Applications that wish to use
    this must first initialize colorama with a call to ``colorama.init``.
    See the colorama documentation for details.

    __ https://pypi.python.org/pypi/colorama

    .. versionchanged:: 4.5
       Added support for ``colorama``. Changed the constructor
       signature to be compatible with `logging.config.dictConfig`.
    """
    def __init__(
        self,
        fmt: str = DEFAULT_FORMAT,
        datefmt: str = DEFAULT_DATE_FORMAT,
        style: str = "%",
        color: bool = True,
        colors: Dict[int, int] = None,
    ) -> None:
        r"""
        :arg bool color: Enables color support.
        :arg str fmt: Log message format.
          It will be applied to the attributes dict of log records. The
          text between ``%(color)s`` and ``%(end_color)s`` will be colored
          depending on the level if color support is on.
        :arg dict colors: color mappings from logging level to terminal color
          code
        :arg str datefmt: Datetime format.
          Used for formatting ``(asctime)`` placeholder in ``prefix_fmt``.

        .. versionchanged:: 3.2

           Added ``fmt`` and ``datefmt`` arguments.
        """
        colors = colors or DEFAULT_COLORS
        logging.Formatter.__init__(self, datefmt=datefmt)
        self._fmt = fmt

        self._colors = {}  # type: Dict[int, str]
        if color and _stderr_supports_color():
            if curses is not None:
                fg_color = curses.tigetstr("setaf") or curses.tigetstr("setf") or b""

                for levelno, code in colors.items():
                    # Convert the terminal control characters from
                    # bytes to unicode strings for easier use with the
                    # logging module.
                    self._colors[levelno] = unicode_type(
                        curses.tparm(fg_color, code), "ascii"
                    )
                self._normal = unicode_type(curses.tigetstr("sgr0"), "ascii")
            else:
                # If curses is not present (currently we'll only get here for
                # colorama on windows), assume hard-coded ANSI color codes.
                for levelno, code in colors.items():
                    self._colors[levelno] = "\033[2;3%dm" % code
                self._normal = "\033[0m"
        else:
            self._normal = ""

    def format(self, record: Any) -> str:
        try:
            message = record.getMessage()
            assert isinstance(message, basestring_type)  # guaranteed by logging
            # Encoding notes:  The logging module prefers to work with character
            # strings, but only enforces that log messages are instances of
            # basestring.  In python 2, non-ascii bytestrings will make
            # their way through the logging framework until they blow up with
            # an unhelpful decoding error (with this formatter it happens
            # when we attach the prefix, but there are other opportunities for
            # exceptions further along in the framework).
            #
            # If a byte string makes it this far, convert it to unicode to
            # ensure it will make it out to the logs.  Use repr() as a fallback
            # to ensure that all byte strings can be converted successfully,
            # but don't do it by default so we don't add extra quotes to ascii
            # bytestrings.  This is a bit of a hacky place to do this, but
            # it's worth it since the encoding errors that would otherwise
            # result are so useless (and tornado is fond of using utf8-encoded
            # byte strings wherever possible).
            record.message = _safe_unicode(message)
        except Exception as e:
            record.message = "Bad message (%r): %r" % (e, record.__dict__)

        record.asctime = self.formatTime(record, cast(str, self.datefmt))

        if record.levelno in self._colors:
            record.color = self._colors[record.levelno]
            record.end_color = self._normal
        else:
            record.color = record.end_color = ""

        formatted = self._fmt % record.__dict__

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            # exc_text contains multiple lines.  We need to _safe_unicode
            # each line separately so that non-utf8 bytes don't cause
            # all the newlines to turn into '\n'.
            lines = [formatted.rstrip()]
            lines.extend(_safe_unicode(ln) for ln in record.exc_text.split("\n"))
            formatted = "\n".join(lines)
        return formatted.replace("\n", "\n    ")


def enable_pretty_logging(logging_="INFO",
                          log_file_prefix='',
                          log_rotate_mode='size',
                          log_file_max_size=100 * 1000 * 1000,
                          log_file_num_backups=10,
                          log_rotate_when='midnight',
                          log_rotate_interval=1,
                          log_to_stderr=None,

                          logger: Optional[logging.Logger] = None) -> None:
    """Turns on formatted logging output as configured.

    This is called automatically by `tornado.options.parse_command_line`
    and `tornado.options.parse_config_file`.
    """
    if logging_ is None or logging_.lower() == "none":
        return
    if logger is None:
        logger = logging.getLogger()
    logger.setLevel(getattr(logging, logging_.upper()))
    if log_file_prefix:
        rotate_mode = log_rotate_mode
        if rotate_mode == "size":
            channel: logging.Handler = logging.handlers.RotatingFileHandler(
                filename=log_file_prefix,
                maxBytes=log_file_max_size,
                backupCount=log_file_num_backups,
                encoding="utf-8",
            )
        elif rotate_mode == "time":
            channel: logging.Handler = logging.handlers.TimedRotatingFileHandler(
                filename=log_file_prefix,
                when=log_rotate_when,
                interval=log_rotate_interval,
                backupCount=log_file_num_backups,
                encoding="utf-8",
            )
        else:
            error_message = (
                "The value of log_rotate_mode option should be "
                + '"size" or "time", not "%s".' % rotate_mode
            )
            raise ValueError(error_message)
        channel.setFormatter(LogFormatter(color=False))
        logger.addHandler(channel)

    if log_to_stderr or (log_to_stderr is None and not logger.handlers):
        # Set up color if we are in a tty and curses is installed
        channel = logging.StreamHandler()
        channel.setFormatter(LogFormatter())
        logger.addHandler(channel)


class Logger:
    def __init__(self, name='', extra_prefix=''):
        self.name = name
        self.extra_prefix = extra_prefix

    def _log_str(self, msg_tuple: tuple, kwargs: dict):
        _s = f'{self.name}:{self.extra_prefix}:{",".join(map(str, msg_tuple))}:' \
             f'{",".join(map(lambda k: f"{k[0]}:{k[1]}", kwargs.items()))}'
        return _s.strip(':')

    def info(self, *msg, **kwargs):
        logging.info(self._log_str(msg, kwargs))

    def error(self, *msg, exc_info=False, **kwargs):
        logging.error(self._log_str(msg, kwargs), exc_info=exc_info)

    def exceptions(self, *msg, **kwargs):
        self.error(*msg, exc_info=True, **kwargs)

    def warning(self, *msg, **kwargs):
        logging.warning(self._log_str(msg, kwargs))
