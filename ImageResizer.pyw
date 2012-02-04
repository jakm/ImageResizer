#!/usr/bin/env python
# -*- coding: utf8 -*-

import os
import sys

import ImageResizer

if __name__ == '__main__':
    os.chdir(os.path.dirname(sys.argv[0]))
    
    app = ImageResizer.ImageResizer()
    app.main()
