#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
from typing import Optional

from .media_info import MediaInfoProcessor
from .mixins import PopulateDBVisionItemMixin, PopulateDBVisionSeriesMixin
from .writers import StdoutWriter, BaseWriter
from .logger import initialise_logging

from mediabrowser.models import VisionItem

logger = initialise_logging()


class PopulateDatabase(PopulateDBVisionItemMixin, PopulateDBVisionSeriesMixin):
    """Class to create records in database from list of file names and/or csv file."""

    def __init__(
        self,
        quiet=False,
        physical_media: Optional[Path] = None,
        alias_csv: Optional[Path] = None,
        database="default",
        writer: Optional[BaseWriter] = None,
    ):
        if writer is None:
            self._writer = StdoutWriter(quiet=quiet)
        else:
            self._writer = writer
        self._database = database
        super().__init__()

        self._quiet = quiet
        self._media_info_processor = MediaInfoProcessor(physical_media, alias_csv)

    def _write(self, s):
        self._writer.write(s)
        # if not self._quiet:
        # print(s)

    def clear(self, model=VisionItem):
        """Remove all entries from the given `model` table"""
        model.objects.using(self._database).delete()
        self._write("Cleared database")
