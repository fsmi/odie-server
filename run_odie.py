#! /usr/bin/env python3

import os

import odie
import config
import routes

from odie import app


def init_upload_dir():
    dir = config.DOCUMENT_DIRECTORY
    if not os.path.isdir(dir):
        os.mkdir(dir)
    for x in range(0x100):
        p = os.path.join(dir, hex(x)[2:])
        if not os.path.isdir(p):
            os.mkdir(p)

if __name__ == '__main__':
    init_upload_dir()
    app.run()
