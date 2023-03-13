import _thread as thread
import time

def count(name, delay):
	for i in range(4):
		time.sleep(delay)
		print(i)

thread.start_new_thread(count, ("1", 1))
thread.start_new_thread(count, ("2", 1))
print("Done!")
time.sleep(10)