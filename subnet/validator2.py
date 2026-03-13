#!/usr/bin/env python3
"""Validator 2 — Run in Terminal 4: python subnet/validator2.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["VALIDATOR_ID"] = "2"
from subnet.validator_node import main
main()
