#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProgressBar class
"""

import shutil

class ProgressBar:
    
    def __init__(self, maximum):
        """ Make ProgressBar object
        
            Parameters
            ----------
            maximum : float
                Max value
        """
        self.mx = maximum
        try:
            # get width of terminal
            width = shutil.get_terminal_size().columns
            # width of progress bar
            # 9 characters are needed for percentage etc.
            self.width = int(width)-9
            self.show_bar = True
        except ValueError:
            # if we can't get terminal size, show only the percentage
            self.show_bar = False
        self.progress(0)
        
    def progress(self, value):
        """ Update the progress bar
        
            Parameters
            ----------
            value : float
                Progress value
        """
        # calculate percentage progress
        p = value/self.mx
        show = '{:5.1f}%'.format(100*p)
        
        # make bar, if required
        if self.show_bar:
            progress = int(self.width*p)
            remaining = self.width-progress
            show += ' [' + '#'*progress + '-'*remaining + ']'
        
        # set line ending to either carriage return or new line
        if p < 1:
            end = '\r'
        else:
            end = '\n'
            
        print(show, end=end, flush=True)
        