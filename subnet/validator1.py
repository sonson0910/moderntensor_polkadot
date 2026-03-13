#!/usr/bin/env python3
"""Validator 1 — Run in Terminal 3: python subnet/validator1.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["VALIDATOR_ID"] = "1"
from subnet.validator_node import main
main()
