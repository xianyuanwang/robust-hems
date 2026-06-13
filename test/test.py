from copy import deepcopy
from bubble_sort import bubble_sort, bubble_sort_inplace


def run_tests():
	cases = [
		([], []),
		([1], [1]),
		([1, 2, 3, 4], [1, 2, 3, 4]),
		([4, 3, 2, 1], [1, 2, 3, 4]),
		([3, 1, 2, 1], [1, 1, 2, 3]),
		([5, -1, 3, 0], [-1, 0, 3, 5]),
	]

	passed = 0
	for i, (inp, expected) in enumerate(cases, 1):
		out = bubble_sort(inp)
		if out != expected:
			print(f"Case {i} bubble_sort FAILED: inp={inp} out={out} expected={expected}")
			continue

		# test in-place
		arr = deepcopy(inp)
		out2 = bubble_sort_inplace(arr)
		if out2 != expected or arr != expected:
			print(f"Case {i} bubble_sort_inplace FAILED: inp={inp} out={out2} arr={arr} expected={expected}")
			continue

		passed += 1

	total = len(cases)
	print(f"Passed {passed}/{total} tests")


if __name__ == "__main__":
	run_tests()

