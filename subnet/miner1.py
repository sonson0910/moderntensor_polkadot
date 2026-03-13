#!/usr/bin/env python3
"""Miner 1 — Run in Terminal 1: python subnet/miner1.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["MINER_ID"] = "1"
from subnet.miner_node import main
main()
