# Copyright (C) 2019-2022 Intel Corporation
#
# SPDX-License-Identifier: MIT

from typing import Iterable, List, Optional
import argparse
import logging as log
import textwrap

from tqdm import tqdm

from datumaro.components.converter import (
    AnnotationExportErrorAction, ExportErrorPolicy, ItemExportErrorAction,
)
from datumaro.components.extractor import (
    ImportErrorPolicy, ItemImportErrorAction,
)
from datumaro.components.progress_reporting import ProgressReporter


def add_subparser(subparsers, name, builder):
    return builder(lambda **kwargs: subparsers.add_parser(name, **kwargs))

class MultilineFormatter(argparse.HelpFormatter):
    """
    Keeps line breaks introduced with '|n' separator
    and spaces introduced with '|s'.
    """

    def __init__(self, keep_natural=False, **kwargs):
        super().__init__(**kwargs)
        self._keep_natural = keep_natural

    def _fill_text(self, text, width, indent):
        text = self._whitespace_matcher.sub(' ', text).strip()
        text = text.replace('|s', ' ')

        paragraphs = text.split('|n ')
        if self._keep_natural:
            paragraphs = sum((p.split('\n ') for p in paragraphs), [])

        multiline_text = ''
        for paragraph in paragraphs:
            formatted_paragraph = textwrap.fill(paragraph, width,
                initial_indent=indent, subsequent_indent=indent) + '\n'
            multiline_text += formatted_paragraph
        return multiline_text

def required_count(nmin=0, nmax=0):
    assert 0 <= nmin and 0 <= nmax and nmin or nmax

    class RequiredCount(argparse.Action):
        def __call__(self, parser, args, values, option_string=None):
            k = len(values)
            if not ((nmin and (nmin <= k) or not nmin) and \
                    (nmax and (k <= nmax) or not nmax)):
                msg = "Argument '%s' requires" % self.dest
                if nmin and nmax:
                    msg += " from %s to %s arguments" % (nmin, nmax)
                elif nmin:
                    msg += " at least %s arguments" % nmin
                else:
                    msg += " no more %s arguments" % nmax
                raise argparse.ArgumentTypeError(msg)
            setattr(args, self.dest, values)
    return RequiredCount

def at_least(n):
    return required_count(n, 0)

def join_cli_args(args: argparse.Namespace, *names: Iterable[str]) -> List:
    "Merges arg values in a list"

    joined = []

    for name in names:
        value = getattr(args, name)
        if not isinstance(value, list):
            value = [value]
        joined += value

    return joined

def show_video_import_warning():
    log.warning("Using 'video_frames' in a project may lead "
        "to different results across multiple runs, if the "
        "system setup changes (library version, OS, etc.). "
        "If you need stable results, consider splitting the video "
        "manually using instructions at: "
        "https://openvinotoolkit.github.io/datumaro/docs/user-manual/media_formats/")

class CliProgressReporter(ProgressReporter):
    def __init__(self):
        self._tqdm = None

    def start(self, total: int, *, desc: Optional[str] = None):
        self._tqdm = tqdm(total=total, desc=desc, leave=False)

    def finish(self):
        if self._tqdm is not None:
            self._tqdm.close()

    def report_status(self, progress: int):
        diff = progress - self._tqdm.n
        if diff:
            self._tqdm.update(diff)

    def get_frequency(self) -> float:
        return 0.001

class RelaxedImportErrorPolicy(ImportErrorPolicy):
    def report_item_error(self, error):
        log.warning('Failed to import item: %s', error)
        return ItemImportErrorAction.skip_item

    def report_annotation_error(self, error):
        log.warning('Failed to import annotation: %s', error)
        return ItemImportErrorAction.skip

class RelaxedExportErrorPolicy(ExportErrorPolicy):
    def report_item_error(self, error):
        log.warning('Failed to export item: %s', error)
        return ItemExportErrorAction.skip_item

    def report_annotation_error(self, error):
        log.warning('Failed to export annotation: %s', error)
        return AnnotationExportErrorAction.skip_annotation
