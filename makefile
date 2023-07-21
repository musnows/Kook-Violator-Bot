.PHONY:ps
ps:
	ps jax | head -1 && ps jax | grep volbot.py |  grep -v grep

.PHONY:run
run:
	nohup python3.10 -u volbot.py >> /dev/null 2>&1 &
