busy = [[(0, 30), (90, 120)], [(45, 60), (45, 55)]]


all_busy_intervals = sorted([interval for user_intervals in busy for interval in user_intervals])

for i in range(1, len(all_busy_intervals)):
    print(i)
