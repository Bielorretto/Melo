#!/usr/bin/env python3
"""Point d'entrée de Melo : ./cli.py melo ouvre le menu."""

import argparse

from core.menu import run_menu


def main():
    parser = argparse.ArgumentParser(prog="cli.py", description="Simulateur de piscine Melo")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("melo", help="ouvre le menu de Melo (piscine / common core, exam / module / IA)")
    parser.parse_args()
    run_menu()


if __name__ == "__main__":
    main()
