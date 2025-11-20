from order_system import OrderDispatcher

class StaffAssistant:
    def __init__(self, auto_approve=False):
        self.auto_approve = auto_approve
        self.log = []

    def review_recommendations(self, unit_id, recs, current_turn, dispatcher: OrderDispatcher):
        for rec in recs:
            if self.auto_approve:
                decision = "approved"
                dispatcher.dispatch_from_recommendations(unit_id, [rec], current_turn)
            else:
                print("\n--- AI Suggestion ---")
                print(f"Unit: {unit_id}")
                print(f"Action: {rec['action']}")
                print(f"Reason: {rec['text']}")
                print(f"Priority: {rec.get('priority', 'normal')}")
                choice = input("Approve this order? [y/n]: ").strip().lower()
                if choice == "y":
                    dispatcher.dispatch_from_recommendations(unit_id, [rec], current_turn)
                    decision = "approved"
                else:
                    decision = "rejected"

            self.log.append({
                "unit": unit_id,
                "action": rec["action"],
                "reason": rec["text"],
                "priority": rec.get("priority", "normal"),
                "decision": decision,
                "turn": current_turn
            })

    def print_log(self):
        print("\n=== Staff Assistant Log ===")
        for entry in self.log:
            print(f"Turn {entry['turn']}: {entry['unit']} → {entry['action']} ({entry['decision']})")
