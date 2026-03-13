#!/usr/bin/env python3
"""Validator 3 — Run in Terminal 5: python subnet/validator3.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["VALIDATOR_ID"] = "3"
from subnet.validator_node import main
main()
