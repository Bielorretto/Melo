#!/usr/bin/env python3
"""Point d'entrée de Melo : ./cli.py melo ouvre le menu, ./cli.py metrique les statistiques."""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(prog="cli.py", description="Simulateur de piscine Melo")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("melo", help="ouvre le menu de Melo (piscine / common core, exam / module / IA)")
    metrique = sub.add_parser("metrique", help="ouvre le graphique des utilisateurs de Melo dans le navigateur")
    metrique.add_argument("--demo", action="store_true", help="affiche la page avec des données d'exemple")
    args = parser.parse_args()

    if args.command == "metrique":
        from core.metrics import run_metrique
        sys.exit(run_metrique(demo=args.demo))

    from core.menu import run_menu
    from core.stats import record_launch
    record_launch()
    run_menu()


if __name__ == "__main__":
    main()
