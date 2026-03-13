#!/usr/bin/env python3
"""Miner 2 — Run in Terminal 2: python subnet/miner2.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["MINER_ID"] = "2"
from subnet.miner_node import main
main()
