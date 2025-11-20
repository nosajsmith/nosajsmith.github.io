# -*- coding: utf-8 -*-
from dataclasses import asdict
def movement_report_dict(report): return {'movements':[asdict(m) for m in report.movements]}
def combat_report_dict(report): return {'combats':[{'attacker':c.attacker,'defender':c.defender,'location':c.location,'odds':c.odds,'result':c.result,'atk_losses':c.atk_losses,'def_losses':c.def_losses,'defender_retreat_path':c.defender_retreat_path} for c in report.combats]}
