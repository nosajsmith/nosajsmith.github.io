from server.staff_model_v1 import StaffModelV1

def main() -> None:
    staff = StaffModelV1()  # default capacity=4
    base = 12

    print("Submit 8 orders (base ETA = 12h)")
    for i in range(1, 9):
        staff.submit_order()  # submit FIRST so overload applies immediately
        eff = staff.estimate_latency(base)
        print(f"{i:02d}. load={staff.load} base={base} eff={eff}")

    print("\nAdvance time 12h (decay should reduce load by 2)")
    staff.advance_time(12)
    eff_after = staff.estimate_latency(base)
    print(f"after: load={staff.load} base={base} eff={eff_after}")

if __name__ == "__main__":
    main()
