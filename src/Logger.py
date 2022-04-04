#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""Log.py: A helper for printing info
"""
LOG_LEVEL = 3

"""
    DEBUG       = 4
    INFO        = 3
    CRITICAL    = 2
    ERROR       = 1
"""


HEADER = '\033[95m'
OKBLUE = '\033[94m'
OKCYAN = '\033[96m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'


def DEBUG(message):
    if LOG_LEVEL >= 4:
        print (OKBLUE + "DEBUG: "+str(message)+"\n" + ENDC)

def INFO(message):
    if LOG_LEVEL >= 3:
        print (HEADER+ "INFO: "+str(message)+"\n" + ENDC)

def CRITICAL(message):
    if LOG_LEVEL >= 2:
        print (WARNING + "CRITICAL: "+str(message)+"\n" + ENDC)

def ERROR(message):
    if LOG_LEVEL >= 1:
        print (FAIL + "ERROR: "+str(message)+"\n"+ ENDC)