"""Autonomy layer.

Two responsibilities, deliberately kept together because they are the same
concern seen from two sides:

* :mod:`autonomy.supervisor` — keep the bot running (always-on operation).
* :mod:`autonomy.edge_gate` — decide whether it is allowed to risk real capital.

A bot that can run unattended but cannot judge whether it should is more
dangerous than one that simply stops.
"""
